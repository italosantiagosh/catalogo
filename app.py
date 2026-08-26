"""
Catalogo de medalhas -- ponto de entrada Flask.

Rotas ate a ETAPA 9:
    /                       catalogo -- busca + grid de cards por santo/devocional
    /produto/<id>           pagina de produto -- modelos, tamanho, quantidade
    /carrinho               itens do carrinho + botoes de WhatsApp (persistido em localStorage)
    /api/carrinho/calcular  preco/faixa de atacado recalculados a partir da quantidade total
    /personalizada          gerador de medalha personalizada (upload -> simulacao)

O numero de WhatsApp fica so em config.py (WHATSAPP_NUMBER); a pagina
do carrinho recebe esse valor via render_template e monta a mensagem
inteira no navegador (static/js/carrinho_pagina.js), a partir dos
mesmos dados que ja aparecem na tela -- nao ha nenhum numero nem
mensagem duplicados em outro lugar do codigo.

O calculo de preco fica centralizado em services/pricing.py
(calcular_preco, proxima_faixa, calcular_carrinho) e so e chamado pelo
servidor -- a pagina do carrinho manda a lista de itens pro endpoint
acima e recebe de volta preco unitario/subtotal por item, a faixa
atingida e o quanto falta pra proxima.

O gerador de medalha personalizada (services/gerador/) e o mesmo
codigo do repositorio `mockup`, ja em producao em
gerador-medalhas.onrender.com -- so o import interno de compositor.py
virou relativo para funcionar como pacote aqui dentro; a logica de
composicao (compositor.py) e a geometria calibrada (config.py) nao
foram alteradas.

/personalizada usa o mesmo editor de recorte (canvas, arraste + zoom)
e o mesmo esquema de downloads por token de uso unico (/download/<token>)
do `mockup` -- ver _registrar_download abaixo. Por isso so funciona com
1 worker do gunicorn (Procfile/render.yaml: --workers 1): os tokens
ficam em memoria do processo, um download podia cair num worker
diferente do que gerou a previa.
"""

from __future__ import annotations

import base64
import hmac
import io
import secrets
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as escapar_xml

from flask import Flask, Response, abort, jsonify, redirect, render_template, request, send_file, url_for
from PIL import Image
from werkzeug.datastructures import FileStorage

from apscheduler.schedulers.background import BackgroundScheduler

from config import (
    ADMIN_PASSWORD,
    ADMIN_USER,
    CANONICAL_DOMAIN,
    DESCRICOES_CATEGORIA,
    DESCRICOES_FORMATO,
    DESTAQUES_HOME,
    ENABLE_SCHEDULER,
    GA4_MEASUREMENT_ID,
    GOOGLE_SITE_VERIFICATION,
    INSTAGRAM_URL,
    KIT_LIVRARIA_SHALOM,
    LEMBRETE_MINUTOS,
    META_PIXEL_ID,
    PROCURADOS_HOME,
    PROVA_SOCIAL,
    VIDEO_APRESENTACAO_URL,
    WHATSAPP_NUMBER,
)
from services.catalogo import (
    buscar_produto,
    carregar_produtos,
    categoria_por_slug,
    categorias_com_slug,
    normalizar_busca,
    slugify,
)
from services.paginas_institucionais import PAGINAS_ATENDIMENTO
from services.catalogo_pdf import gerar_pdf_catalogo
from services.email import (
    enviar_confirmacao_pedido,
    enviar_lembrete_pedido_pendente,
    enviar_link_pagamento,
    enviar_pedido_enviado,
)
from services.frete import calcular_frete
from services.infinitepay import criar_link_pagamento
from services.pedidos import (
    atualizar_status,
    criar_pedido,
    listar_pedidos,
    listar_pedidos_pendentes_para_lembrete,
    marcar_email_enviado,
    marcar_email_lembrete_enviado,
    marcar_email_pedido_criado_enviado,
    marcar_pago,
    marcar_tiny_sincronizado,
    obter_pedido,
)
from services.pix import gerar_copia_cola, gerar_qr_data_uri
from services.tiny import criar_pedido_tiny
from services.gerador.compositor import auto_cover_box, compose_medal, crop_to_box, load_rgba
from services.gerador.config import IMAGE_EXTENSIONS, MEDAL_SPECS
from services.pricing import CHAVES_PRECO, calcular_carrinho, preco_varejo

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024  # 60MB no total do upload


@app.route("/healthz", methods=["GET"])
def healthz():
    """Sempre 200, nunca redirecionado (ver _redirecionar_para_dominio_canonico
    abaixo) -- se o Render tiver algum health check apontando pro host
    antigo (catalogo-medalhas.onrender.com), configurar esse caminho como
    Health Check Path evita que ele vire um redirect 301 depois que
    CANONICAL_DOMAIN estiver ativo."""
    return "ok", 200


@app.before_request
def _redirecionar_para_dominio_canonico():
    """Com CANONICAL_DOMAIN configurado (ver config.py), manda qualquer
    acesso por outro host pro dominio definitivo (301, preserva
    caminho+query) -- evita as duas URLs (Render + dominio proprio)
    ficarem indexadas como conteudo duplicado. So GET/HEAD de pagina:
    /healthz e /api/* ficam de fora pra nao quebrar health check nem
    chamadas fetch() em andamento durante a transicao."""
    if not CANONICAL_DOMAIN:
        return None
    if request.host.lower() == CANONICAL_DOMAIN.lower():
        return None
    if request.method not in ("GET", "HEAD"):
        return None
    if request.path == "/healthz" or request.path.startswith("/api/"):
        return None
    destino = f"https://{CANONICAL_DOMAIN}{request.full_path if request.query_string else request.path}"
    return redirect(destino, code=301)


def _dados_organizacao() -> dict:
    """Schema.org Organization (SEO -- ajuda o Google a reconhecer a
    marca/negocio) -- dados reais: CNPJ, endereco (so retirada com
    agendamento, nao e loja fisica aberta), contato. Igual em toda
    pagina, ver base.html."""
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Nove de Julho Artigos Ltda",
        "alternateName": "Nove de Julho",
        "url": request.url_root,
        "logo": url_for("static", filename="img/logo-icone.png", _external=True),
        "taxID": "39.390.354/0001-25",
        "telephone": f"+55{WHATSAPP_NUMBER[2:]}",
        "email": "9djulho@gmail.com",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "Rua Furnas, 4835",
            "addressLocality": "Natal",
            "addressRegion": "RN",
            "addressCountry": "BR",
        },
        "sameAs": [INSTAGRAM_URL],
    }


