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
import io
import secrets
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_file, url_for
from PIL import Image
from werkzeug.datastructures import FileStorage

from config import (
    DESCRICOES_CATEGORIA,
    DESCRICOES_FORMATO,
    DESTAQUES_HOME,
    GA4_MEASUREMENT_ID,
    INSTAGRAM_URL,
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
    slugify,
)
from services.paginas_institucionais import PAGINAS_ATENDIMENTO
from services.catalogo_pdf import gerar_pdf_catalogo
from services.frete import calcular_frete
from services.pix import gerar_copia_cola, gerar_qr_data_uri
from services.gerador.compositor import auto_cover_box, compose_medal, crop_to_box, load_rgba
from services.gerador.config import IMAGE_EXTENSIONS, MEDAL_SPECS
from services.pricing import CHAVES_PRECO, calcular_carrinho, preco_varejo

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024  # 60MB no total do upload


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
        "instagram_url": INSTAGRAM_URL,
        "ano_atual": datetime.now(timezone.utc).year,
        "dados_organizacao": _dados_organizacao(),
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


def _montar_destaques(itens_por_id: dict) -> list[dict]:
    """Monta os grupos de destaques da home (DESTAQUES_HOME em config.py)
    a partir dos itens ja carregados -- ids que nao existirem mais no
    catalogo sao ignorados silenciosamente, nao quebram a pagina."""
    destaques = []
    for grupo in DESTAQUES_HOME:
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
    caminhos = [url_for("index"), url_for("carrinho"), url_for("personalizada")]
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


@app.route("/", methods=["GET"])
def index():
    produtos = carregar_produtos()
    itens = [
        {
            "id": p["id"],
            "nome": p["nome"],
            "categoria": p["categoria"],
            "thumbnail": p["modelos"][0]["imagem"],
            "thumbnail_chaveiro": p["modelos"][0]["imagem_chaveiro"],
        }
        for p in produtos
    ]
    categorias = categorias_com_slug(produtos)
    itens_por_id = {item["id"]: item for item in itens}
    destaques = _montar_destaques(itens_por_id)
    procurados = [itens_por_id[pid] for pid in PROCURADOS_HOME if pid in itens_por_id]
    return render_template(
        "index.html",
        produtos=itens,
        categorias=categorias,
        preco_varejo=preco_varejo(),
        destaques=destaques,
        procurados=procurados,
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
    return render_template(
        "pagina_atendimento.html", pagina=pagina, slug=slug, dados_breadcrumb=dados_breadcrumb
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


@app.route("/personalizada", methods=["GET"])
def personalizada():
    return render_template(
        "personalizada.html",
        preco_varejo=preco_varejo(),
        preco_varejo_chaveiro=preco_varejo("chaveiro"),
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