def _dados_website() -> dict:
    """Schema.org WebSite + SearchAction (SEO -- habilita o Google a
    considerar mostrar uma caixa de busca do proprio site direto no
    resultado, "sitelinks searchbox"). Aponta pra /catalogo, que e onde
    a busca de verdade filtra os produtos (ver static/js/catalogo.js)."""
    base = request.url_root.rstrip("/")
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Nove de Julho",
        "url": f"{base}/",
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{base}/catalogo?q={{termo_busca}}",
            },
            "query-input": "required name=termo_busca",
        },
    }


def _dados_faq(faq_items: list[tuple[str, str]]) -> dict:
    """Schema.org FAQPage -- so pra paginas de atendimento que tem
    "faq_items" (ver services/paginas_institucionais.py). Habilita o
    rich snippet de pergunta expansivel direto no resultado do Google."""
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": pergunta,
                "acceptedAnswer": {"@type": "Answer", "text": resposta},
            }
            for pergunta, resposta in faq_items
        ],
    }


def _dados_breadcrumb(itens: list[tuple[str, str]]) -> dict:
    """Schema.org BreadcrumbList a partir de uma lista [(nome, url_absoluta), ...],
    na ordem Catalogo -> ... -> pagina atual. Ver produto()/categoria()/
    pagina_atendimento() e o nav visual correspondente nos templates."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": nome, "item": url}
            for i, (nome, url) in enumerate(itens)
        ],
    }


@app.context_processor
def _injetar_globais_de_template():
    # Disponivel em todo template (base.html usa pro botao flutuante de
    # WhatsApp, pela bolinha de video, pelos scripts de analytics e pelo
    # schema.org Organization no <head>) -- nenhum desses muda por rota.
    return {
        "whatsapp_number": WHATSAPP_NUMBER,
        "video_apresentacao_url": VIDEO_APRESENTACAO_URL,
        "ga4_measurement_id": GA4_MEASUREMENT_ID,
        "meta_pixel_id": META_PIXEL_ID,
        "google_site_verification": GOOGLE_SITE_VERIFICATION,
        "instagram_url": INSTAGRAM_URL,
        "ano_atual": datetime.now(timezone.utc).year,
        "dados_organizacao": _dados_organizacao(),
        "dados_website": _dados_website(),
    }


CropBox = tuple[float, float, float, float]

# Formato/cor (escolhidos na tela, ver produto.js/personalizada.js) -> id de
# MEDAL_SPECS (services/gerador/config.py). "medalha" e o mesmo mockup
# independente do tamanho (12mm/16mm sao so o tamanho fisico impresso, a
# simulacao visual e identica) -- so entremeio muda de spec conforme a cor.
FORMATO_PARA_SPEC = {
    ("medalha", None): "prata_16mm",
    ("entremeio", "prata"): "entremeio_prata",
    ("entremeio", "ouro_velho"): "entremeio_ouro_velho",
    ("chaveiro", None): "chaveiro",
}


def _formatar_preco(valor: float) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


app.jinja_env.filters["preco"] = _formatar_preco


def _extensao_valida(nome_arquivo: str) -> bool:
    nome_lower = nome_arquivo.lower()
    return any(nome_lower.endswith(ext) for ext in IMAGE_EXTENSIONS)


def _resolver_spec_id(formato: str, cor: str | None) -> str | None:
    return FORMATO_PARA_SPEC.get((formato, cor))


# Downloads (previa da medalha, recorte 1:1) ficam guardados aqui em
# memoria por um token de uso unico, em vez de embutidos como data URI --
# o Safari do iPhone tem suporte inconsistente pra "baixar" data URIs
# grandes, so mostra a imagem em vez de salvar. Um link de verdade pro
# navegador buscar (com Content-Disposition) funciona em qualquer
# navegador -- mesmo esquema do repositorio `mockup` (ver docstring do
# modulo sobre --workers 1).
_DOWNLOAD_TTL_SEGUNDOS = 15 * 60
_downloads: dict[str, tuple[bytes, str, str, float]] = {}


def _registrar_download(dados: bytes, mimetype: str, nome_arquivo: str) -> str:
    agora = time.time()
    for token, (_, _, _, expira_em) in list(_downloads.items()):
        if expira_em < agora:
            _downloads.pop(token, None)
    token = secrets.token_urlsafe(16)
    _downloads[token] = (dados, mimetype, nome_arquivo, agora + _DOWNLOAD_TTL_SEGUNDOS)
    return token


def _imagem_para_bytes(imagem: Image.Image) -> bytes:
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    return buffer.getvalue()


def _sem_extensao(nome_arquivo: str) -> str:
    return Path(nome_arquivo).stem


def _ler_box(valores: dict) -> CropBox | None:
    try:
        return (
            float(valores["x1"]),
            float(valores["y1"]),
            float(valores["x2"]),
            float(valores["y2"]),
        )
    except (KeyError, ValueError, TypeError):
        return None


def _preview_data_uri(imagem: Image.Image) -> str:
    return "data:image/png;base64," + base64.b64encode(_imagem_para_bytes(imagem)).decode("ascii")


def _crop_quadrada(caminho: Path, crop_box: CropBox | None) -> Image.Image:
    """Recorte quadrado 1:1 'cru' (sem moldura da medalha) -- o arquivo que
    deve ser reenviado pelo WhatsApp se o cliente reposicionou/deu zoom no
    recorte (ver aviso na pagina)."""
    img = load_rgba(caminho)
    box = crop_box if crop_box is not None else auto_cover_box(img.size)
    quadrado = crop_to_box(img, box)
    fundo = Image.new("RGB", quadrado.size, (255, 255, 255))
    fundo.paste(quadrado, mask=quadrado.split()[3])
    return fundo


def _salvar_temp(arquivo: FileStorage) -> tempfile._TemporaryFileWrapper:
    sufixo = Path(arquivo.filename).suffix or ".jpg"
    tmp = tempfile.NamedTemporaryFile(suffix=sufixo)
    arquivo.save(tmp.name)
    return tmp


def _montar_destaques(produtos: list[dict], itens_por_id: dict) -> list[dict]:
    """Monta os grupos de destaques da home (DESTAQUES_HOME em config.py)
    a partir dos itens ja carregados -- ids que nao existirem mais no
    catalogo sao ignorados silenciosamente, nao quebram a pagina.

    Um grupo normal lista "produtos" (ids diferentes, 1 card cada, foto do
    modelo 1). Um grupo com "modelos_de" lista, em vez disso, os VARIOS
    modelos de UM SO produto (cada card leva pra mesma pagina de produto,
    so a foto/legenda mudam) -- usado no Ano Jubilar de Sao Francisco."""
    produtos_por_id = {p["id"]: p for p in produtos}
    destaques = []
    for grupo in DESTAQUES_HOME:
        if "modelos_de" in grupo:
            produto = produtos_por_id.get(grupo["modelos_de"])
            produtos_grupo = (
                [
                    {
                        "id": produto["id"],
                        "nome": f"{produto['nome']} — {modelo['nome']}",
                        "thumbnail": modelo["imagem"],
                    }
                    for modelo in produto["modelos"]
                ]
                if produto
                else []
            )
        else:
            produtos_grupo = [itens_por_id[pid] for pid in grupo["produtos"] if pid in itens_por_id]
        if produtos_grupo:
            destaques.append({"titulo": grupo["titulo"], "produtos": produtos_grupo})
    return destaques


@app.route("/robots.txt", methods=["GET"])
def robots_txt():
    linhas = ["User-agent: *", "Allow: /", f"Sitemap: {request.url_root}sitemap.xml"]
    return Response("\n".join(linhas), mimetype="text/plain")


@app.route("/sitemap.xml", methods=["GET"])
def sitemap_xml():
    produtos = carregar_produtos()
    caminhos = [
        url_for("index"),
        url_for("catalogo_completo"),
        url_for("carrinho"),
        url_for("personalizada"),
        url_for("kit_livraria_shalom"),
    ]
    caminhos += [url_for("categoria", slug=c["slug"]) for c in categorias_com_slug(produtos)]
    caminhos += [url_for("produto", produto_id=p["id"]) for p in produtos]
    caminhos += [url_for("pagina_atendimento", slug=s) for s in PAGINAS_ATENDIMENTO]

    base = request.url_root.rstrip("/")
    itens_xml = "".join(
        f"<url><loc>{(base + caminho).replace('&', '&amp;')}</loc></url>" for caminho in caminhos
    )
    corpo = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + itens_xml + "</urlset>"
    )
    return Response(corpo, mimetype="application/xml")


# Um item de feed por VARIACAO de verdade -- cada combinacao que o
# cliente realmente escolhe na pagina de produto (formato, depois
# tamanho ou cor) vira 1 item, pra cada MODELO do santo. Sao Jose, por
# exemplo, tem 6 modelos x 5 variacoes = 30 itens. (sufixo do id,
# prefixo do titulo, campo da imagem no modelo, chave_preco pro preco
# de varejo, chave de DESCRICOES_FORMATO, g:size, g:color).
_VARIANTES_FEED = (
    ("medalha-12mm", "Medalha", "imagem", "12mm", "medalha", "1,2 cm", None),
    ("medalha-16mm", "Medalha", "imagem", "16mm", "medalha", "1,6 cm", None),
    ("entremeio-prata", "Entremeio", "imagem_entremeio_prata", "entremeio", "entremeio", None, "Prata"),
    ("entremeio-ouro-velho", "Entremeio", "imagem_entremeio_ouro_velho", "entremeio", "entremeio", None, "Ouro velho"),
    ("chaveiro", "Chaveiro", "imagem_chaveiro", "chaveiro", "chaveiro", None, None),
)


@app.route("/feed-produtos.xml", methods=["GET"])
def feed_produtos_xml():
    """Feed de produtos no formato RSS 2.0 + namespace do Google (o mesmo
    formato aceito tanto pelo Google Merchant Center/Shopping quanto pelo
    Meta Commerce Manager, pra Loja do Instagram/Facebook) -- 1 item por
    modelo x variacao (ver _VARIANTES_FEED acima), todos agrupados por
    g:item_group_id (o id do produto) pra aparecerem como variantes do
    mesmo santo no Google/Meta, nao como produtos avulsos repetidos.
    `availability` sempre "in stock": o catalogo e feito sob encomenda,
    nao ha controle de estoque real pra diferenciar (mesma decisao ja
    tomada no schema.org Product de templates/produto.html)."""
    produtos = carregar_produtos()
    base = request.url_root.rstrip("/")

    itens_xml = []
    for produto in produtos:
        link = base + url_for("produto", produto_id=produto["id"])
        categoria = escapar_xml(produto["categoria"])
        for modelo in produto["modelos"]:
            for sufixo, prefixo_titulo, campo_imagem, chave_preco, chave_descricao, tamanho, cor in _VARIANTES_FEED:
                imagem_relativa = modelo.get(campo_imagem)
                if not imagem_relativa:
                    continue
                imagem = base + url_for("static", filename=imagem_relativa)
                sufixo_titulo = f" — {tamanho}" if tamanho else (f" — {cor}" if cor else "")
                titulo = escapar_xml(f"{prefixo_titulo} de {produto['nome']} — Modelo {modelo['id']}{sufixo_titulo}")
                descricao = escapar_xml(
                    f"{prefixo_titulo} de {produto['nome']}, modelo {modelo['id']}, de atacado. "
                    f"{DESCRICOES_FORMATO[chave_descricao]} Desconto progressivo por "
                    "quantidade, sem cupom."
                )
                preco_item = f"{preco_varejo(chave_preco):.2f} BRL"
                # rotulo do conjunto (Medalha/Entremeio/Chaveiro) -- vai em
                # custom_label_0 (campo feito pra isso, tanto Google quanto
                # Meta deixam criar colecoes/product sets filtrando por ele)
                # e tambem no product_type, como hierarquia categoria >
                # formato, que ajuda a navegacao por facetas no Shopping.
                rotulo_grupo = chave_descricao.capitalize()
                item = [
                    "<item>",
                    f"<g:id>{escapar_xml(produto['id'])}-modelo{modelo['id']}-{sufixo}</g:id>",
                    f"<g:item_group_id>{escapar_xml(produto['id'])}</g:item_group_id>",
                    f"<title>{titulo}</title>",
                    f"<description>{descricao}</description>",
                    f"<link>{escapar_xml(link)}</link>",
                    f"<g:image_link>{escapar_xml(imagem)}</g:image_link>",
                    "<g:availability>in stock</g:availability>",
                    f"<g:price>{preco_item}</g:price>",
                    "<g:brand>Nove de Julho</g:brand>",
                    "<g:condition>new</g:condition>",
                    "<g:identifier_exists>no</g:identifier_exists>",
                    f"<g:product_type>{categoria} &gt; {rotulo_grupo}</g:product_type>",
                    "<g:google_product_category>Religious &amp; Ceremonial &gt; Religious Jewelry</g:google_product_category>",
                    f"<g:custom_label_0>{rotulo_grupo}</g:custom_label_0>",
                ]
                if tamanho:
                    item.append(f"<g:size>{escapar_xml(tamanho)}</g:size>")
                if cor:
                    item.append(f"<g:color>{escapar_xml(cor)}</g:color>")
                item.append("</item>")
                itens_xml.append("".join(item))

    corpo = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0"><channel>'
        "<title>Nove de Julho — Catálogo de Atacado</title>"
        f"<link>{base}/</link>"
        "<language>pt-BR</language>"
        "<description>Medalhas, entremeios e chaveiros religiosos de atacado.</description>"
        + "".join(itens_xml)
        + "</channel></rss>"
    )
    return Response(corpo, mimetype="application/xml")


def _itens_do_grid(produtos: list[dict]) -> list[dict]:
    return [
        {
            "id": p["id"],
            "nome": p["nome"],
            "categoria": p["categoria"],
            "thumbnail": p["modelos"][0]["imagem"],
            "thumbnail_chaveiro": p["modelos"][0]["imagem_chaveiro"],
        }
        for p in produtos
    ]


@app.route("/", methods=["GET"])
def index():
    """Home -- landing page comercial (hero, vantagens, destaques, banners),
    SEM a grade completa de produtos (fica em /catalogo, ver
    catalogo_completo abaixo) -- pedido do usuario pra manter a home mais
    limpa/curta, mostrando so 4 santos em destaque + botao pro catalogo
    inteiro."""
    produtos = carregar_produtos()
    itens = _itens_do_grid(produtos)
    itens_por_id = {item["id"]: item for item in itens}
    destaques = _montar_destaques(produtos, itens_por_id)
    procurados = [itens_por_id[pid] for pid in PROCURADOS_HOME if pid in itens_por_id]
    categorias = categorias_com_slug(produtos)
    return render_template(
        "index.html",
        preco_varejo=preco_varejo(),
        destaques=destaques,
        procurados=procurados,
        categorias=categorias,
    )


@app.route("/catalogo", methods=["GET"])
def catalogo_completo():
    """Grade completa com busca + filtro por categoria -- o que antes
    ficava direto na home. `?q=` (opcional) vem do campo de busca da home
    e pre-preenche o filtro aqui (ver static/js/catalogo.js)."""
    produtos = carregar_produtos()
    itens = _itens_do_grid(produtos)
    categorias = categorias_com_slug(produtos)
    dados_breadcrumb = _dados_breadcrumb(
        [
            ("Início", url_for("index", _external=True)),
            ("Catálogo completo", url_for("catalogo_completo", _external=True)),
        ]
    )
    return render_template(
        "catalogo.html",
        produtos=itens,
        categorias=categorias,
        preco_varejo=preco_varejo(),
        dados_breadcrumb=dados_breadcrumb,
    )


@app.route("/kit-livraria-shalom", methods=["GET"])
def kit_livraria_shalom():
    """Kit inicial sugerido (ver config.py:KIT_LIVRARIA_SHALOM) -- o
    sortimento que o cliente ja mandava manualmente pelo WhatsApp vira
    uma pagina com tudo pre-preenchido, editavel item a item, com um
    botao que joga tudo no carrinho de uma vez (static/js/kit.js)."""
    produtos_por_id = {p["id"]: p for p in carregar_produtos()}
    itens = []
    for entrada in KIT_LIVRARIA_SHALOM:
        produto = produtos_por_id.get(entrada["produto_id"])
        if produto is None:
            continue
        modelo = next((m for m in produto["modelos"] if m["id"] == entrada["modelo_id"]), None)
        if modelo is None:
            continue
        nome_exibicao = produto["nome"]
        if entrada.get("rotulo_extra"):
            nome_exibicao = f"{nome_exibicao} ({entrada['rotulo_extra']})"
        itens.append(
            {
                "produto_id": produto["id"],
                "produto_nome": produto["nome"],
                "nome_exibicao": nome_exibicao,
                "modelo_id": modelo["id"],
                "modelo_nome": modelo["nome"],
                "imagem": url_for("static", filename=modelo["imagem"]),
                "quantidade_sugerida": entrada["quantidade_sugerida"],
            }
        )
    dados_breadcrumb = _dados_breadcrumb(
        [
            ("Início", url_for("index", _external=True)),
            ("Kit Livraria Shalom", url_for("kit_livraria_shalom", _external=True)),
        ]
    )
    return render_template(
        "kit.html",
        itens=itens,
        quantidade_total_sugerida=sum(i["quantidade_sugerida"] for i in itens),
        preco_varejo=preco_varejo(),
        dados_breadcrumb=dados_breadcrumb,
    )


@app.route("/categoria/<slug>", methods=["GET"])
def categoria(slug: str):
    """Pagina propria por categoria (SEO: URL indexavel, com titulo e
    meta description unicos -- ver config.py:DESCRICOES_CATEGORIA) --
    alem do filtro por clique que ja existe na home."""
    produtos = carregar_produtos()
    nome_categoria = categoria_por_slug(produtos, slug)
    if nome_categoria is None:
        abort(404)
    itens = [
        {
            "id": p["id"],
            "nome": p["nome"],
            "thumbnail": p["modelos"][0]["imagem"],
            "thumbnail_chaveiro": p["modelos"][0]["imagem_chaveiro"],
        }
        for p in produtos
        if p["categoria"] == nome_categoria
    ]
    dados_breadcrumb = _dados_breadcrumb(
        [
            ("Catálogo", url_for("index", _external=True)),
            (nome_categoria, url_for("categoria", slug=slug, _external=True)),
        ]
    )
    return render_template(
        "categoria.html",
        categoria_nome=nome_categoria,
        categoria_descricao=DESCRICOES_CATEGORIA.get(nome_categoria, ""),
        produtos=itens,
        preco_varejo=preco_varejo(),
        dados_breadcrumb=dados_breadcrumb,
    )


@app.route("/produto/<produto_id>", methods=["GET"])
def produto(produto_id: str):
    produto = buscar_produto(produto_id)
    if produto is None:
        abort(404)
    preco = preco_varejo()
    categoria_slug = slugify(produto["categoria"])

    relacionados = [
        {
            "id": p["id"],
            "nome": p["nome"],
            "thumbnail": p["modelos"][0]["imagem"],
        }
        for p in carregar_produtos()
        if p["categoria"] == produto["categoria"] and p["id"] != produto_id
    ][:6]

    dados_produto = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": produto["nome"],
        "image": url_for("static", filename=produto["modelos"][0]["imagem"], _external=True),
        "description": (
            f"Medalha, entremeio e chaveiro de {produto['nome']} a partir de "
            f"R$ {preco:.2f} -- desconto de atacado automático conforme a quantidade."
        ),
        "offers": {
            "@type": "Offer",
            "url": url_for("produto", produto_id=produto_id, _external=True),
            "priceCurrency": "BRL",
            "price": f"{preco:.2f}",
            "availability": "https://schema.org/InStock",
        },
    }
    dados_breadcrumb = _dados_breadcrumb(
        [
            ("Catálogo", url_for("index", _external=True)),
            (produto["categoria"], url_for("categoria", slug=categoria_slug, _external=True)),
            (produto["nome"], url_for("produto", produto_id=produto_id, _external=True)),
        ]
    )
    return render_template(
        "produto.html",
        produto=produto,
        categoria_slug=categoria_slug,
        relacionados=relacionados,
        preco_varejo=preco,
        preco_varejo_chaveiro=preco_varejo("chaveiro"),
        prova_social=PROVA_SOCIAL,
        descricoes_formato=DESCRICOES_FORMATO,
        dados_produto=dados_produto,
        dados_breadcrumb=dados_breadcrumb,
    )


@app.route("/carrinho", methods=["GET"])
def carrinho():
    return render_template("carrinho.html")


@app.route("/atendimento/<slug>", methods=["GET"])
def pagina_atendimento(slug: str):
    pagina = PAGINAS_ATENDIMENTO.get(slug)
    if pagina is None:
        abort(404)
    dados_breadcrumb = _dados_breadcrumb(
        [
            ("Catálogo", url_for("index", _external=True)),
            (pagina["titulo"], url_for("pagina_atendimento", slug=slug, _external=True)),
        ]
    )
    dados_faq = _dados_faq(pagina["faq_items"]) if pagina.get("faq_items") else None
    return render_template(
        "pagina_atendimento.html",
        pagina=pagina,
        slug=slug,
        dados_breadcrumb=dados_breadcrumb,
        dados_faq=dados_faq,
    )


@app.route("/catalogo.pdf", methods=["GET"])
def catalogo_pdf():
    """PDF com o catalogo completo (fotos + tabela de precos de atacado +
    orientacoes de pedido) -- ver services/catalogo_pdf.py. Servido
    inline (nao forcado como anexo) pra abrir no visualizador de PDF do
    navegador, de onde da pra salvar/baixar normalmente."""
    return send_file(
        io.BytesIO(gerar_pdf_catalogo()),
        mimetype="application/pdf",
        as_attachment=False,
        download_name="catalogo-nove-de-julho.pdf",
    )


def _itens_validos_do_corpo(dados: dict) -> list[dict]:
    itens_validos = []
    for item in dados.get("itens", []):
        try:
            chave_preco = str(item["chave_preco"])
            quantidade = int(item["quantidade"])
        except (KeyError, TypeError, ValueError):
            continue
        if chave_preco not in CHAVES_PRECO or quantidade <= 0:
            continue
        itens_validos.append({"chave_preco": chave_preco, "quantidade": quantidade})
    return itens_validos


def _itens_com_descricao_do_corpo(dados: dict) -> list[dict]:
    """Mesma validacao de _itens_validos_do_corpo, mas guarda tambem uma
    descricao legivel (nome do produto/modelo/formato) pra exibir no
    pedido e no item de pagamento -- so cosmetico, NUNCA usado pra
    calcular preco (isso continua vindo so de chave_preco+quantidade,
    via calcular_carrinho)."""
    itens_validos = []
    for item in dados.get("itens", []):
        try:
            chave_preco = str(item["chave_preco"])
            quantidade = int(item["quantidade"])
        except (KeyError, TypeError, ValueError):
            continue
        if chave_preco not in CHAVES_PRECO or quantidade <= 0:
            continue
        partes = [str(item.get(campo, "")).strip() for campo in ("produtoNome", "modeloNome") if item.get(campo)]
        formato = str(item.get("formato", "")).strip()
        if formato and formato != "medalha":
            partes.append(formato.capitalize())
        descricao = " — ".join(p for p in partes if p) or chave_preco
        itens_validos.append({"chave_preco": chave_preco, "quantidade": quantidade, "descricao": descricao[:120]})
    return itens_validos


def _cliente_valido(dados: dict) -> dict | None:
    cliente = dados.get("cliente") or {}
    nome = str(cliente.get("nome", "")).strip()
    documento = str(cliente.get("documento", "")).strip()
    telefone = str(cliente.get("telefone", "")).strip()
    email = str(cliente.get("email", "")).strip()
    if not nome or not documento or not telefone or not email:
        return None
    tipo_pessoa = str(cliente.get("tipo_pessoa", "fisica"))
    return {
        "nome": nome,
        "tipo_pessoa": tipo_pessoa if tipo_pessoa in ("fisica", "juridica") else "fisica",
        "documento": documento,
        "telefone": telefone,
        "email": email,
    }


def _endereco_valido(dados: dict) -> dict | None:
    endereco = dados.get("endereco") or {}
    campos_obrigatorios = ["cep", "logradouro", "numero", "bairro", "cidade", "uf"]
    valores = {campo: str(endereco.get(campo, "")).strip() for campo in campos_obrigatorios}
    if any(not valores[campo] for campo in campos_obrigatorios):
        return None
    valores["complemento"] = str(endereco.get("complemento", "")).strip()
    # opcional -- so preenchido quando o cliente marca "entregar em
    # nome de outra pessoa/empresa" (ver static/js/carrinho_pagina.js).
    # Se vazio, quem recebe e´ o proprio cliente cadastrado (ver
    # services.pedidos.criar_pedido/templates/pedido.html).
    valores["destinatario_nome"] = str(endereco.get("destinatario_nome", "")).strip()
    tipo_pessoa_dest = str(endereco.get("destinatario_tipo_pessoa", "")).strip()
    valores["destinatario_tipo_pessoa"] = tipo_pessoa_dest if tipo_pessoa_dest in ("fisica", "juridica") else ""
    valores["destinatario_documento"] = str(endereco.get("destinatario_documento", "")).strip()
    return valores


@app.route("/api/busca", methods=["GET"])
def api_busca():
    """Busca ao vivo da home -- digitar no campo chama isso (debounced,
    ver static/js/home_busca.js) e mostra nome + miniatura dos santos que
    baterem, sem precisar apertar Enter nem carregar a grade completa
    (essa fica em /catalogo)."""
    termo = normalizar_busca(request.args.get("q", ""))
    if not termo:
        return jsonify([])
    itens = _itens_do_grid(carregar_produtos())
    resultados = [item for item in itens if termo in normalizar_busca(item["nome"])][:6]
    return jsonify(
        [
            {
                "id": item["id"],
                "nome": item["nome"],
                "thumbnail": url_for("static", filename=item["thumbnail"]),
                "url": url_for("produto", produto_id=item["id"]),
            }
            for item in resultados
        ]
    )


@app.route("/api/carrinho/calcular", methods=["POST"])
def api_calcular_carrinho():
    dados = request.get_json(silent=True) or {}
    itens_validos = _itens_validos_do_corpo(dados)
    return jsonify(calcular_carrinho(itens_validos))


@app.route("/api/frete/calcular", methods=["POST"])
def api_calcular_frete():
    dados = request.get_json(silent=True) or {}
    itens_validos = _itens_validos_do_corpo(dados)
    cep = str(dados.get("cep", ""))

    resumo_carrinho = calcular_carrinho(itens_validos)
    resultado = calcular_frete(
        itens_validos,
        cep,
        resumo_carrinho["subtotal_total"],
        resumo_carrinho["frete_gratis_atingido"],
    )
    return jsonify(resultado)


@app.route("/api/pedido/criar", methods=["POST"])
def api_pedido_criar():
    """Cria o pedido (persistido, ver services/pedidos.py) e gera o link
    de pagamento da InfinitePay -- caminho automatico do "Pagar agora"
    no carrinho, alternativa ao "Finalizar pelo WhatsApp" (que continua
    funcionando do jeito que sempre funcionou, sem passar por aqui).
    Preco sempre recalculado no servidor (calcular_carrinho) -- nunca
    confia em subtotal/preco mandado pelo navegador."""
    dados = request.get_json(silent=True) or {}
    itens_validos = _itens_com_descricao_do_corpo(dados)
    if not itens_validos:
        return jsonify(erro="Carrinho vazio."), 400

    calculo = calcular_carrinho(itens_validos)
    if not calculo["atinge_minimo"]:
        return jsonify(erro="Pedido abaixo do mínimo de produtos."), 400

    frete = dados.get("frete") or {}
    try:
        frete_preco = float(frete.get("preco"))
    except (TypeError, ValueError):
        return jsonify(erro="Escolha uma opção de frete."), 400
    frete_descricao = str(frete.get("texto", "")).strip()
    if not frete_descricao:
        return jsonify(erro="Escolha uma opção de frete."), 400

    cliente = _cliente_valido(dados)
    if cliente is None:
        return jsonify(erro="Preencha seus dados completos (nome, documento, telefone e e-mail)."), 400
    endereco = _endereco_valido(dados)
    if endereco is None:
        return jsonify(erro="Preencha o endereço de entrega completo."), 400

    # guarda o preco unitario junto de cada item persistido -- alem de
    # registro, e o que os dois pontos abaixo usam pra reconstruir o
    # pedido sem precisar recalcular tudo de novo (ver
    # _itens_pagamento_de_pedido e o webhook mais abaixo).
    for item_validado, item_calculado in zip(itens_validos, calculo["itens"]):
        item_validado["valor_unitario"] = item_calculado["preco_unitario"]

    pedido = criar_pedido(
        itens=itens_validos,
        subtotal=calculo["subtotal_total"],
        frete_descricao=frete_descricao,
        frete_preco=frete_preco,
        cliente=cliente,
        endereco=endereco,
    )

    resultado = _gerar_link_pagamento_para_pedido(pedido, cliente, endereco)
    if "erro" in resultado:
        return jsonify(erro=resultado["erro"]), 502

    # e-mail com o link, caso o cliente feche a aba antes de terminar
    # de pagar -- best-effort, mesmo tratamento das outras integracoes
    # do fluxo (nao bloqueia a resposta se falhar).
    resultado_email = enviar_link_pagamento(
        pedido, resultado["url"], url_for("ver_pedido", token=pedido["token"], _external=True)
    )
    marcar_email_pedido_criado_enviado(pedido["token"], erro=resultado_email.get("erro"))

    return jsonify(url=resultado["url"], token=pedido["token"], codigo=pedido["codigo"])


def _itens_pagamento_de_pedido(pedido: dict) -> list[dict]:
    """Reconstroi a lista de itens no formato que a InfinitePay espera a
    partir de um pedido ja persistido (ver services.pedidos) -- usado
    tanto na criacao quanto em /api/pedido/<token>/novo-link, sem
    precisar do carrinho original de novo."""
    itens_pagamento = [
        {
            "id": item["chave_preco"],
            "description": item.get("descricao") or item["chave_preco"],
            "quantity": item["quantidade"],
            "price": round(item["valor_unitario"] * 100),
        }
        for item in pedido["itens"]
    ]
    if pedido.get("frete_preco", 0) > 0:
        itens_pagamento.append(
            {
                "id": "frete",
                "description": pedido.get("frete_descricao", ""),
                "quantity": 1,
                "price": round(pedido["frete_preco"] * 100),
            }
        )
    return itens_pagamento


def _gerar_link_pagamento_para_pedido(pedido: dict, cliente: dict, endereco: dict) -> dict:
    return criar_link_pagamento(
        order_nsu=pedido["token"],
        redirect_url=url_for("ver_pedido", token=pedido["token"], _external=True),
        webhook_url=url_for("webhook_infinitepay", _external=True),
        itens_pagamento=_itens_pagamento_de_pedido(pedido),
        cliente=cliente,
        endereco=endereco,
    )


def _cliente_e_endereco_do_pedido(pedido: dict) -> tuple[dict, dict]:
    """Reconstroi os dicts de cliente/endereco a partir de um pedido ja
    persistido -- usado pra gerar um novo link de pagamento sem
    precisar do carrinho original de novo (ver
    api_pedido_novo_link e _enviar_lembretes_pedidos_pendentes)."""
    cliente = {
        "nome": pedido.get("cliente_nome", ""),
        "tipo_pessoa": pedido.get("cliente_tipo_pessoa", ""),
        "documento": pedido.get("cliente_documento", ""),
        "telefone": pedido.get("cliente_telefone", ""),
        "email": pedido.get("cliente_email", ""),
    }
    endereco = {
        "cep": pedido.get("endereco_cep", ""),
        "logradouro": pedido.get("endereco_logradouro", ""),
        "numero": pedido.get("endereco_numero", ""),
        "complemento": pedido.get("endereco_complemento", ""),
        "bairro": pedido.get("endereco_bairro", ""),
        "cidade": pedido.get("endereco_cidade", ""),
        "uf": pedido.get("endereco_uf", ""),
    }
    return cliente, endereco


@app.route("/api/pedido/<token>/novo-link", methods=["POST"])
def api_pedido_novo_link(token: str):
    """Gera um novo link de pagamento pro mesmo pedido -- pro caso do
    link original ter expirado (a InfinitePay nao documenta um prazo
    fixo, entao em vez de tentar adivinhar, so oferecemos gerar de
    novo quando precisar). So funciona pra pedido ainda pendente."""
    pedido = obter_pedido(token)
    if pedido is None:
        return jsonify(erro="Pedido não encontrado."), 404
    if pedido["status"] != "pendente":
        return jsonify(erro="Esse pedido não está mais aguardando pagamento."), 400

    cliente, endereco = _cliente_e_endereco_do_pedido(pedido)
    resultado = _gerar_link_pagamento_para_pedido(pedido, cliente, endereco)
    if "erro" in resultado:
        return jsonify(erro=resultado["erro"]), 502
    return jsonify(url=resultado["url"])


@app.route("/webhook/infinitepay", methods=["POST"])
def webhook_infinitepay():
    """Recebido pela InfinitePay quando um pagamento e´ confirmado (ver
    redirect_url/webhook_url em api_pedido_criar acima). So marca como
    pago quando o valor pago cobre o total esperado -- e´ idempotente
    (webhook repetido nao reprocessa, ver services.pedidos.marcar_pago),
    entao sempre responde 200 mesmo quando nao ha nada a fazer, pra
    InfinitePay nao ficar reenviando em loop."""
    dados = request.get_json(silent=True) or {}
    token = str(dados.get("order_nsu", ""))
    pedido = obter_pedido(token) if token else None
    if pedido is None:
        return jsonify(erro="Pedido não encontrado."), 404

    try:
        valor_pago_centavos = float(dados.get("paid_amount", 0))
    except (TypeError, ValueError):
        valor_pago_centavos = 0.0

    total_esperado_centavos = round(pedido["total"] * 100)
    if valor_pago_centavos < total_esperado_centavos:
        return jsonify(ok=True, aviso="valor pago menor que o esperado, pedido não confirmado"), 200

    pedido_pago = marcar_pago(
        token,
        forma_pagamento=str(dados.get("capture_method", "")),
        parcelas=dados.get("installments"),
        valor_pago=valor_pago_centavos / 100,
        transaction_nsu=str(dados.get("transaction_nsu", "")),
    )

    # sincroniza com a Tiny so na primeira confirmacao -- webhook
    # repetido (comum em integracoes de pagamento) nao reenvia o
    # mesmo pedido pra la de novo. Falha na Tiny nao derruba a
    # confirmacao do pagamento (o pedido ja esta pago no site de
    # qualquer forma) -- so fica registrado o erro pra conferir depois.
    if pedido_pago and not pedido_pago["tiny_sincronizado"]:
        resultado_tiny = criar_pedido_tiny(pedido_pago)
        marcar_tiny_sincronizado(
            token,
            numero_pedido=resultado_tiny.get("numero"),
            erro=resultado_tiny.get("erro"),
        )

    # mesma logica -- so uma vez por pedido, falha nao derruba a
    # confirmacao do pagamento (ver services/email.py).
    if pedido_pago and not pedido_pago["email_enviado"]:
        resultado_email = enviar_confirmacao_pedido(
            pedido_pago, url_for("ver_pedido", token=token, _external=True)
        )
        marcar_email_enviado(token, erro=resultado_email.get("erro"))

    return jsonify(ok=True), 200


@app.route("/pedido/<token>", methods=["GET"])
def ver_pedido(token: str):
    pedido = obter_pedido(token)
    if pedido is None:
        abort(404)
    return render_template("pedido.html", pedido=pedido)


def _autenticacao_admin_valida(auth) -> bool:
    # sem as duas credenciais configuradas, o painel fica bloqueado
    # por padrao (nunca expõe pedido de ninguem sem senha definida).
    if not ADMIN_USER or not ADMIN_PASSWORD or auth is None:
        return False
    usuario_ok = hmac.compare_digest(auth.username or "", ADMIN_USER)
    senha_ok = hmac.compare_digest(auth.password or "", ADMIN_PASSWORD)
    return usuario_ok and senha_ok


@app.route("/admin/pedidos", methods=["GET"])
def admin_pedidos():
    """Painel interno pra ver os pedidos sem precisar consultar o
    SQLite direto -- autenticacao HTTP Basic simples (ver
    _autenticacao_admin_valida acima), pensado pra uso ocasional por
    uma unica pessoa, nao um sistema de contas."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    status_filtro = request.args.get("status") or None
    pedidos = listar_pedidos(status=status_filtro)
    return render_template("admin_pedidos.html", pedidos=pedidos, status_filtro=status_filtro)


@app.route("/admin/pedidos/<token>", methods=["GET"])
def admin_pedido_detalhe(token: str):
    """Tela de um pedido so, com formulario pra avancar o status na mao
    (faturado/enviado/entregue -- ver admin_pedido_status abaixo)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    pedido = obter_pedido(token)
    if pedido is None:
        abort(404)
    return render_template("admin_pedido_detalhe.html", pedido=pedido)


@app.route("/admin/pedidos/<token>/status", methods=["POST"])
def admin_pedido_status(token: str):
    """Avanca o status manualmente (ver services.pedidos.atualizar_status
    -- a MESMA funcao que um futuro webhook da Tiny vai chamar, so que
    automaticamente). Pra novo_status="enviado", so dispara o e-mail
    de "pedido enviado" se realmente for uma transicao nova (evita
    reenviar se o formulario for reenviado sem querer)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    pedido_antes = obter_pedido(token)
    if pedido_antes is None:
        abort(404)

    novo_status = str(request.form.get("status", "")).strip()
    codigo_rastreio = str(request.form.get("codigo_rastreio", "")).strip() or None
    link_rastreio = str(request.form.get("link_rastreio", "")).strip() or None

    pedido_atualizado = atualizar_status(
        token, novo_status, codigo_rastreio=codigo_rastreio, link_rastreio=link_rastreio
    )
    if pedido_atualizado is None:
        abort(400, description="Status inválido.")

    if novo_status == "enviado" and pedido_antes["status"] != "enviado":
        enviar_pedido_enviado(
            pedido_atualizado,
            pedido_atualizado.get("codigo_rastreio") or "",
            pedido_atualizado.get("link_rastreio") or "",
            url_for("ver_pedido", token=token, _external=True),
        )

    return redirect(url_for("admin_pedido_detalhe", token=token))


@app.route("/api/pix/gerar", methods=["POST"])
def api_pix_gerar():
    """Gera o Pix "copia e cola" + QR code com o valor do pedido ja
    preenchido (ver services/pix.py -- BR Code estatico com valor, sem
    integracao com API de banco)."""
    dados = request.get_json(silent=True) or {}
    try:
        valor = float(dados.get("valor", 0))
    except (TypeError, ValueError):
        return jsonify(erro="Valor invalido."), 400
    if valor <= 0:
        return jsonify(erro="Valor invalido."), 400

    txid = str(dados.get("txid") or "***")
    copia_cola = gerar_copia_cola(valor, txid)
    return jsonify(copia_cola=copia_cola, qr_data_uri=gerar_qr_data_uri(copia_cola))


_FAQ_PERSONALIZADA = [
    (
        "Posso enviar a foto de um santo menos conhecido, que não está no catálogo?",
        "Sim -- é literalmente pra isso que esse serviço existe. Envie a imagem que "
        "você já tem e simule antes de pedir.",
    ),
    (
        "Posso personalizar com foto de uma pessoa, não de um santo?",
        "Sim, pra casamentos, lembranças e relicários. Só imagens de cunho religioso "
        "precisam ser de devoção católica.",
    ),
    (
        "Vejo o resultado antes de pagar?",
        "Sim -- o simulador gera a prévia exata da peça, no formato escolhido, antes "
        "de você decidir.",
    ),
    (
        "Tem desconto de atacado pra personalizada?",
        "Tem sim -- a quantidade personalizada soma junto com o resto do carrinho "
        "pra faixa de desconto, do mesmo jeito que qualquer outro santo do catálogo.",
    ),
    (
        "Quanto tempo demora?",
        "O mesmo prazo do catálogo: produção em até 5 dias úteis após a confirmação "
        "do pagamento, mais o prazo de transporte.",
    ),
]


@app.route("/personalizada", methods=["GET"])
def personalizada():
    return render_template(
        "personalizada.html",
        preco_varejo=preco_varejo(),
        preco_varejo_chaveiro=preco_varejo("chaveiro"),
        dados_faq=_dados_faq(_FAQ_PERSONALIZADA),
    )


@app.route("/download/<token>")
def download(token: str):
    """Serve um download registrado por _registrar_download -- uso unico
    (removido assim que baixado) e expira em 15min se nunca for usado.
    Sempre como application/octet-stream (mesmo pras imagens PNG): no
    Safari do iOS, Content-Type image/* costuma so EXIBIR a imagem em vez
    de salvar, ignorando Content-Disposition -- octet-stream forca "baixar"."""
    entrada = _downloads.pop(token, None)
    if entrada is None or entrada[3] < time.time():
        abort(404, description="Link de download expirado ou já utilizado. Gere a imagem de novo.")
    dados, _mimetype_original, nome_arquivo, _ = entrada
    resposta = send_file(
        io.BytesIO(dados),
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=nome_arquivo,
    )
    resposta.headers["Cache-Control"] = "no-store"
    return resposta


@app.route("/api/personalizada/preview", methods=["POST"])
def api_personalizada_preview():
    """Uma imagem + recorte (opcional, ver editor de recorte em
    personalizada.js) + formato/cor -> previa da medalha (mostrada inline)
    + links de download reais pra previa e pro recorte quadrado 1:1."""
    arquivo = request.files.get("imagem")
    if not arquivo or not arquivo.filename:
        return jsonify(erro="Nenhuma imagem enviada."), 400
    if not _extensao_valida(arquivo.filename):
        return jsonify(erro="Formato invalido. Aceitos: " + ", ".join(IMAGE_EXTENSIONS)), 400

    formato = request.form.get("formato", "medalha")
    cor = request.form.get("cor") or None
    spec_id = _resolver_spec_id(formato, cor)
    if spec_id is None or spec_id not in MEDAL_SPECS:
        return jsonify(erro="Formato/cor invalido."), 400
    spec = MEDAL_SPECS[spec_id]

    box = _ler_box(request.form)
    with _salvar_temp(arquivo) as tmp:
        caminho = Path(tmp.name)
        try:
            resultado = compose_medal(spec, caminho, crop_box=box)
            recorte = _crop_quadrada(caminho, box)
        except Exception as exc:
            return jsonify(erro=f"Erro ao gerar a simulação: {exc}"), 400

    nome_base = _sem_extensao(arquivo.filename)
    token_preview = _registrar_download(
        _imagem_para_bytes(resultado), "image/png", f"{nome_base}_{spec_id}.png"
    )
    token_crop = _registrar_download(
        _imagem_para_bytes(recorte), "image/png", f"{nome_base}_recorte.png"
    )
    return jsonify(
        preview=_preview_data_uri(resultado),
        url_preview=f"/download/{token_preview}",
        url_crop=f"/download/{token_crop}",
    )


@app.errorhandler(404)
def pagina_nao_encontrada(erro):
    return render_template("404.html"), 404


def _enviar_lembretes_pedidos_pendentes() -> None:
    """Job agendado (ver _iniciar_scheduler_lembretes abaixo) -- roda a
    cada 10min, manda um lembrete (com link novo) pra pedido "pendente"
    ha´ mais de LEMBRETE_MINUTOS sem pagar. Sem CANONICAL_DOMAIN
    configurado nao ha´ como montar um link de verdade pro e-mail, entao
    so nao faz nada nesse caso (nunca manda um link quebrado)."""
    if not CANONICAL_DOMAIN:
        return
    candidatos = listar_pedidos_pendentes_para_lembrete(LEMBRETE_MINUTOS)
    if not candidatos:
        return
    with app.test_request_context(base_url=f"https://{CANONICAL_DOMAIN}"):
        for pedido in candidatos:
            cliente, endereco = _cliente_e_endereco_do_pedido(pedido)
            resultado_link = _gerar_link_pagamento_para_pedido(pedido, cliente, endereco)
            if "erro" in resultado_link:
                marcar_email_lembrete_enviado(pedido["token"], erro=resultado_link["erro"])
                continue
            resultado_email = enviar_lembrete_pedido_pendente(
                pedido, resultado_link["url"], url_for("ver_pedido", token=pedido["token"], _external=True)
            )
            marcar_email_lembrete_enviado(pedido["token"], erro=resultado_email.get("erro"))


def _iniciar_scheduler_lembretes() -> None:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(_enviar_lembretes_pedidos_pendentes, "interval", minutes=10, id="lembretes_pedidos_pendentes")
    scheduler.start()


# So liga em producao de verdade (ENABLE_SCHEDULER=true no servidor) --
# nunca em teste/dev, senao sobe uma thread de fundo rodando de
# verdade a cada import do modulo (ver config.py).
if ENABLE_SCHEDULER:
    _iniciar_scheduler_lembretes()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
