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
do `mockup` -- previa/recorte gerados sao guardados de forma DURAVEL
(SQLite, ver services/imagens_personalizadas.py e
servir_imagem_personalizada abaixo), nunca em memoria do processo.
"""

from __future__ import annotations

import base64
import csv
import hmac
import io
import os
import re
import secrets
import tempfile
import threading
import zipfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as escapar_xml

from flask import Flask, Response, abort, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from PIL import ExifTags, Image, ImageOps
from pillow_heif import register_heif_opener
from werkzeug.datastructures import FileStorage

# Fotos de iPhone vem em HEIC/HEIF por padrao (nao JPEG) -- sem isso,
# Image.open() nao reconhece o arquivo e tanto o upload da personalizada
# quanto o de avaliacoes (ver /api/avaliacoes abaixo) falham pra quem
# manda foto direto da galeria do iPhone sem converter antes.
register_heif_opener()

from apscheduler.schedulers.background import BackgroundScheduler

from config import (
    ADMIN_PASSWORD,
    ADMIN_USER,
    AVALIACAO_SEGUIMENTO_DIAS_APOS_ENTREGA,
    CANCELAMENTO_MINUTOS_APOS_LEMBRETE,
    CANONICAL_DOMAIN,
    CATEGORIA_PERSONALIZADOS,
    COMBOS_2LADOS_PRONTOS,
    DESCRICOES_CATEGORIA,
    DESCRICOES_FORMATO,
    DESTAQUES_HOME,
    ENABLE_SCHEDULER,
    FAIXAS_PRODUCAO_DIAS_UTEIS,
    GA4_MEASUREMENT_ID,
    GOOGLE_SITE_VERIFICATION,
    INSTAGRAM_URL,
    KIT_LIVRARIA_SHALOM,
    LEMBRETE_MINUTOS,
    META_PIXEL_ID,
    PROCURADOS_HOME,
    PRODUCAO_DIAS_UTEIS,
    PRODUTOS_PERSONALIZADOS,
    PRODUTOS_TITULO_ANTIGO,
    PROVA_SOCIAL,
    RETENCAO_IMAGENS_PEDIDO_CANCELADO_DIAS,
    SECRET_KEY,
    UPSELL_HORAS_APOS_PAGAMENTO,
    VENDAS_RECENTES_DIAS,
    VENDAS_RECENTES_MINIMO_PARA_EXIBIR,
    VIDEO_APRESENTACAO_URL,
    WEBHOOK_INFINITEPAY_SECRET,
    WHATSAPP_NUMBER,
)
import services.analytics as analytics
from services.catalogo import (
    buscar_produto,
    carregar_produtos,
    categoria_por_slug,
    categorias_com_slug,
    normalizar_busca,
    slugify,
)
from services.paginas_institucionais import PAGINAS_ATENDIMENTO
from services.blog import ARTIGOS_BLOG, artigo_por_produto_id
from services.landing_paginas import PAGINAS_LANDING
from services.catalogo_pdf import gerar_pdf_catalogo
from services.avaliacoes import (
    atualizar_status as atualizar_status_avaliacao,
    criar_avaliacao,
    listar_avaliacoes,
    listar_avaliacoes_aprovadas,
    media_e_total_aprovadas,
    medias_e_totais_aprovadas,
)
from services.push import (
    enviar_notificacao as enviar_notificacao_push,
    obter_application_server_key,
    remover_subscription as remover_push_subscription,
    salvar_subscription as salvar_push_subscription,
)
from services.email import (
    enviar_boleto_gerado,
    enviar_codigo_verificacao,
    enviar_confirmacao_pedido,
    enviar_lembrete_pedido_pendente,
    enviar_link_pagamento,
    enviar_nota_fiscal_disponivel,
    enviar_notificacao_venda,
    enviar_oportunidade_upsell,
    enviar_pedido_avaliacao,
    enviar_pedido_cancelado,
    enviar_pedido_enviado,
    enviar_pedido_excluido,
    enviar_pedido_recompra,
)
from services.documentos import cpf_valido, documento_valido, numero_whatsapp, telefone_valido
from services.frete import calcular_frete, logo_transportadora
from services.infinitepay import criar_link_pagamento
from services.pedidos import (
    ESTAGIOS_RECOMPRA_DIAS,
    arquivar_pedido,
    atualizar_status,
    cancelar_pedido,
    confirmar_venda_manual,
    contagem_pedidos_por_status,
    criar_pedido,
    desarquivar_pedido,
    editar_item_formato,
    editar_valor,
    email_para_documento,
    estatisticas_hoje,
    excluir_pedido,
    gerar_codigo_verificacao_documento,
    limpar_codigos_verificacao_expirados,
    listar_pedidos,
    listar_pedidos_boleto_pendentes,
    listar_pedidos_cancelados_para_limpar_imagens,
    listar_pedidos_entregues_para_recompra,
    listar_pedidos_entregues_para_seguimento_avaliacao,
    listar_pedidos_pagos_para_upsell,
    listar_pedidos_pendentes_para_cancelar,
    listar_pedidos_pendentes_para_lembrete,
    listar_pedidos_por_documento,
    marcar_boleto_erro,
    marcar_email_avaliacao_enviado,
    marcar_email_avaliacao_seguimento_enviado,
    marcar_email_cancelado_enviado,
    marcar_email_recompra_enviado,
    marcar_email_enviado,
    marcar_email_lembrete_enviado,
    marcar_email_pedido_criado_enviado,
    marcar_email_nota_fiscal_enviado,
    marcar_email_pedido_enviado_enviado,
    marcar_email_upsell_enviado,
    marcar_imagens_pedido_apagadas,
    marcar_notificacao_venda_enviada,
    marcar_pago,
    marcar_tiny_sincronizado,
    numero_modelo_personalizada,
    obter_pedido,
    pedidos_por_uf,
    previsoes_do_pedido,
    produtos_mais_vendidos,
    quantidade_por_material,
    reativar_pedido_cancelado,
    resumo_vendas_periodo,
    salvar_dados_boleto_inter,
    taxa_cancelamento,
    taxa_clientes_recorrentes,
    formas_pagamento_periodo,
    unidades_vendidas_por_produto,
    vendas_por_dia,
    verificar_codigo_documento,
)
from services.imagens_personalizadas import (
    apagar_imagens,
    marcar_imagem_usada,
    obter_imagem,
    purgar_imagens_antigas,
    salvar_imagem,
)
from services.inter import baixar_pdf, consultar_cobranca, emitir_boleto
from services.pix import gerar_copia_cola, gerar_qr_data_uri
from services.tiny import buscar_contatos_tiny, criar_pedido_tiny, erro_e_duplicidade
from services.gerador.compositor import auto_cover_box, compose_medal, crop_to_box, load_rgba
from services.gerador.config import IMAGE_EXTENSIONS, MEDAL_SPECS
from services.pricing import CHAVES_PRECO, calcular_carrinho, preco_varejo, tabela_de_faixas

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024  # 60MB no total do upload
# Assina o cookie de sessao de /meus-pedidos (ver config.py:SECRET_KEY) --
# sem SECRET_KEY configurado (dev/teste), cai numa chave aleatoria gerada
# na subida do processo: login funciona, mas invalida sozinho a cada
# restart (aceitavel fora de producao).
app.secret_key = SECRET_KEY or secrets.token_urlsafe(32)

# Limite de requisicoes por IP nos endpoints publicos que custam algo
# de verdade (chamam API externa paga/com limite, mandam e-mail, geram
# imagem) -- protege contra abuso/spam automatizado sem incomodar
# gente de verdade usando o site normalmente (ver conversa "tornar o
# site e apis seguros"). storage_uri="memory://" e´ seguro aqui porque
# o gunicorn roda com 1 worker (processo) so (render.yaml) -- as varias
# THREADS desse worker (--worker-class gthread --threads 8) compartilham
# a MESMA memoria, entao continuam contando pro mesmo limite certinho.
# Se um dia isso mudar pra mais workers (processos, nao threads),
# precisa trocar pra um storage compartilhado (Redis) senao cada
# processo conta separado.
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")


@limiter.request_filter
def _pular_rate_limit_em_teste() -> bool:
    """Sem isso, os testes (que reusam o mesmo processo/limiter pra
    centenas de chamadas nos mesmos endpoints) comecam a tomar 429 no
    meio da suite -- TESTING=True so e´ ligado pelos fixtures de teste
    (ver tests/*.py), nunca em producao."""
    return app.testing

# Atras do proxy do Render (TLS termina la, chega no gunicorn como HTTP
# "puro") -- sem isso, request.scheme/url_for(_external=True) nao sabem
# que a conexao original era https (afeta os links https:// mandados
# por e-mail e pro checkout da InfinitePay).
from werkzeug.middleware.proxy_fix import ProxyFix  # noqa: E402

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# /static/* servido pelo WhiteNoise, ANTES de chegar no roteamento do
# Flask -- ver conversa "auditoria Claude in Chrome": o handler padrao
# de arquivo estatico do Flask e´ pensado pra desenvolvimento, nao pra
# producao -- numa home com 30+ imagens carregando juntas, isso
# contribuia pra imagem quebrada de forma intermitente (a mesma imagem
# carregava normal se pedida sozinha, so falhava sob disputa por
# atencao do processo -- resolvido em conjunto com "--threads 8" no
# render.yaml). WhiteNoise serve o arquivo de forma mais leve e ja
# manda Cache-Control -- curto pros arquivos daqui, que nao tem hash no
# nome (nao dava pra usar cache longo/imutavel sem isso, senao um
# deploy que troca o CONTEUDO de "logo-icone.png" mantendo o MESMO
# nome ficaria servindo a versao antiga do cache do navegador por
# muito tempo).
from whitenoise import WhiteNoise  # noqa: E402

app.wsgi_app = WhiteNoise(app.wsgi_app, root="static/", prefix="static/")


@app.after_request
def _cabecalhos_seguranca(resposta: Response) -> Response:
    """Headers de seguranca basicos (nenhum deles muda comportamento pra
    quem usa o site normalmente) -- ver conversa "tornar o site e apis
    seguros". CSP permite 'unsafe-inline' pra scripts/estilos porque o
    site usa varios <script> inline (ex: window.WHATSAPP_NUMBER em
    carrinho.html) -- nao e´ protecao completa contra XSS, mas fecha a
    porta mais comum de abuso (carregar/mandar dado pra dominio externo
    nao listado)."""
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resposta.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resposta.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://connect.facebook.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        # blob: e´ obrigatorio -- static/js/personalizada.js carrega a
        # foto que o cliente envia via URL.createObjectURL(file) antes
        # de desenhar no canvas do editor de recorte; sem isso a
        # simulacao trava logo no upload (ja aconteceu, ver conversa).
        "img-src 'self' data: blob: https:; "
        "media-src 'self' https:; "
        "connect-src 'self' https://viacep.com.br https://www.google-analytics.com https://analytics.google.com "
        "https://www.facebook.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return resposta


def _origem_admite_mesma_origem() -> bool:
    """Confere Origin (ou Referer, quando o navegador nao manda Origin
    em POST classico de formulario) contra o host da propria request --
    usado nas rotas admin que MUDAM estado (ver decorator abaixo). O
    painel usa HTTP Basic (sem cookie de sessao), mas o navegador
    reenvia a credencial cacheada automaticamente em qualquer request
    pro mesmo dominio -- inclusive uma vinda de um form em outro site
    (CSRF classico). Sem sessao/cookie nao da pra usar token CSRF
    tradicional, entao a defesa aqui e conferir que o pedido realmente
    veio de uma pagina do proprio site."""
    origem = request.headers.get("Origin") or request.headers.get("Referer")
    if not origem:
        # navegadores modernos sempre mandam Origin em POST -- sem
        # nenhum dos dois headers, mais provavel ser script/ferramenta
        # de linha de comando (curl, painel usado por script) do que
        # navegador real; nao bloqueia esse caso pra nao quebrar
        # integracoes/uso via API do proprio dono.
        return True
    host_pedido = urlsplit(origem).netloc
    return host_pedido == request.host


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


@app.before_request
def _bloquear_post_admin_de_outra_origem():
    """CSRF cross-origin em cima do painel admin (ver
    _origem_admite_mesma_origem acima) -- so se aplica a POST em rotas
    /admin/*, que sao sempre mudanca de estado nesse painel (nunca so
    leitura)."""
    if request.method == "POST" and request.path.startswith("/admin/") and not _origem_admite_mesma_origem():
        abort(403)


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


def _dados_artigo_schema(artigo: dict, url_artigo: str, imagem_url: str) -> dict:
    """Schema.org BlogPosting -- pros artigos de /blog (ver
    services/blog.py) aparecerem melhor formatados na busca do Google
    (autor, data de publicacao, imagem)."""
    return {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": artigo["titulo"],
        "description": artigo["resumo"],
        "image": imagem_url,
        "datePublished": artigo["publicado_em"],
        "author": {"@type": "Organization", "name": "Nove de Julho"},
        "publisher": {"@type": "Organization", "name": "Nove de Julho"},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url_artigo},
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


def _tabelas_desconto_para_template() -> list[dict]:
    """[{"titulo": ..., "faixas": [...]}, ...] -- um bloco por GRUPO de
    atacado (ver services/pricing.py) pro popup de faixas de desconto
    acionado pelo aviso "desconto progressivo" do topo (ver
    templates/base.html) -- cada grupo tem tabela propria, entao
    aparecem 3 tabelas separadas em vez de uma so."""
    return [
        {"titulo": "Medalha e entremeio (1 lado)", "faixas": tabela_de_faixas("16mm")},
        {"titulo": "Chaveiro (1 ou 2 lados)", "faixas": tabela_de_faixas("chaveiro")},
        {"titulo": "Medalha e entremeio de 2 lados", "faixas": tabela_de_faixas("medalha_2lados")},
    ]


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
        "tabelas_desconto": _tabelas_desconto_para_template(),
    }


CropBox = tuple[float, float, float, float]

# Formato/cor (escolhidos na tela, ver produto.js/personalizada.js) -> id de
# MEDAL_SPECS (services/gerador/config.py). "medalha" e o mesmo mockup
# independente do tamanho (12mm/16mm sao so o tamanho fisico impresso, a
# simulacao visual e identica) -- so entremeio muda de spec conforme a cor.
# entremeio_2lados reaproveita EXATAMENTE as mesmas specs do entremeio de
# 1 lado (mesma base fisica, so aplicada nos dois lados -- ver conversa);
# medalha_2lados usa as specs novas, uma por cor (ver services/gerador/
# config.py:medalha_2lados_prata/ouro_velho).
FORMATO_PARA_SPEC = {
    ("medalha", None): "prata_16mm",
    ("entremeio", "prata"): "entremeio_prata",
    ("entremeio", "ouro_velho"): "entremeio_ouro_velho",
    ("chaveiro", None): "chaveiro",
    ("chaveiro_2lados", None): "chaveiro_2lados",
    ("medalha_2lados", "prata"): "medalha_2lados_prata",
    ("medalha_2lados", "ouro_velho"): "medalha_2lados_ouro_velho",
    ("entremeio_2lados", "prata"): "entremeio_prata",
    ("entremeio_2lados", "ouro_velho"): "entremeio_ouro_velho",
}


def _formatar_preco(valor: float) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


# Todo timestamp do banco (criado_em/pago_em/entregue_em etc.) e´ salvo
# em UTC (datetime.now(timezone.utc).isoformat(), ver services/
# pedidos.py) -- sem converter pro fuso de Natal/Brasilia (UTC-3, sem
# horario de verao desde 2019) antes de mostrar, todo horario no
# painel aparecia 3h adiantado (ver conversa). ZoneInfo em vez de um
# "-3h" fixo pra continuar certo se o Brasil um dia voltar a ter
# horario de verao.
FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")


def _para_fuso_brasil(valor) -> datetime | None:
    if valor is None:
        return None
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor)
    if valor.tzinfo is not None:
        valor = valor.astimezone(FUSO_BRASIL)
    return valor


def _formatar_data_br(valor) -> str:
    valor = _para_fuso_brasil(valor)
    return valor.strftime("%d/%m/%Y") if valor else ""


def _formatar_data_hora_br(valor) -> str:
    valor = _para_fuso_brasil(valor)
    return valor.strftime("%d/%m/%Y %H:%M") if valor else ""


app.jinja_env.filters["preco"] = _formatar_preco
app.jinja_env.filters["data_br"] = _formatar_data_br
app.jinja_env.filters["data_hora_br"] = _formatar_data_hora_br
app.jinja_env.filters["whatsapp"] = numero_whatsapp
# Registrado como global (nao filtro) pra poder ser chamado direto nos
# templates do painel admin com o pedido inteiro (ver
# services.pedidos.previsoes_do_pedido).
app.jinja_env.globals["previsoes_do_pedido"] = previsoes_do_pedido
app.jinja_env.globals["logo_transportadora"] = logo_transportadora


def _extensao_valida(nome_arquivo: str) -> bool:
    nome_lower = nome_arquivo.lower()
    return any(nome_lower.endswith(ext) for ext in IMAGE_EXTENSIONS)


# Tamanho maximo (lado maior) da foto de avaliacao guardada -- fotos de
# celular costumam vir com varios MB, e essa foto e´ salva como data URI
# direto na coluna `foto` da tabela avaliacoes (mesmo SQLite de
# services/pedidos.py, sem disco separado pra arquivo). Reduzir aqui
# evita o banco inchar; qualidade JPEG 78 mantem a foto reconhecivel
# sem pesar.
_AVALIACAO_FOTO_LADO_MAXIMO = 1000


def _foto_avaliacao_para_data_uri(arquivo: FileStorage) -> str:
    imagem = Image.open(arquivo.stream)
    imagem = imagem.convert("RGB")
    imagem.thumbnail((_AVALIACAO_FOTO_LADO_MAXIMO, _AVALIACAO_FOTO_LADO_MAXIMO))
    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=78)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _resolver_spec_id(formato: str, cor: str | None) -> str | None:
    return FORMATO_PARA_SPEC.get((formato, cor))



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


# O servidor roda com 1 processo gunicorn e 8 threads (ver render.yaml)
# -- todas compartilham a mesma memoria, entao 2+ uploads pesados
# processando ao mesmo tempo somam os picos em vez de ficarem isolados
# (ver conversa: caiu com "exceeded its memory limit" bem na hora de
# subir 2 fotos de celular juntas pela personalizada). Esse semaforo
# serializa so a parte pesada (abrir/reduzir/compor a imagem) -- uploads
# extras esperam alguns segundos na fila em vez de estourarem a memoria
# junto; o timeout fica abaixo do --timeout 90 do gunicorn pra devolver
# um erro tratavel em vez do worker inteiro travar esperando.
_LIMITE_PROCESSAMENTO_IMAGEM_PESADO = threading.Semaphore(1)
_TIMEOUT_ESPERA_PROCESSAMENTO_SEGUNDOS = 60


# Fotos de celular moderno passam facil de 12-48MP -- processar em
# resolucao total (compose_medal/_crop_quadrada, que carregam a imagem
# inteira em memoria varias vezes com PIL/numpy pra compor a medalha)
# pode estourar a memoria do processo, pra uma peca que sai impressa
# com 1,2 a 3cm de diametro (ver conversa: alerta real do Render
# "exceeded its memory limit", log mostrando POST
# /api/personalizada/preview bem no pico). O canvas final da medalha
# (services/gerador/assets/base_medalha.png etc.) e´ so 1254x1254px, com
# a foto do cliente preenchendo um circulo de ~890px de diametro
# (INNER_RADIUS_FRAC=0.355 em services/gerador/config.py) -- 1600px da´
# bastante folga pra recorte/zoom manual sem nunca precisar de mais que
# isso.
_FOTO_PERSONALIZADA_LADO_MAXIMO = 1600


def _reduzir_temp_se_grande_demais(caminho: Path, box: "CropBox | None") -> "CropBox | None":
    """Reduz o arquivo temporario ANTES do processamento pesado, se
    algum lado passar de _FOTO_PERSONALIZADA_LADO_MAXIMO. `box` (se
    informado) vem em pixels da imagem ORIGINAL (ver
    services/gerador/compositor.py:crop_to_box) -- precisa escalar na
    MESMA proporcao, senao o recorte manual do cliente sai deslocado
    depois que a imagem encolhe."""
    with Image.open(caminho) as arquivo_original:
        # Tamanho e orientacao vem do cabecalho, leitura barata que nao
        # decodifica pixel nenhum -- precisa ser lido ANTES do draft()
        # abaixo, que ja´ muda o `.size` aparente do objeto pra escala
        # reduzida. `box` vem em pixels da imagem original *ja´
        # corrigida* pela orientacao EXIF (mesmo referencial que
        # exif_transpose produz), entao troca largura/altura aqui se a
        # orientacao for uma que roda 90/270 graus.
        largura_bruta, altura_bruta = arquivo_original.size
        orientacao = arquivo_original.getexif().get(ExifTags.Base.Orientation, 1)
        troca_lados = orientacao in (5, 6, 7, 8)
        largura, altura = (altura_bruta, largura_bruta) if troca_lados else (largura_bruta, altura_bruta)
        maior_lado = max(largura, altura)
        if maior_lado <= _FOTO_PERSONALIZADA_LADO_MAXIMO:
            return box
        fator = _FOTO_PERSONALIZADA_LADO_MAXIMO / maior_lado

        # draft() pede pro decoder de JPEG decodificar ja´ numa escala
        # reduzida (1/2, 1/4...), em vez de decodificar os 12-48MP
        # inteiros pra so´ depois encolher -- corta o pico de memoria
        # bem na raiz pra fotos JPEG (a maioria fora do iPhone/HEIC, que
        # nao suporta draft e cai no caminho normal abaixo mesmo assim).
        # O resize() final sempre mira no tamanho calculado a partir do
        # ORIGINAL (acima), entao o resultado fica identico independente
        # de em que escala o draft decodificou.
        arquivo_original.draft("RGB", (_FOTO_PERSONALIZADA_LADO_MAXIMO, _FOTO_PERSONALIZADA_LADO_MAXIMO))
        imagem = ImageOps.exif_transpose(arquivo_original)
        imagem = imagem.resize(
            (max(1, round(largura * fator)), max(1, round(altura * fator))), Image.LANCZOS
        )
    # "with" fecha e libera o buffer decodificado do arquivo original
    # aqui, ANTES do save -- exif_transpose/resize sempre devolvem uma
    # imagem propria, entao `imagem` continua valida depois que
    # arquivo_original fecha.
    parametros_save = {"quality": 90} if caminho.suffix.lower() in (".jpg", ".jpeg") else {}
    imagem.save(caminho, **parametros_save)

    if box is None:
        return None
    x1, y1, x2, y2 = box
    return (x1 * fator, y1 * fator, x2 * fator, y2 * fator)


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
            destaques.append({"chave": grupo.get("chave", ""), "titulo": grupo["titulo"], "produtos": produtos_grupo})
    return destaques


@app.route("/robots.txt", methods=["GET"])
def robots_txt():
    linhas = ["User-agent: *", "Allow: /", f"Sitemap: {request.url_root}sitemap.xml"]
    return Response("\n".join(linhas), mimetype="text/plain")


# Data usada como <lastmod> pra tudo no sitemap -- calculada uma vez
# quando o processo sobe (proxy de "conteudo como estava nesse
# deploy"). Nao ha data de edicao por produto (data/produtos.json nao
# guarda isso, e adicionar so pra isso seria manutencao manual sujeita
# a erro) -- um lastmod unico e honesto e´ melhor que nenhum ou que um
# inventado por item.
_SITEMAP_LASTMOD = datetime.now(timezone.utc).strftime("%Y-%m-%d")


@app.route("/sitemap.xml", methods=["GET"])
def sitemap_xml():
    produtos = carregar_produtos()
    # (caminho, changefreq, priority) -- home/catalogo primeiro (mais
    # importantes e mudam mais), produto/categoria no meio, paginas
    # institucionais e carrinho (nao e´ conteudo de busca) por ultimo.
    entradas = [
        (url_for("index"), "weekly", "0.8"),
        (url_for("catalogo_completo"), "weekly", "0.8"),
        (url_for("personalizada"), "monthly", "0.7"),
        (url_for("kit_livraria_shalom"), "monthly", "0.6"),
        (url_for("cruz_para_terco"), "monthly", "0.6"),
        (url_for("carrinho"), "yearly", "0.1"),
    ]
    entradas += [(url_for("landing_pagina", slug=s), "monthly", "0.6") for s in PAGINAS_LANDING]
    entradas += [
        (url_for("categoria", slug=c["slug"]), "weekly", "0.7") for c in categorias_com_slug(produtos)
    ]
    entradas += [(url_for("produto", produto_id=p["id"]), "monthly", "0.6") for p in produtos]
    entradas += [(url_for("pagina_atendimento", slug=s), "yearly", "0.3") for s in PAGINAS_ATENDIMENTO]
    entradas.append((url_for("blog_indice"), "monthly", "0.6"))
    entradas += [(url_for("blog_artigo", slug=s), "yearly", "0.5") for s in ARTIGOS_BLOG]

    base = request.url_root.rstrip("/")
    itens_xml = "".join(
        f"<url><loc>{(base + caminho).replace('&', '&amp;')}</loc>"
        f"<lastmod>{_SITEMAP_LASTMOD}</lastmod>"
        f"<changefreq>{changefreq}</changefreq>"
        f"<priority>{priority}</priority></url>"
        for caminho, changefreq, priority in entradas
    )
    corpo = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + itens_xml + "</urlset>"
    )
    return Response(corpo, mimetype="application/xml")


@app.route("/llms.txt", methods=["GET"])
def llms_txt():
    base = request.url_root.rstrip("/")
    produtos = carregar_produtos()
    categorias = categorias_com_slug(produtos)
    linhas_categorias = "\n".join(
        f"- [{c['nome']}]({base}{url_for('categoria', slug=c['slug'])})" for c in categorias
    )
    linhas_landing = "\n".join(
        f"- [{p['titulo']}]({base}{url_for('landing_pagina', slug=s)}): {p['resumo']}"
        for s, p in PAGINAS_LANDING.items()
    )
    corpo = f"""# Nove de Julho -- Catálogo de Atacado

> Catálogo de atacado de medalhas, entremeios e chaveiros religiosos católicos,
> resinados -- medalha de 1 lado em aço inoxidável, os demais formatos em liga
> de zinco. Mais de 130 santos e devoções, com desconto de atacado automático
> por quantidade (sem cupom) e opção de peça personalizada a partir de foto
> enviada pelo cliente.

Site institucional/loja da Nove de Julho, empresa brasileira. Preços em Real
(R$), pagamento via Pix (padrão), cartão em até 12x ou boleto, com nota fiscal
para CPF ou CNPJ. Pedido mínimo de R$ 30 em produtos (frete calculado à parte);
frete grátis para o Brasil todo acima de R$ 300 em compras. Produção sob
encomenda: de 5 a 10 dias úteis após confirmação do pagamento, prazo que cresce
com a quantidade total do pedido (500+ peças: 7 dias úteis; 1000+: 8 dias
úteis; 2000+: 10 dias úteis).

## Páginas principais

- [Catálogo completo]({base}{url_for('catalogo_completo')}): todos os santos e devoções disponíveis
- [Medalha personalizada]({base}{url_for('personalizada')}): envio de foto própria, com simulação antes de pedir
- [Kit Livraria Shalom]({base}{url_for('kit_livraria_shalom')}): sortimento pronto com os santos mais vendidos
- [Cruz para Terço]({base}{url_for('cruz_para_terco')}): cruz avulsa (prata, ouro velho ou dourado) pra completar o terço
- [Quem somos]({base}{url_for('pagina_atendimento', slug='quem-somos')}): história da marca e do fundador
- [Blog]({base}{url_for('blog_indice')}): história e significado dos santos e devoções do catálogo

## Páginas por público/uso

{linhas_landing}

## Categorias

{linhas_categorias}

## Formatos disponíveis por santo/devoção

Medalha, entremeio (para terço) e chaveiro -- cada um com opções de tamanho
e/ou cor conforme o modelo.

## Observações para agentes

- Preços de atacado variam por faixa de quantidade total no carrinho e são
  calculados automaticamente; não há tabela estática confiável fora do site.
- Sitemap completo em [/sitemap.xml]({base}/sitemap.xml).
"""
    return Response(corpo, mimetype="text/plain")


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


def _com_avaliacoes(itens: list[dict]) -> list[dict]:
    """Anexa media_avaliacoes/total_avaliacoes em cada item do grid (ver
    _itens_do_grid/_itens_personalizados_do_grid abaixo) pra estrelinha
    aparecer no card do catalogo/home/categoria -- uma query so´ pra
    tudo (ver services/avaliacoes.py:medias_e_totais_aprovadas), em vez
    de bater no banco uma vez por produto a cada carregamento de
    pagina. Produto sem avaliacao aprovada fica sem as duas chaves de
    proposito (ver conversa: melhor nao mostrar nada do que 5 estrelas
    cinza, que pareceria nota zero em vez de "ainda sem avaliacao")."""
    medias = medias_e_totais_aprovadas()
    for item in itens:
        media_total = medias.get(item["id"])
        if media_total:
            item["media_avaliacoes"], item["total_avaliacoes"] = media_total
    return itens


def _com_vendas_recentes(itens: list[dict]) -> list[dict]:
    """Anexa vendas_recentes (unidades) em cada item do grid quando bate
    VENDAS_RECENTES_MINIMO_PARA_EXIBIR nos ultimos VENDAS_RECENTES_DIAS
    dias (ver services/pedidos.py:unidades_vendidas_por_produto) --
    selo "X vendidas nos ultimos 30 dias" no card do catalogo/home/
    categoria. Produto abaixo do minimo fica sem a chave de proposito
    (ver conversa: numero baixo pareceria pouco procurado em vez de
    reforcar confianca -- so vale a pena mostrar quando e´ um numero
    que impressiona)."""
    vendas = unidades_vendidas_por_produto(VENDAS_RECENTES_DIAS)
    for item in itens:
        quantidade = vendas.get(item["id"], 0)
        if quantidade >= VENDAS_RECENTES_MINIMO_PARA_EXIBIR:
            item["vendas_recentes"] = quantidade
    return itens


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


def _itens_personalizados_do_grid() -> list[dict]:
    """"Produtos" da personalizada (config.py:PRODUTOS_PERSONALIZADOS) no
    MESMO formato de _itens_do_grid, pra entrar direto na grade/busca do
    catalogo -- so que "thumbnail" e´ o mockup real de cada peca (ver
    PRODUTOS_PERSONALIZADOS) e o card, em vez de ir pra /produto/<id>,
    manda pra /personalizada com o formato certo pre-selecionado (ver
    templates/catalogo.html e api_busca, que usam "personalizada_url"
    quando presente em vez de montar url_for('produto', ...)).
    thumbnail_chaveiro = thumbnail (sem "alt" de verdade pra esses cards --
    cada item ja e´ um formato especifico, nao um santo com varias fotos)."""
    return [
        {
            "id": p["id"],
            "nome": p["nome"],
            "categoria": CATEGORIA_PERSONALIZADOS,
            "thumbnail": p["thumbnail"],
            "thumbnail_chaveiro": p["thumbnail"],
            "personalizada_url": url_for("personalizada", formato=p["formato"]),
        }
        for p in PRODUTOS_PERSONALIZADOS
    ]


def _itens_combos_do_grid() -> list[dict]:
    """Combos "medalha de 2 lados" prontos (config.py:COMBOS_2LADOS_PRONTOS)
    no card da home (ver DESTAQUES_HOME "novidades") -- mesmo padrao de
    "personalizada_url" que _itens_personalizados_do_grid, so que aqui o
    link manda pra /personalizada com os 2 lados JA escolhidos
    (?combo=<id>, ver personalizada() abaixo e static/js/personalizada.js:
    tentarAutoPreencherCombo)."""
    return [
        {
            "id": c["id"],
            "nome": c["nome"],
            "thumbnail": c["thumbnail"],
            "thumbnail_chaveiro": c["thumbnail"],
            "personalizada_url": url_for("personalizada", formato="medalha_2lados", combo=c["id"]),
        }
        for c in COMBOS_2LADOS_PRONTOS
    ]


@app.route("/", methods=["GET"])
def index():
    """Home -- landing page comercial (hero, vantagens, destaques, banners),
    SEM a grade completa de produtos (fica em /catalogo, ver
    catalogo_completo abaixo) -- pedido do usuario pra manter a home mais
    limpa/curta, mostrando so 4 santos em destaque + botao pro catalogo
    inteiro."""
    produtos = carregar_produtos()
    itens = _com_vendas_recentes(_com_avaliacoes(_itens_do_grid(produtos)))
    itens_por_id = {item["id"]: item for item in itens}
    # combos "medalha de 2 lados" prontos (ver DESTAQUES_HOME "novidades")
    # entram no mesmo dict pra _montar_destaques resolver os ids deles
    # igual aos santos normais -- nao aparecem em mais nenhum outro lugar
    # (catalogo/busca), so nesse destaque da home.
    itens_por_id.update({item["id"]: item for item in _itens_combos_do_grid()})
    destaques = _montar_destaques(produtos, itens_por_id)
    # A home intercala esses 3 grupos com outras secoes (historia,
    # banner de preco automatico -- ver templates/index.html), entao
    # cada um precisa ser endereçavel por "chave" em vez de so um loop
    # unico -- um grupo sem produtos hoje (id removido do catalogo)
    # simplesmente some da home, sem quebrar nada.
    destaques_por_chave = {d["chave"]: d for d in destaques if d.get("chave")}
    procurados = [itens_por_id[pid] for pid in PROCURADOS_HOME if pid in itens_por_id]
    categorias = categorias_com_slug(produtos)
    # "Ultima chance" antes da grade generica de santos, pra quem rolou a
    # home inteira e ainda nao achou o que queria (ver conversa) -- reusa
    # _itens_personalizados_do_grid, que ja tem o formato certo
    # (personalizada_url) pro render_destaque da home.
    destaque_personalizados = {
        "titulo": "🎨 Não achou? Crie a sua peça personalizada",
        "produtos": _itens_personalizados_do_grid(),
    }
    return render_template(
        "index.html",
        preco_varejo=preco_varejo(),
        destaque_mais_vendidos=destaques_por_chave.get("mais_vendidos"),
        destaque_ano_jubilar=destaques_por_chave.get("ano_jubilar"),
        destaque_novidades=destaques_por_chave.get("novidades"),
        destaque_personalizados=destaque_personalizados,
        procurados=procurados,
        categorias=categorias,
        cores_cruz_terco=_cores_cruz_terco(),
    )


@app.route("/catalogo", methods=["GET"])
def catalogo_completo():
    """Grade completa com busca + filtro por categoria -- o que antes
    ficava direto na home. `?q=` (opcional) vem do campo de busca da home
    e pre-preenche o filtro aqui (ver static/js/catalogo.js)."""
    produtos = carregar_produtos()
    # produtos "personalizada" (config.py:PRODUTOS_PERSONALIZADOS) entram
    # no final da grade + como categoria propria pro cliente encontrar
    # procurando/filtrando, mesmo sem saber que a personalizada existe
    # (ver conversa). "Personalizada" nao tem pagina /categoria/<slug>
    # de verdade (nao e´ uma categoria de santo, ver categoria() abaixo)
    # -- slug=None faz o chip apontar pro proprio /catalogo em vez de 404.
    itens = _com_vendas_recentes(_com_avaliacoes(_itens_do_grid(produtos) + _itens_personalizados_do_grid()))
    categorias = categorias_com_slug(produtos) + [{"nome": CATEGORIA_PERSONALIZADOS, "slug": None}]
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


def _cores_cruz_terco() -> list[dict]:
    """3 cores da Cruz para Terco (ver cruz_para_terco/index abaixo) --
    fatorado numa funcao pra home e a pagina do produto usarem os MESMOS
    dados (preco sempre de precos.json via preco_varejo, nunca duplicado
    a mao)."""
    return [
        {
            "id": "prata",
            "nome": "Prata",
            "chave_preco": "cruz_terco_prata",
            "preco": preco_varejo("cruz_terco_prata"),
            "imagem_frente": url_for("static", filename="img/produtos/cruz_terco_prata_frente.jpg"),
            "imagem_perfil": url_for("static", filename="img/produtos/cruz_terco_prata_perfil.jpg"),
        },
        {
            "id": "ouro_velho",
            "nome": "Ouro velho",
            "chave_preco": "cruz_terco_ouro_velho",
            "preco": preco_varejo("cruz_terco_ouro_velho"),
            "imagem_frente": url_for("static", filename="img/produtos/cruz_terco_ouro_velho_frente.jpg"),
            "imagem_perfil": url_for("static", filename="img/produtos/cruz_terco_ouro_velho_perfil.jpg"),
        },
        {
            "id": "dourado",
            "nome": "Dourado",
            "chave_preco": "cruz_terco_dourado",
            "preco": preco_varejo("cruz_terco_dourado"),
            "imagem_frente": url_for("static", filename="img/produtos/cruz_terco_dourado_frente.jpg"),
            "imagem_perfil": url_for("static", filename="img/produtos/cruz_terco_dourado_perfil.jpg"),
        },
    ]


@app.route("/cruz-para-terco", methods=["GET"])
def cruz_para_terco():
    """Cruz pra terco (pedido em 2026-09-11, "Cruz do Papa"/"Cruz de Sao
    Joao Paulo II") -- pagina propria (nao usa o produto.html generico,
    ver conversa: nao tem santo/modelo, so 3 cores da MESMA peca fisica,
    4,2 x 1,7 cm), no mesmo padrao de pagina dedicada do /kit-livraria-
    shalom. Preco vem sempre de precos.json (preco_varejo), nunca
    hardcoded aqui -- prata/ouro velho R$2,50, dourado R$3,00 (pedido do
    usuario, sem tabela de atacado propria pra essa peca)."""
    cores = _cores_cruz_terco()
    dados_breadcrumb = _dados_breadcrumb(
        [
            ("Início", url_for("index", _external=True)),
            ("Cruz para Terço", url_for("cruz_para_terco", _external=True)),
        ]
    )
    return render_template(
        "cruz_terco.html",
        cores=cores,
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
    itens = _com_vendas_recentes(_com_avaliacoes(_itens_do_grid([p for p in produtos if p["categoria"] == nome_categoria])))
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

    avaliacoes_aprovadas = listar_avaliacoes_aprovadas(produto_id)
    media_avaliacoes, total_avaliacoes = media_e_total_aprovadas(produto_id)
    vendas_recentes_qtd = unidades_vendidas_por_produto(VENDAS_RECENTES_DIAS).get(produto_id, 0)
    vendas_recentes = vendas_recentes_qtd if vendas_recentes_qtd >= VENDAS_RECENTES_MINIMO_PARA_EXIBIR else None

    dados_produto = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": produto["nome"],
        "image": url_for("static", filename=produto["modelos"][0]["imagem"], _external=True),
        "brand": {"@type": "Brand", "name": "Nove de Julho"},
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
            # Search Console (Listagens do comerciante) tambem reportava
            # "validFrom nao foi encontrado (em offers)" -- preco eh valido
            # desde ja´ (renderizado por requisicao, sempre a data atual).
            "validFrom": datetime.now(timezone.utc).date().isoformat(),
            # "E preciso especificar validThrough ou priceValidUntil (em
            # offers)" -- preco pode mudar a qualquer momento (admin edita
            # data/precos.json), entao em vez de uma data fixa/distante,
            # declara uma janela curta que rola sozinha a cada requisicao
            # (hoje + 90 dias) -- nunca fica "vencida" pro Google enquanto a
            # pagina continuar sendo recrawleada dentro desse prazo.
            "priceValidUntil": (datetime.now(timezone.utc) + timedelta(days=90)).date().isoformat(),
            # Politica real de troca/devolucao (7 dias corridos, arrependimento
            # sem justificativa, frete de volta por nossa conta) -- ver
            # services/paginas_institucionais.py:"trocas-e-devolucao". Faltando
            # esse campo o Search Console reporta "hasMerchantReturnPolicy nao
            # foi encontrado (em offers)" nas Listagens do comerciante.
            "hasMerchantReturnPolicy": {
                "@type": "MerchantReturnPolicy",
                "applicableCountry": "BR",
                "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
                # nome certo confirmado -- "merchandiseReturnDays" (o que
                # tinha antes) NAO existe no vocabulario do Google, so
                # "merchantReturnDays" (ver conversa: Search Console
                # reportando "merchantReturnDays" nao encontrado mesmo com
                # merchandiseReturnDays presente).
                "merchantReturnDays": 7,
                "returnMethod": "https://schema.org/ReturnByMail",
                "returnFees": "https://schema.org/FreeReturn",
            },
            # Frete gratis Brasil todo (config.py: frete_gratis acima de
            # R$300) declarado aqui como padrao -- prazo de manuseio segue
            # PRODUCAO_DIAS_UTEIS/FAIXAS_PRODUCAO_DIAS_UTEIS (services/
            # pedidos.py) e o prazo de transporte 2 a 20 dias uteis ja usado
            # em services/paginas_institucionais.py. Faltando esse campo o
            # Search Console reporta "shippingDetails nao foi encontrado
            # (em offers)".
            "shippingDetails": {
                "@type": "OfferShippingDetails",
                "shippingRate": {"@type": "MonetaryAmount", "value": "0", "currency": "BRL"},
                "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "BR"},
                "deliveryTime": {
                    "@type": "ShippingDeliveryTime",
                    "handlingTime": {
                        "@type": "QuantitativeValue",
                        "minValue": PRODUCAO_DIAS_UTEIS,
                        "maxValue": max(FAIXAS_PRODUCAO_DIAS_UTEIS.values(), default=PRODUCAO_DIAS_UTEIS),
                        "unitCode": "d",
                    },
                    "transitTime": {
                        "@type": "QuantitativeValue",
                        "minValue": 2,
                        "maxValue": 20,
                        "unitCode": "d",
                    },
                },
            },
        },
    }
    # AggregateRating/Review so entram com dado REAL (avaliacao aprovada
    # no painel admin, nunca fabricado) -- ver services/avaliacoes.py.
    if total_avaliacoes > 0:
        dados_produto["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": media_avaliacoes,
            "reviewCount": total_avaliacoes,
        }
        dados_produto["review"] = [
            {
                "@type": "Review",
                "author": {"@type": "Person", "name": avaliacao["nome_cliente"]},
                "reviewRating": {"@type": "Rating", "ratingValue": avaliacao["nota"], "bestRating": 5},
                **({"reviewBody": avaliacao["texto"]} if avaliacao["texto"] else {}),
            }
            for avaliacao in avaliacoes_aprovadas
        ]
    dados_breadcrumb = _dados_breadcrumb(
        [
            ("Catálogo", url_for("index", _external=True)),
            (produto["categoria"], url_for("categoria", slug=categoria_slug, _external=True)),
            (produto["nome"], url_for("produto", produto_id=produto_id, _external=True)),
        ]
    )
    artigo_relacionado = artigo_por_produto_id(produto_id)
    return render_template(
        "produto.html",
        produto=produto,
        categoria_slug=categoria_slug,
        titulo_antigo=produto["id"] in PRODUTOS_TITULO_ANTIGO,
        relacionados=relacionados,
        preco_varejo=preco,
        preco_varejo_chaveiro=preco_varejo("chaveiro"),
        prova_social=PROVA_SOCIAL,
        descricoes_formato=DESCRICOES_FORMATO,
        dados_produto=dados_produto,
        dados_breadcrumb=dados_breadcrumb,
        avaliacoes=avaliacoes_aprovadas,
        media_avaliacoes=media_avaliacoes,
        total_avaliacoes=total_avaliacoes,
        vendas_recentes=vendas_recentes,
        slug_artigo_relacionado=artigo_relacionado[0] if artigo_relacionado else None,
        producao_dias_uteis=PRODUCAO_DIAS_UTEIS,
    )


def _produto_para_avaliar(produto_id: str) -> dict | None:
    """Resolve produto_id tanto do catalogo de santos quanto de
    PRODUTOS_PERSONALIZADOS (config.py) -- avaliar_produto/
    api_avaliacoes_criar abaixo precisam aceitar os dois (peca
    personalizada tambem pode ser avaliada, ver conversa). Normaliza
    os dois em {"id", "nome", "imagem"} (personalizada nao tem
    "modelos", so um thumbnail unico) pro template nao precisar saber
    a origem."""
    produto = buscar_produto(produto_id)
    if produto is not None:
        return {"id": produto["id"], "nome": produto["nome"], "imagem": produto["modelos"][0]["imagem"]}
    for p in PRODUTOS_PERSONALIZADOS:
        if p["id"] == produto_id:
            return {"id": p["id"], "nome": p["nome"], "imagem": p["thumbnail"]}
    return None


@app.route("/avaliar", methods=["GET"])
def avaliar_geral():
    """Mesma pagina isolada de avaliar_produto abaixo, so que sem
    produto pre-selecionado -- mostra um campo de busca (reaproveita
    /api/busca, mesmo usado na home) e o formulario so aparece depois
    de escolher o produto (ver static/js/avaliar_busca.js). Pensado pra
    mandar um UNICO link pra toda a base de clientes antiga, sem
    precisar de um link por produto (ver conversa)."""
    return render_template("avaliar.html", produto=None)


@app.route("/avaliar/<produto_id>", methods=["GET"])
def avaliar_produto(produto_id: str):
    """Pagina isolada so com o formulario de avaliacao (ver conversa --
    mandar o link da pagina de produto inteira pra base de clientes
    antiga faz a maioria desistir antes de chegar na secao de avaliar).
    Mesmo formulario/JS do produto.html (static/js/avaliacoes.js), so
    que ja aberto e sem o resto da pagina em volta. Usado pelo e-mail
    automatico de avaliacao (ja sabe qual produto pedir, ver
    _enviar_pedidos_para_avaliacao) -- pro link geral sem produto fixo,
    ver avaliar_geral acima."""
    produto = _produto_para_avaliar(produto_id)
    if produto is None:
        abort(404)
    return render_template("avaliar.html", produto=produto)


@app.route("/carrinho", methods=["GET"])
def carrinho():
    return render_template(
        "carrinho.html",
        producao_dias_uteis=PRODUCAO_DIAS_UTEIS,
        faixas_producao_dias_uteis=FAIXAS_PRODUCAO_DIAS_UTEIS,
    )


_REDIRECT_ATENDIMENTO_ALIASES = {
    # slugs da plataforma antiga (ver auditoria Search Console/conversa)
    # que viraram outro slug aqui -- 301 pra nao perder o SEO acumulado.
    "politicas-de-pagamento": "formas-de-pagamento",
    "politica-de-cookies": "termos-e-privacidade",
    "termos-de-uso-e-politica-de-privacidade": "termos-e-privacidade",
    "politica-de-devolucao-e-reembolso": "trocas-e-devolucao",
}


@app.route("/atendimento/<slug>", methods=["GET"])
def pagina_atendimento(slug: str):
    pagina = PAGINAS_ATENDIMENTO.get(slug)
    if pagina is None:
        alvo = _REDIRECT_ATENDIMENTO_ALIASES.get(slug)
        if alvo:
            return redirect(url_for("pagina_atendimento", slug=alvo), code=301)
        if slug == "precos-de-atacado":  # sem pagina equivalente hoje
            return redirect(url_for("catalogo_completo"), code=301)
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


def _thumbnail_do_artigo(artigo: dict) -> str:
    """Miniatura de um artigo do blog -- reaproveita a foto do proprio
    produto relacionado (ver services/blog.py), sem precisar de nenhuma
    imagem nova so pro blog. Artigo sem produto de catalogo (ex: a
    historia da propria loja, ver conversa) usa "imagem_manual" no
    lugar -- uma imagem de marca ja existente em static/img/."""
    produto_id = artigo.get("produto_relacionado_id")
    if produto_id:
        produto = buscar_produto(produto_id)
        if produto:
            return produto["modelos"][0]["imagem"]
    return artigo.get("imagem_manual", "")


def _url_cta_do_artigo(artigo: dict) -> str:
    """URL do botao principal do artigo (substitui __URL_PRODUTO__ no
    corpo, ver services/blog.py) -- pro produto relacionado quando
    existir, ou pra uma rota manual (`cta_endpoint`) quando o artigo
    nao for sobre um santo especifico do catalogo (ex: a historia da
    propria loja linkando pra /personalizada)."""
    produto_id = artigo.get("produto_relacionado_id")
    if produto_id:
        return url_for("produto", produto_id=produto_id, _external=True)
    return url_for(artigo["cta_endpoint"], _external=True)


@app.route("/blog", methods=["GET"])
def blog_indice():
    dados_breadcrumb = _dados_breadcrumb(
        [
            ("Catálogo", url_for("index", _external=True)),
            ("Blog", url_for("blog_indice", _external=True)),
        ]
    )
    artigos = [
        {"slug": slug, "thumbnail": _thumbnail_do_artigo(artigo), **artigo}
        for slug, artigo in sorted(ARTIGOS_BLOG.items(), key=lambda item: item[1]["publicado_em"], reverse=True)
    ]
    return render_template("blog_indice.html", artigos=artigos, dados_breadcrumb=dados_breadcrumb)


@app.route("/blog/<slug>", methods=["GET"])
def blog_artigo(slug: str):
    artigo = ARTIGOS_BLOG.get(slug)
    if artigo is None:
        abort(404)
    url_produto = _url_cta_do_artigo(artigo)
    corpo_html = artigo["corpo_html"].replace("__URL_PRODUTO__", url_produto)
    imagem_url = url_for("static", filename=_thumbnail_do_artigo(artigo), _external=True)
    url_artigo = url_for("blog_artigo", slug=slug, _external=True)
    dados_breadcrumb = _dados_breadcrumb(
        [
            ("Catálogo", url_for("index", _external=True)),
            ("Blog", url_for("blog_indice", _external=True)),
            (artigo["titulo"], url_artigo),
        ]
    )
    dados_artigo = _dados_artigo_schema(artigo, url_artigo, imagem_url)
    return render_template(
        "blog_artigo.html",
        artigo=artigo,
        corpo_html=corpo_html,
        imagem_url=imagem_url,
        url_produto=url_produto,
        dados_breadcrumb=dados_breadcrumb,
        dados_artigo=dados_artigo,
    )


@app.route("/para/<slug>", methods=["GET"])
def landing_pagina(slug: str):
    """Landing page por publico/uso (ver services/landing_paginas.py) --
    diferente do /blog (narrativa sobre um santo) e do /atendimento
    (suporte/politicas): aqui alguem chegando de anuncio ou busca tipo
    "medalha pra casamento" acha os produtos certos pro uso dela."""
    pagina = PAGINAS_LANDING.get(slug)
    if pagina is None:
        abort(404)
    dados_breadcrumb = _dados_breadcrumb(
        [
            ("Catálogo", url_for("index", _external=True)),
            (pagina["titulo"], url_for("landing_pagina", slug=slug, _external=True)),
        ]
    )
    return render_template(
        "landing.html",
        pagina=pagina,
        slug=slug,
        dados_breadcrumb=dados_breadcrumb,
    )


@app.route("/busca", methods=["GET"])
def busca_legado_redirect():
    """URL de busca da plataforma anterior (ver auditoria Search
    Console/conversa) -- a busca de hoje e´ direto em /catalogo?q=...
    (ver services/catalogo.py e o SearchAction do schema.org em
    _dados_website_schema). 301 preservando o termo buscado, se houver."""
    termo = request.args.get("q", "")
    if termo:
        return redirect(url_for("catalogo_completo", q=termo), code=301)
    return redirect(url_for("catalogo_completo"), code=301)


@app.route("/chaveiros", methods=["GET"])
@app.route("/medalhas", methods=["GET"])
def colecao_legado_redirect():
    """"/chaveiros" e "/medalhas" eram paginas de colecao por FORMATO na
    plataforma anterior (todos os chaveiros/medalhas de todos os
    santos numa grade so´, ver auditoria Search Console/conversa) --
    hoje o formato e´ escolhido dentro da pagina de cada produto, sem
    uma colecao equivalente, entao 301 pro catalogo completo."""
    return redirect(url_for("catalogo_completo"), code=301)


_REDIRECT_PRODUTO_LEGADO_PREFIXOS = (
    "medalha-de-", "medalha-do-", "medalha-da-", "medalha-das-", "medalha-dos-",
    "chaveiro-de-", "chaveiro-do-", "chaveiro-da-", "pingente-de-", "entremeio-de-",
    "cadeia-de-consagracao-inox-de-", "cadeia-de-consagracao-de-",
    "cadeia-de-consagracao-inox-com-medalha-de-", "cadeia-de-consagracao-com-medalha-de-",
)

_REDIRECT_PRODUTO_LEGADO_ALIASES = {
    # slug ja sem prefixo/sufixo (ver _resolver_produto_legado_id abaixo)
    # -> produto_id atual, pros casos que o nome mudou (canonizacao, ex:
    # "beato" virou "santo"/"são") ou nao dava pra resolver so tirando
    # prefixo/sufixo (ver auditoria Search Console/conversa). Verificado
    # manualmente um por um -- casos ambiguos ficam de fora de proposito
    # (melhor 404 do que redirecionar pro produto errado).
    "ressuscitado-que-passou-pela-cruz": "ressuscitado",
    "serva-de-deus-clare-crocker": "irma-clare",
    "beato-carlo-acutis": "carlo-acutis",
    "beato-pier-giorgio-frassati": "sao-pier-giorgio-frassati",
    "nossa-senhora-da-ternura": "nossa-senhora-mae-da-ternura",
    "santa-gemma-galgani": "santa-gemma",
    "santa-gianna-beretta-molla": "santa-gianna",
    "santa-teresa-benedita-da-cruz-edith-stein": "edith-stein",
    "sao-josemaria-escriva": "sao-jose-maria-escriva",
    "sao-luiz-e-santa-zelia-pais-de-teresinha": "pais-de-teresinha",
    "sao-miguel-arcanjo": "sao-miguel",
    "divino-semeador": "jesus-semeador",
    "santa-rita-de-cassia-folheado-a-ouro": "santa-rita-de-cassia",
}

_REDIRECT_PERSONALIZADA_LEGADO = {
    # as 3 URLs de personalizada da plataforma antiga -- cada uma vira o
    # formato correspondente ja pre-selecionado em /personalizada.
    "medalha-de-santo-personalizada-de-1-lado": "medalha",
    "medalha-personalizada-de-2-lados": "medalha_2lados",
    "chaveiro-personalizado-de-2-lados": "chaveiro_2lados",
}


def _resolver_produto_legado_id(slug: str) -> str | None:
    """Resolve um slug de produto da PLATAFORMA ANTIGA da loja (URLs tipo
    /<slug>/p, ainda indexadas pelo Google -- ver auditoria Search
    Console/conversa) pro produto_id atual, tirando o prefixo
    ("medalha-de-", "chaveiro-do-" etc.) e sufixo ("-modelo-2",
    "-1-lado" etc.) e conferindo se sobrou um produto_id valido -- ou
    usando _REDIRECT_PRODUTO_LEGADO_ALIASES pros casos que precisam de
    mapeamento manual. Devolve None se nao reconhecer (peca
    descontinuada, ex: "nossa-senhora-das-lagrimas") -- nesse caso e´
    melhor deixar 404 do que redirecionar errado."""
    normalizado = slug
    for prefixo in _REDIRECT_PRODUTO_LEGADO_PREFIXOS:
        if normalizado.startswith(prefixo):
            normalizado = normalizado[len(prefixo):]
            break
    normalizado = re.sub(r"-modelo-\d+$", "", normalizado)
    normalizado = re.sub(r"-\d+-lados?$", "", normalizado)
    normalizado = _REDIRECT_PRODUTO_LEGADO_ALIASES.get(normalizado, normalizado)
    if buscar_produto(normalizado) is not None:
        return normalizado
    return None


@app.route("/<path:slug>/p", methods=["GET"])
def produto_legado_redirect(slug: str):
    """URLs no formato da plataforma anterior da loja (antes da migracao
    pro Flask), ainda indexadas pelo Google (ver auditoria Search
    Console/conversa) -- 301 pro produto atual (ou pra /personalizada no
    formato certo) quando da pra resolver, senao 404 normal (peca
    descontinuada)."""
    formato_personalizada = _REDIRECT_PERSONALIZADA_LEGADO.get(slug)
    if formato_personalizada:
        return redirect(url_for("personalizada", formato=formato_personalizada), code=301)
    produto_id = _resolver_produto_legado_id(slug)
    if produto_id is None:
        abort(404)
    return redirect(url_for("produto", produto_id=produto_id), code=301)


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


# Mesmos rotulos usados no carrinho (static/js/carrinho_pagina.js --
# TAMANHO_LABEL/COR_LABEL/FORMATO_LABEL/detalheFormato) -- mantidos
# identicos aqui pra descricao do pedido bater com o que o cliente ja
# viu no carrinho, incluindo a variacao (tamanho/cor), que antes nao
# aparecia no pedido persistido (so produto + modelo).
_TAMANHO_LABEL = {"12mm": "1,2 cm", "16mm": "1,6 cm", "14mm": "1,4 cm", "18mm": "1,8 cm"}
_COR_LABEL = {"prata": "Prata", "ouro_velho": "Ouro velho", "dourado": "Dourado"}
_FORMATO_LABEL = {
    "medalha": "Medalha", "entremeio": "Entremeio", "chaveiro": "Chaveiro",
    "medalha_2lados": "Medalha 2 lados", "entremeio_2lados": "Entremeio 2 lados",
    "chaveiro_2lados": "Chaveiro 2 lados", "cruz_terco": "Cruz para terço",
}


def _detalhe_formato_do_item(item: dict) -> str:
    formato = str(item.get("formato") or "medalha")
    if formato == "entremeio":
        cor = str(item.get("cor", ""))
        return f"{_FORMATO_LABEL['entremeio']} · {_COR_LABEL.get(cor, cor)}"
    if formato == "chaveiro":
        return _FORMATO_LABEL["chaveiro"]
    if formato == "chaveiro_2lados":
        # sem cor/tamanho (so uma versao, prata/inox -- ver conversa
        # 2026-09-03), mesmo criterio do chaveiro de 1 lado acima.
        return _FORMATO_LABEL["chaveiro_2lados"]
    if formato == "entremeio_2lados":
        cor = str(item.get("cor", ""))
        return f"{_FORMATO_LABEL[formato]} · {_COR_LABEL.get(cor, cor)}"
    if formato == "medalha_2lados":
        # tamanho (14/18mm) e´ so fisico -- mesmo preco, mesma simulacao
        # visual (ver conversa, mesmo criterio ja usado no "medalha" 1
        # lado com 12/16mm) -- mas ainda entra no detalhe/CSV pra
        # producao saber qual tamanho imprimir.
        cor = str(item.get("cor", ""))
        tamanho = str(item.get("tamanho", ""))
        return f"{_FORMATO_LABEL[formato]} · {_COR_LABEL.get(cor, cor)} · {_TAMANHO_LABEL.get(tamanho, tamanho)}"
    if formato == "cruz_terco":
        # sem tamanho (peca unica, 4,2 x 1,7 cm -- ver conversa
        # 2026-09-11) -- so a cor muda.
        cor = str(item.get("cor", ""))
        return f"{_FORMATO_LABEL['cruz_terco']} · {_COR_LABEL.get(cor, cor)}"
    tamanho = str(item.get("tamanho", ""))
    return f"{_FORMATO_LABEL['medalha']} · {_TAMANHO_LABEL.get(tamanho, tamanho)}"


# So pro CSV de producao (ver admin_pedido_csv) -- pedido do usuario:
# a coluna "Modelo" ("Modelo 1", "Modelo 2"...) so precisa do numero, e
# a coluna "Variação" so precisa do numero/tamanho do molde usado na
# producao (12/16 pra medalha, 29 pro chaveiro -- 1 ou 2 lados, mesmo
# molde fisico -- e 16 fixo pro entremeio, 1 ou 2 lados, sem cor), em
# vez do texto por extenso usado no resto do site.
_VARIACAO_CSV_LABEL = {
    "12mm": "12", "16mm": "16",
    "chaveiro": "29", "chaveiro_2lados": "29",
    "entremeio": "16", "entremeio_2lados": "16",
}

# Medalha de 2 lados imprime num molde MENOR que o tamanho nominal (a
# borda/resina faz o acabamento final parecer maior -- pedido do
# usuario) -- SO no CSV de producao o molde de 14mm sai como "12" e o
# de 18mm como "16". O tamanho nominal usado em todo o resto do site
# (preco, SKU da Tiny, simulacao visual) continua 14mm/18mm sem
# nenhuma mudanca -- essa troca e´ so na hora de escrever o CSV.
_VARIACAO_CSV_TAMANHO_MEDALHA_2LADOS = {"14mm": "12", "18mm": "16"}

# Fallback pra pedido ANTIGO, de antes do campo "tamanho" comecar a ser
# guardado no item persistido (ver conversa: pedido real do site com a
# coluna Variação saindo em branco pra medalha_2lados 1,4cm, porque
# esse pedido foi feito antes dessa correcao). Nesses casos o unico
# lugar que ainda tem o tamanho e´ o texto de "detalhe" (guardado desde
# sempre, nunca teve esse bug) -- procura o rotulo "1,4 cm"/"1,8 cm"
# ali dentro em vez de devolver vazio.
_VARIACAO_CSV_TAMANHO_MEDALHA_2LADOS_POR_DETALHE = {"1,4 cm": "12", "1,8 cm": "16"}


def _modelo_csv_do_item(item: dict) -> str:
    nome = str(item.get("modeloNome", ""))
    prefixo = "Modelo "
    return nome[len(prefixo):] if nome.startswith(prefixo) else nome


def _variacao_csv_do_item(item: dict) -> str:
    chave_preco = str(item.get("chave_preco", ""))
    if chave_preco == "medalha_2lados":
        tamanho = str(item.get("tamanho", ""))
        if tamanho in _VARIACAO_CSV_TAMANHO_MEDALHA_2LADOS:
            return _VARIACAO_CSV_TAMANHO_MEDALHA_2LADOS[tamanho]
        detalhe = str(item.get("detalhe", ""))
        for rotulo, valor in _VARIACAO_CSV_TAMANHO_MEDALHA_2LADOS_POR_DETALHE.items():
            if rotulo in detalhe:
                return valor
        return tamanho
    return _VARIACAO_CSV_LABEL.get(chave_preco, str(item.get("detalhe", "")))


def _produto_e_modelo_csv_do_lado(item: dict, sufixo_lado: str) -> tuple[str, str]:
    """Produto/Modelo de UM lado de um item de 2 lados -- lado escolhido
    do catalogo usa o proprio santo/modelo (mesmo formato de sempre);
    lado com foto usa "Personalizada" + o numero SEPARADO desse lado
    (ver services/pedidos.py:numero_modelo_personalizada -- cada foto e´
    numerada por conta propria, mesmo as duas fazendo parte da mesma
    peca fisica no fim). Lado sem nada ainda (foto "enviar depois" via
    WhatsApp) devolve numero vazio -- so preenche quando a foto chegar."""
    produto_nome_lado = str(item.get(f"produtoNome{sufixo_lado}", ""))
    if produto_nome_lado:
        return produto_nome_lado, _modelo_csv_do_item({"modeloNome": item.get(f"modeloNome{sufixo_lado}", "")})
    numero = item.get(f"numeroModeloPersonalizada{sufixo_lado}")
    return "Personalizada", str(numero) if numero is not None else ""


def _linhas_csv_do_item(item: dict) -> list[list]:
    """Linhas do CSV de producao pra um item -- item de 1 lado vira UMA
    linha (como sempre); item de 2 lados vira DUAS linhas POR UNIDADE de
    quantidade (lado1 e depois lado2, nessa ordem -- pedido do usuario:
    "entra na contagem normal... apenas bastam estar na ordem", sem
    rotulo "lado 1"/"lado 2" na planilha, cada linha ja se identifica
    sozinha pelo proprio produto/numero), repetidas pra cada peca fisica
    (producao monta lado a lado, entao ve os dois lados de cada unidade
    em sequencia, com quantidade 1 em cada linha)."""
    variacao = _variacao_csv_do_item(item)
    if not item.get("duasFaces"):
        return [[item.get("produtoNome", ""), _modelo_csv_do_item(item), variacao, item["quantidade"]]]

    produto1, modelo1 = _produto_e_modelo_csv_do_lado(item, "Lado1")
    produto2, modelo2 = _produto_e_modelo_csv_do_lado(item, "Lado2")
    linhas = []
    for _ in range(int(item.get("quantidade", 0))):
        linhas.append([produto1, modelo1, variacao, 1])
        linhas.append([produto2, modelo2, variacao, 1])
    return linhas


_TAMANHOS_COM_SEPARADOR_CSV_TOTAL = {"12", "16"}  # 29 (chaveiro) fica de fora, ver conversa


def _linhas_csv_pedido(pedido: dict) -> list[list]:
    linhas = []
    for item in pedido["itens"]:
        linhas.extend(_linhas_csv_do_item(item))
    return linhas


def _recortes_personalizados_do_item(item: dict) -> list[tuple]:
    """Numero + URL de cada recorte 1:1 (imagem que vai pra producao de
    verdade, ver conversa) que um item carrega -- 2 lados pode ter 0, 1
    ou 2 (cada lado personalizada com foto propria conta separado, lado
    do catalogo nao tem recorte); 1 lado tem 0 ou 1. MESMO criterio do
    template admin_pedido_detalhe.html (ver os links "Baixar imagem
    1:1" la´), reaproveitado aqui pro zip em massa (ver
    admin_pedidos_zip_personalizadas abaixo)."""
    if item.get("duasFaces"):
        recortes = []
        if item.get("imagemRecorteLado1"):
            recortes.append((item.get("numeroModeloPersonalizadaLado1"), item["imagemRecorteLado1"]))
        if item.get("imagemRecorteLado2"):
            recortes.append((item.get("numeroModeloPersonalizadaLado2"), item["imagemRecorteLado2"]))
        return recortes
    if item.get("imagemRecorte"):
        return [(item.get("numeroModeloPersonalizada"), item["imagemRecorte"])]
    return []


_PREFIXO_IMAGEM_PERSONALIZADA = "/imagem-personalizada/"


def _marcar_imagem_personalizada_usada_se_aplicavel(valor: str) -> None:
    """`imagem`/`imagemRecorte` guardam a URL duravel (ver
    servir_imagem_personalizada) quando o item e´ uma personalizada com
    foto -- marca como "usada" pra services.imagens_personalizadas nunca
    apagar essa imagem na limpeza de simulacoes abandonadas (ver
    purgar_imagens_antigas), mesmo que o pedido demore pra ser pago.
    Nao faz nada pra item sem foto (valor vazio) ou carrinho antigo (data
    URI, de antes dessa mudanca -- ver conversa)."""
    if valor.startswith(_PREFIXO_IMAGEM_PERSONALIZADA):
        marcar_imagem_usada(valor[len(_PREFIXO_IMAGEM_PERSONALIZADA):])


_CAMPOS_IMAGEM_PERSONALIZADA_ITEM = (
    "imagem", "imagemRecorte", "imagemLado1", "imagemRecorteLado1", "imagemLado2", "imagemRecorteLado2",
)


def _tokens_imagens_personalizadas_do_pedido(pedido: dict) -> list[str]:
    """Junta os tokens de TODAS as imagens personalizadas (previa e
    recorte, dos 2 lados se for duasFaces) referenciadas pelos itens de
    um pedido -- usado por _limpar_imagens_pedidos_cancelados abaixo pra
    saber exatamente o que apagar."""
    tokens = []
    for item in pedido["itens"]:
        for campo in _CAMPOS_IMAGEM_PERSONALIZADA_ITEM:
            valor = str(item.get(campo) or "")
            if valor.startswith(_PREFIXO_IMAGEM_PERSONALIZADA):
                tokens.append(valor[len(_PREFIXO_IMAGEM_PERSONALIZADA):])
    return tokens


def _itens_com_descricao_do_corpo(dados: dict) -> list[dict]:
    """Mesma validacao de _itens_validos_do_corpo, mas guarda tambem
    campos legiveis (nome do produto/modelo/variacao/imagem) pra exibir
    no pedido, no e-mail, no item de pagamento e no CSV do admin -- so
    cosmetico, NUNCA usado pra calcular preco (isso continua vindo so
    de chave_preco+quantidade, via calcular_carrinho)."""
    itens_validos = []
    for item in dados.get("itens", []):
        try:
            chave_preco = str(item["chave_preco"])
            quantidade = int(item["quantidade"])
        except (KeyError, TypeError, ValueError):
            continue
        if chave_preco not in CHAVES_PRECO or quantidade <= 0:
            continue
        produto_nome = str(item.get("produtoNome", "")).strip()
        modelo_nome = str(item.get("modeloNome", "")).strip()
        detalhe = _detalhe_formato_do_item(item)
        partes = [p for p in (produto_nome, modelo_nome, detalhe) if p]
        descricao = " — ".join(partes) or chave_preco

        # medalha_2lados/entremeio_2lados (ver static/js/personalizada.js)
        # mandam "lado1"/"lado2" em vez de imagem/imagemRecorte direto no
        # item -- uma peca so, duas fotos (uma por lado). "imagem" segue
        # preenchida com a do lado 1, como fallback pra qualquer lugar que
        # ainda so saiba mostrar uma miniatura; quem precisa dos dois
        # lados de verdade usa imagem_lado1/imagem_lado2 (ver pedido.html,
        # admin_pedido_detalhe.html, services/email.py).
        duas_faces = bool(item.get("duasFaces"))
        lado1 = item.get("lado1") or {} if duas_faces else {}
        lado2 = item.get("lado2") or {} if duas_faces else {}
        imagem_lado1 = str(lado1.get("imagem", ""))
        imagem_recorte_lado1 = str(lado1.get("imagemRecorte", "") or "")
        imagem_lado2 = str(lado2.get("imagem", ""))
        imagem_recorte_lado2 = str(lado2.get("imagemRecorte", "") or "")
        # so preenchido quando o lado veio de "escolher do catalogo" (ver
        # static/js/personalizada.js:selecionarSantoDoCatalogo) -- upload
        # e "sem foto" nao tem produto/modelo, ficam vazios.
        produto_nome_lado1 = str(lado1.get("produtoNome", "")).strip()
        modelo_nome_lado1 = str(lado1.get("modeloNome", "")).strip()
        produto_nome_lado2 = str(lado2.get("produtoNome", "")).strip()
        modelo_nome_lado2 = str(lado2.get("modeloNome", "")).strip()

        imagem = imagem_lado1 if duas_faces else str(item.get("imagem", ""))
        imagem_recorte = imagem_recorte_lado1 if duas_faces else str(item.get("imagemRecorte", "") or "")
        for valor in (imagem, imagem_recorte, imagem_lado2, imagem_recorte_lado2):
            _marcar_imagem_personalizada_usada_se_aplicavel(valor)

        itens_validos.append(
            {
                "chave_preco": chave_preco,
                "quantidade": quantidade,
                "descricao": descricao[:160],
                "produtoNome": produto_nome,
                "produtoId": str(item.get("produtoId", "")).strip(),
                # Junto com produtoId, forma o codigo que a Tiny usa pra
                # puxar NCM/categoria sozinha na nota fiscal (ver
                # services/tiny.py:_codigo_estoque_tiny e
                # scripts/gerar_planilha_tiny.py, mesmo esquema de SKU).
                "modeloId": str(item.get("modeloId", "")).strip(),
                "modeloNome": modelo_nome,
                "detalhe": detalhe,
                # cor tem sentido pra entremeio/entremeio_2lados/
                # medalha_2lados (prata/ouro velho sao materia-prima
                # comprada separada, ver conversa) e tamanho pra
                # medalha_2lados (14mm/18mm) -- os dois precisam sobreviver
                # ate a sincronizacao com a Tiny (services.tiny.
                # _chave_material/_codigo_estoque_tiny), que roda so depois
                # do pagamento confirmado, bem depois da criacao do pedido.
                # BUG corrigido: "tamanho" nunca era guardado aqui (so
                # "cor"), entao _chave_material nunca resolvia o SKU
                # especifico de medalha_2lados e toda venda ia pra Tiny com
                # o codigo generico "medalha_2lados" em vez do material
                # certo por tamanho+cor (ver conversa, print real do Tiny).
                "cor": str(item.get("cor", "")).strip(),
                "tamanho": str(item.get("tamanho", "") or "").strip(),
                # imagem NUNCA truncada -- URL duravel pra medalha
                # personalizada (ver services/imagens_personalizadas.py),
                # ou ainda um data URI inteiro num carrinho antigo (de
                # antes dessa mudanca) -- cortar no meio corrompe os dois.
                "imagem": imagem,
                # Recorte quadrado 1:1 (sem a moldura da medalha por cima),
                # so existe pra item personalizado com foto -- e´ o que a
                # producao precisa baixar, nao a previa com moldura. Guardado
                # aqui pra nunca mais depender do cliente reenviar a foto
                # pelo WhatsApp (ver conversa).
                "imagemRecorte": imagem_recorte,
                "duasFaces": duas_faces,
                "imagemLado1": imagem_lado1,
                "imagemRecorteLado1": imagem_recorte_lado1,
                "imagemLado2": imagem_lado2,
                "imagemRecorteLado2": imagem_recorte_lado2,
                "produtoNomeLado1": produto_nome_lado1,
                "modeloNomeLado1": modelo_nome_lado1,
                "produtoNomeLado2": produto_nome_lado2,
                "modeloNomeLado2": modelo_nome_lado2,
            }
        )
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
    tipo_pessoa = tipo_pessoa if tipo_pessoa in ("fisica", "juridica") else "fisica"
    # Inscricao Estadual so faz sentido pra pessoa juridica (ver
    # static/js/carrinho_pagina.js) -- isento nunca guarda numero (os
    # dois sao mutuamente exclusivos na UI, mas confere aqui tambem,
    # nunca confiando so na validacao do navegador).
    inscricao_estadual = str(cliente.get("inscricao_estadual", "")).strip() if tipo_pessoa == "juridica" else ""
    ie_isento = bool(cliente.get("ie_isento")) if tipo_pessoa == "juridica" else False
    ie_nao_contribuinte = bool(cliente.get("ie_nao_contribuinte")) if tipo_pessoa == "juridica" else False
    if ie_isento:
        inscricao_estadual = ""
    return {
        "nome": nome,
        "tipo_pessoa": tipo_pessoa,
        "documento": documento,
        "telefone": telefone,
        "email": email,
        "inscricao_estadual": inscricao_estadual,
        "ie_isento": ie_isento,
        "ie_nao_contribuinte": ie_nao_contribuinte,
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

    # Endereco de entrega DIFERENTE do endereco principal (ver conversa
    # -- pode ser fisicamente outro endereco, nao so outro nome na
    # mesma casa: ex. a coordenadora da livraria recebe no endereco
    # dela, a nota fiscal sai no nome/endereco da paroquia). Sempre
    # opcional EM CONJUNTO: se nenhum campo vier preenchido, a entrega
    # usa o endereco_* principal acima mesmo com destinatario_nome
    # preenchido (ver templates/pedido.html). Se algum vier, todos os
    # obrigatorios (menos complemento) precisam vir -- mesmo criterio
    # do endereco principal, pra nunca faltar dado na etiqueta.
    campos_endereco_destinatario = [
        "destinatario_cep", "destinatario_logradouro", "destinatario_numero",
        "destinatario_bairro", "destinatario_cidade", "destinatario_uf",
    ]
    valores_endereco_dest = {campo: str(endereco.get(campo, "")).strip() for campo in campos_endereco_destinatario}
    algum_preenchido = any(valores_endereco_dest.values())
    todos_preenchidos = all(valores_endereco_dest.values())
    if algum_preenchido and not todos_preenchidos:
        return None
    valores.update(valores_endereco_dest)
    valores["destinatario_complemento"] = str(endereco.get("destinatario_complemento", "")).strip()
    # Telefone de quem recebe, quando diferente de quem fecha a compra
    # (ver conversa) -- opcional mesmo com endereco de entrega diferente
    # preenchido, so pra transportadora/Tiny conseguirem contato se
    # precisar. So valida formato quando preenchido, nunca obrigatorio.
    destinatario_telefone = str(endereco.get("destinatario_telefone", "")).strip()
    if destinatario_telefone and not telefone_valido(destinatario_telefone):
        return None
    valores["destinatario_telefone"] = destinatario_telefone
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
    # produtos "personalizada" tambem aparecem na busca (config.py:
    # PRODUTOS_PERSONALIZADOS, ver conversa) -- por ultimo, pra nao
    # empurrar santos de verdade pra fora do limite de 6 resultados.
    itens = _itens_do_grid(carregar_produtos()) + _itens_personalizados_do_grid()
    resultados = [item for item in itens if termo in normalizar_busca(item["nome"])][:6]
    return jsonify(
        [
            {
                "id": item["id"],
                "nome": item["nome"],
                "thumbnail": url_for("static", filename=item["thumbnail"]),
                "url": item.get("personalizada_url") or url_for("produto", produto_id=item["id"]),
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
@limiter.limit("20 per minute")
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
        resumo_carrinho["desconto_frete_atacado"],
    )
    return jsonify(resultado)


@app.route("/api/pedido/criar", methods=["POST"])
@limiter.limit("10 per minute")
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
    try:
        frete_prazo_dias = int(frete.get("prazo_dias"))
    except (TypeError, ValueError):
        frete_prazo_dias = None

    cliente = _cliente_valido(dados)
    if cliente is None:
        return jsonify(erro="Preencha seus dados completos (nome, documento, telefone e e-mail)."), 400
    rotulo_documento = "CNPJ" if cliente["tipo_pessoa"] == "juridica" else "CPF"
    if not documento_valido(cliente["tipo_pessoa"], cliente["documento"]):
        return jsonify(erro=f"{rotulo_documento} inválido. Confira o número digitado."), 400
    if not telefone_valido(cliente["telefone"]):
        return jsonify(erro="Telefone inválido. Confira o DDD e o número digitado."), 400
    endereco = _endereco_valido(dados)
    if endereco is None:
        return jsonify(erro="Preencha o endereço de entrega completo."), 400
    if endereco.get("destinatario_documento") and not documento_valido(
        endereco.get("destinatario_tipo_pessoa") or "fisica", endereco["destinatario_documento"]
    ):
        rotulo_dest = "CNPJ" if endereco.get("destinatario_tipo_pessoa") == "juridica" else "CPF"
        return jsonify(erro=f"{rotulo_dest} de quem recebe é inválido. Confira o número digitado."), 400

    if frete_descricao == FRETE_RETIRADA_DESCRICAO:
        # retirada no local e´ sempre gratis -- nunca confia num valor
        # diferente que o navegador tenha mandado (mesmo raciocinio da
        # reconferencia abaixo, so que aqui o preco certo ja e´ sabido
        # sem precisar consultar nenhuma transportadora).
        frete_preco = 0.0
    else:
        cep_frete = endereco.get("destinatario_cep") or endereco["cep"]
        frete_minimo = _frete_preco_minimo_valido(
            itens_validos, cep_frete, calculo["subtotal_total"], calculo["frete_gratis_atingido"],
            calculo["desconto_frete_atacado"],
        )
        if frete_minimo is not None and frete_preco < frete_minimo - 0.50:
            return jsonify(erro="O frete mudou -- recalcule antes de pagar."), 400

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
        frete_prazo_dias=frete_prazo_dias,
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


@app.route("/api/pedido/criar-boleto", methods=["POST"])
@limiter.limit("10 per minute")
def api_pedido_criar_boleto():
    """Mesma validacao de api_pedido_criar (carrinho/frete/cliente/
    endereco/documento), so que emite um boleto via Banco Inter (ver
    services/inter.py) em vez de gerar link da InfinitePay. O pedido
    fica "pendente" ate o job de polling confirmar o pagamento (ver
    _verificar_boletos_inter_pendentes mais abaixo) -- pode levar ate 2
    dias uteis, avisado pro cliente na propria pagina de
    acompanhamento (ver templates/pedido.html)."""
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
    try:
        frete_prazo_dias = int(frete.get("prazo_dias"))
    except (TypeError, ValueError):
        frete_prazo_dias = None

    cliente = _cliente_valido(dados)
    if cliente is None:
        return jsonify(erro="Preencha seus dados completos (nome, documento, telefone e e-mail)."), 400
    rotulo_documento = "CNPJ" if cliente["tipo_pessoa"] == "juridica" else "CPF"
    if not documento_valido(cliente["tipo_pessoa"], cliente["documento"]):
        return jsonify(erro=f"{rotulo_documento} inválido. Confira o número digitado."), 400
    if not telefone_valido(cliente["telefone"]):
        return jsonify(erro="Telefone inválido. Confira o DDD e o número digitado."), 400
    endereco = _endereco_valido(dados)
    if endereco is None:
        return jsonify(erro="Preencha o endereço de entrega completo."), 400
    if endereco.get("destinatario_documento") and not documento_valido(
        endereco.get("destinatario_tipo_pessoa") or "fisica", endereco["destinatario_documento"]
    ):
        rotulo_dest = "CNPJ" if endereco.get("destinatario_tipo_pessoa") == "juridica" else "CPF"
        return jsonify(erro=f"{rotulo_dest} de quem recebe é inválido. Confira o número digitado."), 400

    if frete_descricao == FRETE_RETIRADA_DESCRICAO:
        frete_preco = 0.0
    else:
        cep_frete = endereco.get("destinatario_cep") or endereco["cep"]
        frete_minimo = _frete_preco_minimo_valido(
            itens_validos, cep_frete, calculo["subtotal_total"], calculo["frete_gratis_atingido"],
            calculo["desconto_frete_atacado"],
        )
        if frete_minimo is not None and frete_preco < frete_minimo - 0.50:
            return jsonify(erro="O frete mudou -- recalcule antes de pagar."), 400

    for item_validado, item_calculado in zip(itens_validos, calculo["itens"]):
        item_validado["valor_unitario"] = item_calculado["preco_unitario"]

    pedido = criar_pedido(
        itens=itens_validos,
        subtotal=calculo["subtotal_total"],
        frete_descricao=frete_descricao,
        frete_preco=frete_preco,
        frete_prazo_dias=frete_prazo_dias,
        cliente=cliente,
        endereco=endereco,
    )

    resultado = emitir_boleto(seu_numero=pedido["codigo"], valor=pedido["total"], cliente=cliente, endereco=endereco)
    if "erro" in resultado:
        return jsonify(erro=resultado["erro"]), 502

    dados_cobranca = consultar_cobranca(resultado["codigo_solicitacao"])
    boleto = dados_cobranca.get("boleto") or {}
    pix = dados_cobranca.get("pix") or {}
    pedido = salvar_dados_boleto_inter(
        pedido["token"],
        codigo_solicitacao=resultado["codigo_solicitacao"],
        linha_digitavel=boleto.get("linhaDigitavel", ""),
        codigo_barras=boleto.get("codigoBarras", ""),
        pix_copia_cola=pix.get("pixCopiaECola", ""),
    )

    enviar_notificacao_push(
        titulo="🎉 Boleto Emitido",
        corpo=f"Pedido #{pedido['codigo']} -- {_formatar_preco(pedido['total'])}",
        url=url_for("admin_pedido_detalhe", token=pedido["token"], _external=True),
        icone=url_for("static", filename="img/boleto-icone.png"),
    )

    resultado_email = enviar_boleto_gerado(
        pedido, url_for("ver_pedido", token=pedido["token"], _external=True)
    )
    marcar_email_pedido_criado_enviado(pedido["token"], erro=resultado_email.get("erro"))

    return jsonify(
        token=pedido["token"],
        codigo=pedido["codigo"],
        linha_digitavel=pedido["inter_linha_digitavel"],
        pix_copia_cola=pedido["inter_pix_copia_cola"],
    )


@app.route("/api/pedido/criar-whatsapp", methods=["POST"])
@limiter.limit("10 per minute")
def api_pedido_criar_whatsapp():
    """Lead criado ao clicar "Finalizar pelo WhatsApp" no carrinho (ver
    static/js/carrinho_pagina.js) -- sem link de pagamento e sem exigir
    cliente/endereco (o WhatsApp nunca coletou isso). Só entra no painel
    admin com status "whatsapp" pra quem vende acompanhar e preencher
    os dados na mao se a pessoa realmente fechar o pedido na conversa
    (ver confirmar_venda_manual / admin_pedido_confirmar_venda)."""
    dados = request.get_json(silent=True) or {}
    itens_validos = _itens_com_descricao_do_corpo(dados)
    if not itens_validos:
        return jsonify(erro="Carrinho vazio."), 400

    calculo = calcular_carrinho(itens_validos)
    if not calculo["atinge_minimo"]:
        return jsonify(erro="Pedido abaixo do mínimo de produtos."), 400
    for item_validado, item_calculado in zip(itens_validos, calculo["itens"]):
        item_validado["valor_unitario"] = item_calculado["preco_unitario"]

    frete = dados.get("frete") or {}
    try:
        frete_preco = float(frete.get("preco"))
    except (TypeError, ValueError):
        frete_preco = 0.0
    try:
        frete_prazo_dias = int(frete.get("prazo_dias"))
    except (TypeError, ValueError):
        frete_prazo_dias = None
    frete_descricao = str(frete.get("texto", "")).strip()
    # Frete nao simulado (comum em quem fecha direto pelo WhatsApp) --
    # se ja tiver digitado o CEP no calculo, guarda mesmo assim, pra
    # quem for atender ja ter o dado (mesmo criterio do texto da
    # mensagem, ver montarLinhasFrete em carrinho_pagina.js).
    cep_informado = str(dados.get("cep_informado", "")).strip()
    if not frete_descricao and cep_informado:
        frete_descricao = f"CEP informado (frete não calculado): {cep_informado}"

    pedido = criar_pedido(
        itens=itens_validos,
        subtotal=calculo["subtotal_total"],
        frete_descricao=frete_descricao,
        frete_preco=frete_preco,
        frete_prazo_dias=frete_prazo_dias,
        cliente={},
        endereco={},
        status_inicial="whatsapp",
    )

    enviar_notificacao_push(
        titulo="🎉 Você tem um pedido via WhatsApp",
        corpo=f"Pedido #{pedido['codigo']} -- {_formatar_preco(pedido['total'])}",
        url=url_for("admin_pedido_detalhe", token=pedido["token"], _external=True),
        icone=url_for("static", filename="img/icone-whatsapp.png"),
    )

    return jsonify(ok=True, codigo=pedido["codigo"], token=pedido["token"])


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


def _frete_preco_minimo_valido(
    itens: list[dict],
    cep: str,
    subtotal: float,
    frete_gratis_atingido: bool,
    desconto_frete_atacado: float = 0.0,
) -> float | None:
    """Reconfere o preco de frete que o navegador mandou contra uma nova
    cotacao real (Frenet/Melhor Envio) -- sem isso, um cliente podia
    interceptar o POST e mandar qualquer frete_preco (ex: 0,01) pra
    qualquer opcao, mesmo pesada/longe (ver conversa "tornar o site e
    apis seguros"). Devolve o menor preco aceitavel (0.0 quando o
    pedido ja atinge frete gratis, ou com o desconto de atacado ja
    abatido -- ver services.frete.calcular_frete/_resultado_desconto_atacado)
    ou None quando nao da pra confirmar (nenhuma cotacao respondeu, CEP
    invalido, etc.) -- nesse caso o chamador NAO bloqueia o pedido
    (fail-open: um problema temporario na Frenet/Melhor Envio nunca
    deve impedir uma venda de verdade, so a manipulacao deliberada de
    preco e´ bloqueada)."""
    try:
        resultado = calcular_frete(itens, cep, subtotal, frete_gratis_atingido, desconto_frete_atacado)
    except Exception:
        return None
    if resultado.get("erro"):
        return None
    opcoes = resultado.get("opcoes") or []
    if not opcoes:
        return 0.0 if resultado.get("frete_gratis") else None
    # frete_gratis e desconto_atacado_reais usam o mesmo formato de
    # opcao (com "preco_final" ja abatido) -- generaliza os dois casos.
    if "preco_final" in opcoes[0]:
        return min(o["preco_final"] for o in opcoes)
    return min(o["preco"] for o in opcoes)


def _gerar_link_pagamento_para_pedido(pedido: dict, cliente: dict, endereco: dict) -> dict:
    return criar_link_pagamento(
        order_nsu=pedido["token"],
        # ?obrigado=1 so serve pra decidir se mostra o bloco completo de
        # "obrigado pela compra" (ver_pedido/pedido.html) no primeiro
        # retorno apos o pagamento -- nunca usado sozinho pra provar que
        # o pedido foi pago de verdade, so o status no banco importa.
        redirect_url=url_for("ver_pedido", token=pedido["token"], obrigado="1", _external=True),
        # ?chave=... exigida de volta em webhook_infinitepay (ver
        # config.WEBHOOK_INFINITEPAY_SECRET) -- sem isso, qualquer POST
        # com um order_nsu valido conseguia forjar "pagamento confirmado".
        webhook_url=url_for("webhook_infinitepay", chave=WEBHOOK_INFINITEPAY_SECRET or None, _external=True),
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
@limiter.limit("10 per minute")
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


@app.route("/pedido/<token>/reativar-pix", methods=["GET"])
def pedido_reativar_pix(token: str):
    """Link direto no e-mail de recuperacao de pedido cancelado (ver
    services/email.py:enviar_pedido_cancelado) -- reativa o MESMO
    pedido (mesmos itens, mesma foto personalizada se tiver, ver
    services/pedidos.py:reativar_pedido_cancelado) e ja manda direto
    pro checkout Pix/cartao da InfinitePay, sem o cliente precisar
    preencher nada de novo. GET (nao POST) de proposito -- e´ um link
    clicado direto de dentro do e-mail, sem JS/formulario no meio."""
    pedido = obter_pedido(token)
    if pedido is None:
        abort(404)
    if pedido["status"] == "cancelado":
        pedido = reativar_pedido_cancelado(token)
    if pedido["status"] != "pendente":
        # ja foi reativado por outro clique/aba, ja foi pago, ou nunca
        # esteve cancelado -- nunca gera link a toa, so leva pra pagina
        # de acompanhamento de sempre.
        return redirect(url_for("ver_pedido", token=token))

    cliente, endereco = _cliente_e_endereco_do_pedido(pedido)
    resultado = _gerar_link_pagamento_para_pedido(pedido, cliente, endereco)
    if "erro" in resultado:
        return redirect(
            url_for("ver_pedido", token=token, reativar_erro="Não conseguimos gerar o link de pagamento agora.")
        )
    return redirect(resultado["url"])


@app.route("/pedido/<token>/reativar-boleto", methods=["GET"])
def pedido_reativar_boleto(token: str):
    """Mesma ideia de pedido_reativar_pix acima, so que emite um boleto
    via Banco Inter (ver api_pedido_criar_boleto) pro pedido reativado,
    em vez de link da InfinitePay -- depois manda pra pagina de
    acompanhamento, que ja mostra os dados do boleto quando
    preenchidos (ver templates/pedido.html)."""
    pedido = obter_pedido(token)
    if pedido is None:
        abort(404)
    if pedido["status"] == "cancelado":
        pedido = reativar_pedido_cancelado(token)
    if pedido["status"] != "pendente":
        return redirect(url_for("ver_pedido", token=token))
    if pedido.get("inter_codigo_solicitacao"):
        # ja tem um boleto emitido pra esse pedido (ex: clique duplicado
        # no mesmo link) -- nao emite outro, so mostra o que ja existe.
        return redirect(url_for("ver_pedido", token=token))

    cliente, endereco = _cliente_e_endereco_do_pedido(pedido)
    resultado = emitir_boleto(seu_numero=pedido["codigo"], valor=pedido["total"], cliente=cliente, endereco=endereco)
    if "erro" in resultado:
        return redirect(url_for("ver_pedido", token=token, reativar_erro="Não conseguimos gerar o boleto agora."))

    dados_cobranca = consultar_cobranca(resultado["codigo_solicitacao"])
    boleto = dados_cobranca.get("boleto") or {}
    pix = dados_cobranca.get("pix") or {}
    salvar_dados_boleto_inter(
        token,
        codigo_solicitacao=resultado["codigo_solicitacao"],
        linha_digitavel=boleto.get("linhaDigitavel", ""),
        codigo_barras=boleto.get("codigoBarras", ""),
        pix_copia_cola=pix.get("pixCopiaECola", ""),
    )
    return redirect(url_for("ver_pedido", token=token))


@app.route("/webhook/infinitepay", methods=["POST"])
def webhook_infinitepay():
    """Recebido pela InfinitePay quando um pagamento e´ confirmado (ver
    redirect_url/webhook_url em api_pedido_criar acima). So marca como
    pago quando o valor pago cobre o total esperado -- e´ idempotente
    (webhook repetido nao reprocessa, ver services.pedidos.marcar_pago),
    entao sempre responde 200 mesmo quando nao ha nada a fazer, pra
    InfinitePay nao ficar reenviando em loop."""
    if WEBHOOK_INFINITEPAY_SECRET and not hmac.compare_digest(
        request.args.get("chave", ""), WEBHOOK_INFINITEPAY_SECRET
    ):
        abort(404)

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
    _pos_pagamento_confirmado(pedido_pago, token)

    return jsonify(ok=True), 200


@app.route("/webhook/tiny-captura/<tipo>", methods=["POST"])
@limiter.limit("30 per minute")
def webhook_tiny_captura(tipo: str):
    """Endpoint TEMPORARIO -- so pra descobrir o formato real que a Tiny
    manda nos webhooks configurados em "Integração com API do ERP >
    notificações" (URLs de situação de pedido / nota fiscal / rastreio,
    ver conversa). NAO processa nada ainda -- so registra o payload cru
    no log (visivel no Render), pra depois construir o tratamento de
    verdade (ex: marcar "faturado" sozinho quando a nota sair na Tiny)
    com base no formato REAL, em vez de adivinhar sem documentação.
    `tipo` so identifica qual URL disparou (situacao-pedido/
    nota-fiscal/rastreio), nao precisa bater com nada especifico."""
    corpo = request.get_data(as_text=True)
    print(f"[TINY WEBHOOK CAPTURA] tipo={tipo} corpo={corpo}", flush=True)
    return jsonify(ok=True), 200


def _pos_pagamento_confirmado(pedido_pago: dict | None, token: str) -> None:
    """Integracoes disparadas na PRIMEIRA confirmacao de pagamento de um
    pedido -- usado tanto pelo webhook automatico da InfinitePay quanto
    pela confirmacao manual de venda combinada no WhatsApp (ver
    admin_pedido_confirmar_venda), pra nunca duplicar essa logica."""
    # sincroniza com a Tiny so na primeira confirmacao -- webhook
    # repetido (comum em integracoes de pagamento) nao reenvia o
    # mesmo pedido pra la de novo. Falha na Tiny nao derruba a
    # confirmacao do pagamento (o pedido ja esta pago no site de
    # qualquer forma) -- so fica registrado o erro pra conferir depois.
    if pedido_pago and not pedido_pago["tiny_sincronizado"]:
        try:
            resultado_tiny = criar_pedido_tiny(pedido_pago)
        except Exception as exc:  # ver comentario acima -- Tiny nunca derruba a confirmacao
            resultado_tiny = {"erro": f"Erro inesperado ao sincronizar: {exc}"}
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

        # avisos internos pra loja (e-mail + push, ver services/email.py
        # e services/push.py) -- reaproveita o mesmo gate acima (so
        # roda na primeira confirmacao) em vez de criar coluna nova so
        # pra isso. Nenhum dos dois pode derrubar o fluxo -- mas
        # diferente do push (que ja nunca levanta excecao, ver
        # services/push.py), o e-mail tem o resultado GRAVADO no pedido
        # (marcar_notificacao_venda_enviada) em vez de so um
        # `except: pass` -- antes disso, se esse e-mail falhasse
        # (ex: EMAIL_NOTIFICACAO_VENDA errado, Brevo bloqueando) nao
        # havia nenhum jeito de saber nem de reenviar (ver conversa,
        # caso real: venda confirmada sem nenhum aviso por e-mail).
        try:
            resultado_notificacao = enviar_notificacao_venda(
                pedido_pago, url_for("admin_pedido_detalhe", token=token, _external=True)
            )
        except Exception as exc:
            resultado_notificacao = {"erro": f"Erro inesperado ao notificar: {exc}"}
        marcar_notificacao_venda_enviada(token, erro=resultado_notificacao.get("erro"))

        enviar_notificacao_push(
            titulo=f"🎉 Você vendeu {_formatar_preco(pedido_pago['total'])}",
            corpo=f"Pedido #{pedido_pago['codigo']}",
            url=url_for("admin_pedido_detalhe", token=token, _external=True),
            icone=url_for("static", filename="img/venda-icone.png"),
        )


# Mesmo texto usado em static/js/carrinho_pagina.js (FRETE_RETIRADA_TEXTO)
# pra montar o frete_descricao do pedido quando o cliente escolhe retirar
# no local -- usado aqui pra trocar os rotulos da timeline ("enviado" nao
# faz sentido pra quem vai retirar -- ver conversa).
FRETE_RETIRADA_DESCRICAO = "Retirada no local"

_PEDIDO_TIMELINE_ETAPAS = (
    ("criado", "Pedido criado"),
    ("pendente", "Aguardando pagamento"),
    ("pago", "Pagamento confirmado"),
    ("faturado", "Pedido faturado"),
    ("enviado", "Pedido enviado"),
    ("entregue", "Pedido entregue"),
)

_PEDIDO_TIMELINE_ETAPAS_RETIRADA = (
    ("criado", "Pedido criado"),
    ("pendente", "Aguardando pagamento"),
    ("pago", "Pagamento confirmado"),
    ("faturado", "Pedido faturado"),
    ("enviado", "Pronto para retirada"),
    ("entregue", "Retirado"),
)

# Posicao de cada status real do banco na timeline acima -- "criado" nao
# e´ um status de verdade (todo pedido ja´ nasce alem dele, so existe
# pra dar o primeiro ponto sempre preenchido), por isso comeca em 1 pra
# status_valido == "pendente". As duas timelines tem as mesmas chaves na
# mesma ordem, entao o indice serve pras duas.
_TIMELINE_INDICE_POR_STATUS = {chave: i for i, (chave, _) in enumerate(_PEDIDO_TIMELINE_ETAPAS)}


def _timeline_do_pedido(pedido: dict) -> list[dict] | None:
    """Timeline visual de progresso (ver templates/pedido.html) -- nao
    faz sentido pra pedido cancelado/excluido/lead do whatsapp (essas
    sao saidas do fluxo normal, nao uma etapa "concluida"), entao
    devolve None nesses casos."""
    if pedido["status"] in ("cancelado", "excluido", "whatsapp"):
        return None
    etapas = (
        _PEDIDO_TIMELINE_ETAPAS_RETIRADA
        if pedido.get("frete_descricao") == FRETE_RETIRADA_DESCRICAO
        else _PEDIDO_TIMELINE_ETAPAS
    )
    indice_atual = _TIMELINE_INDICE_POR_STATUS.get(pedido["status"], 0)
    return [
        {"chave": chave, "rotulo": rotulo, "concluido": i <= indice_atual, "atual": i == indice_atual}
        for i, (chave, rotulo) in enumerate(etapas)
    ]


# "chave_preco" -> formato, so pros 4 formatos de item de santo do
# catalogo escolhido DIRETO (sem passar por 2 lados/personalizada, ver
# _itens_repetiveis_do_pedido abaixo) -- medalha_2lados/entremeio_2lados/
# chaveiro_2lados ficam de fora de proposito (sao sempre um construto
# de personalizada por baixo, nunca tem produtoId no nivel raiz do
# item, ver static/js/personalizada.js).
_FORMATO_POR_CHAVE_SIMPLES = {"12mm": "medalha", "16mm": "medalha", "entremeio": "entremeio", "chaveiro": "chaveiro"}


def _itens_repetiveis_do_pedido(pedido: dict) -> list[dict]:
    """Itens desse pedido que dá pra "repetir" com 1 clique (ver
    static/js/pedido.js:repetirPedido, botao "Repetir esse pedido" em
    pedido.html) -- so santo do catalogo escolhido direto, com
    produtoId valido. Peca personalizada (sem produtoId proprio, foto
    exclusiva daquele pedido) e item de 2 lados (sempre um construto
    de personalizada) ficam de fora -- nao da pra "repetir" sem passar
    pelo simulador nesses casos."""
    itens = []
    for item in pedido["itens"]:
        produto_id = item.get("produtoId")
        chave_preco = item.get("chave_preco")
        formato = _FORMATO_POR_CHAVE_SIMPLES.get(chave_preco)
        if not produto_id or not formato:
            continue
        # pra "medalha", chave_preco JA E´ o tamanho (12mm/16mm) -- so cai
        # no item["tamanho"] quando ele nao veio preenchido (carrinhos
        # antigos, ver static/js/carrinho.js:_migrarItemLegado).
        tamanho = item.get("tamanho") or (chave_preco if formato == "medalha" else None)
        itens.append(
            {
                "produtoId": produto_id,
                "produtoNome": item.get("produtoNome", ""),
                "modeloId": item.get("modeloId", ""),
                "modeloNome": item.get("modeloNome", ""),
                "imagem": item.get("imagem", ""),
                "formato": formato,
                "chave_preco": chave_preco,
                "tamanho": tamanho,
                "cor": item.get("cor") or None,
                "quantidade": item.get("quantidade", 1),
            }
        )
    return itens


@app.route("/pedido/<token>", methods=["GET"])
def ver_pedido(token: str):
    pedido = obter_pedido(token)
    if pedido is None:
        abort(404)
    # ?obrigado=1 vem do redirect_url da InfinitePay (ver
    # _gerar_link_pagamento_para_pedido) -- so mostra o bloco de
    # "obrigado pela compra" nesse primeiro retorno, nao em toda
    # visita futura a essa mesma pagina de acompanhamento. Sempre
    # confere o status de verdade no banco tambem -- o parametro na
    # URL sozinho nao prova nada.
    mostrar_obrigado = request.args.get("obrigado") == "1" and pedido["status"] == "pago"
    oportunidades_upsell = _oportunidades_upsell_do_pedido(pedido) if mostrar_obrigado else []
    return render_template(
        "pedido.html",
        pedido=pedido,
        mostrar_obrigado=mostrar_obrigado,
        oportunidades_upsell=oportunidades_upsell,
        timeline=_timeline_do_pedido(pedido),
        previsoes=previsoes_do_pedido(pedido),
        itens_repetir=_itens_repetiveis_do_pedido(pedido),
    )


# "Meus pedidos" -- atalho OPCIONAL pra quem quer ver de novo todos os
# proprios pedidos sem ter guardado cada link de acompanhamento avulso
# (/pedido/<token>, sempre continua funcionando sozinho). Login so por
# CPF + codigo de 6 digitos por e-mail (ver services/pedidos.py e
# services/email.py:enviar_codigo_verificacao), sem senha pra cadastrar
# nem guardar. Baixar a foto personalizada continua so por fora
# (WhatsApp) -- essa tela so mostra status, nunca expõe a imagem.
_MEUS_PEDIDOS_SESSAO_DOCUMENTO = "meus_pedidos_documento"
_MEUS_PEDIDOS_SESSAO_PENDENTE = "meus_pedidos_documento_pendente"

_STATUS_LABEL_CLIENTE = {
    "pendente": "Aguardando pagamento",
    "pago": "Pagamento confirmado",
    "faturado": "Faturado",
    "enviado": "Enviado",
    "entregue": "Entregue",
    "cancelado": "Cancelado",
}


@app.route("/meus-pedidos", methods=["GET"])
def meus_pedidos():
    documento = session.get(_MEUS_PEDIDOS_SESSAO_DOCUMENTO)
    if documento:
        pedidos = listar_pedidos_por_documento(documento)
        for pedido in pedidos:
            pedido["status_label"] = _STATUS_LABEL_CLIENTE.get(pedido["status"], pedido["status"])
        return render_template("meus_pedidos.html", etapa="lista", pedidos=pedidos)
    if session.get(_MEUS_PEDIDOS_SESSAO_PENDENTE):
        return render_template("meus_pedidos.html", etapa="codigo", erro=request.args.get("erro"))
    return render_template("meus_pedidos.html", etapa="documento", erro=request.args.get("erro"))


@app.route("/meus-pedidos/enviar-codigo", methods=["POST"])
@limiter.limit("5 per minute")
def meus_pedidos_enviar_codigo():
    documento = (request.form.get("documento") or "").strip()
    if not cpf_valido(documento):
        return redirect(url_for("meus_pedidos", erro="documento"))
    codigo = gerar_codigo_verificacao_documento(documento)
    email = email_para_documento(documento)
    if email:
        enviar_codigo_verificacao(email, codigo)
    # Sempre segue pro passo do codigo, mesmo quando esse CPF nunca fez
    # pedido nenhum (email None acima) -- se a resposta fosse diferente
    # nesse caso, daria pra usar esse formulario pra descobrir se um CPF
    # de outra pessoa ja comprou aqui ou nao (ver services/pedidos.py:
    # gerar_codigo_verificacao_documento).
    session[_MEUS_PEDIDOS_SESSAO_PENDENTE] = documento
    session.pop(_MEUS_PEDIDOS_SESSAO_DOCUMENTO, None)
    return redirect(url_for("meus_pedidos"))


@app.route("/meus-pedidos/verificar", methods=["POST"])
@limiter.limit("10 per minute")
def meus_pedidos_verificar():
    documento = session.get(_MEUS_PEDIDOS_SESSAO_PENDENTE)
    if not documento:
        return redirect(url_for("meus_pedidos"))
    codigo = (request.form.get("codigo") or "").strip()
    if verificar_codigo_documento(documento, codigo):
        session[_MEUS_PEDIDOS_SESSAO_DOCUMENTO] = documento
        session.pop(_MEUS_PEDIDOS_SESSAO_PENDENTE, None)
        return redirect(url_for("meus_pedidos"))
    return redirect(url_for("meus_pedidos", erro="codigo"))


@app.route("/meus-pedidos/trocar-cpf", methods=["POST"])
def meus_pedidos_trocar_cpf():
    session.pop(_MEUS_PEDIDOS_SESSAO_PENDENTE, None)
    return redirect(url_for("meus_pedidos"))


@app.route("/meus-pedidos/sair", methods=["POST"])
def meus_pedidos_sair():
    session.pop(_MEUS_PEDIDOS_SESSAO_DOCUMENTO, None)
    session.pop(_MEUS_PEDIDOS_SESSAO_PENDENTE, None)
    return redirect(url_for("meus_pedidos"))


@app.route("/pedido/<token>/boleto.pdf", methods=["GET"])
@limiter.limit("20 per minute")
def ver_boleto_pdf(token: str):
    """Baixa o PDF do boleto sob demanda (nunca guardado no banco, ver
    services/pedidos.py) -- token da URL de acompanhamento ja´ funciona
    como a mesma "senha" que da´ acesso ao resto do pedido, entao nao
    precisa de autenticacao extra aqui."""
    pedido = obter_pedido(token)
    if pedido is None or not pedido.get("inter_codigo_solicitacao"):
        abort(404)
    resultado = baixar_pdf(pedido["inter_codigo_solicitacao"])
    if "erro" in resultado:
        abort(502)
    pdf_bytes = base64.b64decode(resultado["pdf_base64"])
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"boleto-{pedido['codigo']}.pdf",
    )


def _autenticacao_admin_valida(auth) -> bool:
    # sem as duas credenciais configuradas, o painel fica bloqueado
    # por padrao (nunca expõe pedido de ninguem sem senha definida).
    if not ADMIN_USER or not ADMIN_PASSWORD or auth is None:
        return False
    usuario_ok = hmac.compare_digest(auth.username or "", ADMIN_USER)
    senha_ok = hmac.compare_digest(auth.password or "", ADMIN_PASSWORD)
    return usuario_ok and senha_ok


@app.route("/admin/pedidos", methods=["GET"])
@limiter.limit("30 per minute")
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
    mostrar_arquivados = request.args.get("arquivados") == "1"
    pedidos = listar_pedidos(status=status_filtro, arquivados=mostrar_arquivados)
    return render_template(
        "admin_pedidos.html",
        pedidos=pedidos,
        status_filtro=status_filtro,
        mostrar_arquivados=mostrar_arquivados,
        vapid_chave_publica=obter_application_server_key(),
        estatisticas=estatisticas_hoje(),
    )


def _atribuir_numeros_modelo_personalizada(pedido: dict) -> None:
    """Numera cada FOTO personalizada do pedido (ver services/pedidos.py:
    numero_modelo_personalizada) -- contador GLOBAL e sequencial (nunca
    reinicia por pedido, so quando a usuaria pedir -- ver conversa), pra
    identificar cada foto na producao sem depender de nome de santo
    (ela nao tem, e´ uma foto do cliente).

    Item de 1 lado ganha UM numero pra peca inteira -- muda modeloNome
    pra "Modelo N" (MESMO formato ja usado nos produtos do catalogo, ver
    _modelo_csv_do_item, que ja sabe tirar o prefixo "Modelo " sozinho)
    e guarda o numero cru em numeroModeloPersonalizada pro nome do
    arquivo baixado (ver templates/admin_pedido_detalhe.html).

    Item de 2 lados numera lado1/lado2 SEPARADO (ver conversa: cada
    foto e´ um design distinto que a producao imprime por conta
    propria, mesmo as duas fazendo parte da MESMA peca fisica no fim) --
    guarda em numeroModeloPersonalizadaLado1/2, usados tanto no nome do
    arquivo quanto nas linhas do CSV (ver _linhas_csv_do_item acima).

    Tudo isso e´ feito no dict do pedido em MEMORIA (nunca grava de
    volta no banco) -- so o numero em si e´ persistido, numa tabela
    separada por (pedido_token, item_index, lado), pra sempre devolver o
    MESMO numero em toda visita futura a essa foto."""
    for indice, item in enumerate(pedido["itens"]):
        if item.get("duasFaces"):
            if item.get("imagemRecorteLado1"):
                item["numeroModeloPersonalizadaLado1"] = numero_modelo_personalizada(
                    pedido["token"], indice, lado="lado1"
                )
            if item.get("imagemRecorteLado2"):
                item["numeroModeloPersonalizadaLado2"] = numero_modelo_personalizada(
                    pedido["token"], indice, lado="lado2"
                )
            continue
        if item.get("imagemRecorte"):
            numero = numero_modelo_personalizada(pedido["token"], indice)
            item["modeloNome"] = f"Modelo {numero}"
            item["numeroModeloPersonalizada"] = numero


_ASSINATURA_WHATSAPP_CLIENTE = (
    "\n\nQualquer dúvida é só falar. Deus abençoe. Shalom! :)\nÍtalo Santiago -- Nove de Julho"
)


def _itens_texto_whatsapp(pedido: dict) -> str:
    return "\n".join(
        f"- {item.get('quantidade', 1)}x {item.get('descricao') or item.get('chave_preco', '')}"
        for item in pedido["itens"]
    )


def _mensagem_whatsapp_cliente(pedido: dict) -> str:
    """Mensagem pronta pro botao de WhatsApp do cliente no admin (ver
    templates/admin_pedido_detalhe.html) -- o CONTEUDO muda de acordo
    com o status do pedido, sempre com os dados/links relevantes
    daquele momento (pedido do usuario: clicar no wpp do cliente ja
    abrir com a mensagem certa pro que esta acontecendo com o pedido,
    em vez de precisar escrever/copiar informacao na mao toda vez).
    Devolve "" pros status sem mensagem especial definida (whatsapp,
    excluido) -- nesse caso o botao abre sem texto nenhum, como sempre
    foi."""
    nome = pedido.get("cliente_nome", "")
    codigo = pedido["codigo"]
    itens_texto = _itens_texto_whatsapp(pedido)
    frete = pedido.get("frete_descricao") or "a combinar"
    total = _formatar_preco(pedido["total"])
    link_pedido = url_for("ver_pedido", token=pedido["token"], _external=True)

    if pedido["status"] == "pendente":
        if pedido.get("inter_codigo_solicitacao"):
            # boleto ja emitido -- linha digitavel/codigo de barras ja
            # ficaram salvos na hora (ver salvar_dados_boleto_inter),
            # nao precisa gerar nada novo pra mandar direto na mensagem.
            pagamento_texto = (
                f"Boleto -- código de barras: {pedido.get('inter_codigo_barras', '')}\n"
                f"Baixar o boleto: {url_for('ver_boleto_pdf', token=pedido['token'], _external=True)}\n"
            )
        else:
            # Pix/cartao: o link de pagamento original expira sem prazo
            # documentado pela InfinitePay (ver api_pedido_novo_link) --
            # gerar um aqui de novo a cada carregamento da pagina do
            # admin seria uma chamada de API a toa toda vez que o
            # admin so abre o pedido. O link do pedido ja tem o botao
            # "gerar novo link de pagamento" pronto (ver pedido.html).
            pagamento_texto = ""
        return (
            f"Olá {nome}, o seu pedido #{codigo} no site Nove de Julho foi criado com os itens:\n"
            f"{itens_texto}\n"
            f"Frete: {frete}\n"
            f"Total: {total}\n\n"
            f"Estamos aguardando seu pagamento.\n"
            f"{pagamento_texto}"
            f"Pra acompanhar o pedido, o link é esse: {link_pedido}"
            f"{_ASSINATURA_WHATSAPP_CLIENTE}"
        )

    if pedido["status"] == "cancelado":
        url_pix = url_for("pedido_reativar_pix", token=pedido["token"], _external=True)
        url_boleto = url_for("pedido_reativar_boleto", token=pedido["token"], _external=True)
        return (
            f"Olá {nome}! Seu pedido #{codigo} acabou sendo cancelado por falta de pagamento, mas as "
            f"peças continuam com os valores imperdíveis de quando você montou:\n"
            f"{itens_texto}\n"
            f"Frete: {frete}\n"
            f"Total: {total}\n\n"
            f"Dá pra fechar sem refazer nada -- é só escolher:\n"
            f"Pix/cartão: {url_pix}\n"
            f"Boleto: {url_boleto}"
            f"{_ASSINATURA_WHATSAPP_CLIENTE}"
        )

    if pedido["status"] == "pago":
        previsao_envio = _formatar_data_br(previsoes_do_pedido(pedido).get("previsao_envio"))
        previsao_texto = f"Previsão de envio: até {previsao_envio}.\n" if previsao_envio else ""
        return (
            f"Olá {nome}! Seu pedido #{codigo} está confirmado e já entrou em produção. Em breve "
            f"emitimos a nota fiscal.\n"
            f"{previsao_texto}"
            f"Pra acompanhar tudo: {link_pedido}"
            f"{_ASSINATURA_WHATSAPP_CLIENTE}"
        )

    if pedido["status"] == "faturado":
        previsao_envio = _formatar_data_br(previsoes_do_pedido(pedido).get("previsao_envio"))
        previsao_texto = f" Previsão de envio: até {previsao_envio}." if previsao_envio else ""
        link_nf = pedido.get("link_nota_fiscal") or ""
        nf_texto = f" Aqui está a nota fiscal: {link_nf}" if link_nf else ""
        return (
            f"Olá {nome}! Seu pedido #{codigo} foi faturado.{nf_texto}\n"
            f"Logo mais será enviado.{previsao_texto}\n"
            f"Pra acompanhar: {link_pedido}"
            f"{_ASSINATURA_WHATSAPP_CLIENTE}"
        )

    if pedido["status"] == "enviado":
        previsao_entrega = _formatar_data_br(previsoes_do_pedido(pedido).get("previsao_entrega"))
        transportadora = pedido.get("transportadora") or ""
        codigo_rastreio = pedido.get("codigo_rastreio") or ""
        link_rastreio = pedido.get("link_rastreio") or ""
        transportadora_texto = f" pela {transportadora}" if transportadora else ""
        rastreio_texto = f", código de rastreio {codigo_rastreio}" if codigo_rastreio else ""
        link_rastreio_texto = f"Rastreio: {link_rastreio}\n" if link_rastreio else ""
        previsao_texto = f"Previsão de entrega: até {previsao_entrega}.\n" if previsao_entrega else ""
        return (
            f"Olá {nome}! Seu pedido #{codigo} já foi enviado{transportadora_texto}{rastreio_texto}.\n"
            f"{link_rastreio_texto}"
            f"{previsao_texto}"
            f"Pra acompanhar: {link_pedido}"
            f"{_ASSINATURA_WHATSAPP_CLIENTE}"
        )

    if pedido["status"] == "entregue":
        url_avaliar = url_for("avaliar_geral", _external=True)
        return (
            f"Olá {nome}! Que alegria saber que seu pedido #{codigo} já chegou! :)\n"
            f"Poderia avaliar sua compra? Leva menos de 1 minuto: {url_avaliar}"
            f"{_ASSINATURA_WHATSAPP_CLIENTE}"
        )

    return ""


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
    _atribuir_numeros_modelo_personalizada(pedido)
    return render_template(
        "admin_pedido_detalhe.html",
        pedido=pedido,
        mensagem_whatsapp_cliente=_mensagem_whatsapp_cliente(pedido),
    )


@app.route("/admin/pedidos/<token>/csv", methods=["GET"])
def admin_pedido_csv(token: str):
    """CSV pra produção/expedição (uso interno, nao pro cliente) -- ver
    conversa: o usuario ja usa uma planilha com essas colunas pra
    organizar a produção."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    pedido = obter_pedido(token)
    if pedido is None:
        abort(404)
    _atribuir_numeros_modelo_personalizada(pedido)

    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(["Produto", "Modelo", "Variação", "Quantidade"])
    for linha in _linhas_csv_pedido(pedido):
        escritor.writerow(linha)

    # utf-8-sig (BOM no inicio) -- Excel no Windows so reconhece acento
    # certo em CSV com esse prefixo, senao mostra "Variacao" quebrado.
    conteudo_bytes = buffer.getvalue().encode("utf-8-sig")
    resposta = Response(conteudo_bytes, mimetype="text/csv")
    resposta.headers["Content-Disposition"] = f'attachment; filename="pedido-{pedido["codigo"]}.csv"'
    return resposta


@app.route("/admin/pedidos/csv-total", methods=["POST"])
def admin_pedidos_csv_total():
    """CSV de producao com os pedidos SELECIONADOS no painel (ver
    templates/admin_pedidos.html, botao "Baixar CSV total" na barra de
    selecao em massa), um em seguida do outro, na mesma ordem da
    selecao.

    O programa de producao MONTA UMA FOLHA POR TAMANHO (variacao 12 ou
    16 -- 29/chaveiro fica de fora de proposito, ver
    _TAMANHOS_COM_SEPARADOR_CSV_TOTAL abaixo: mais raro, o usuario
    prefere se virar sem separador ali), juntando so as linhas daquele
    tamanho -- nao mantem os pedidos agrupados. Entao 2 pedidos que
    compartilham um tamanho ficam com as linhas desse tamanho grudadas
    uma na outra dentro da folha, mesmo que NAO sejam consecutivos na
    selecao (ex: pedido 1 tem 12 e 16, pedido 2 so´ tem 12, pedido 3 so´
    tem 16 -- na folha do 16, o pedido 1 fica colado no pedido 3, pulando
    o 2 inteiro, ver conversa). Por isso o separador nao compara so´
    pedidos vizinhos: pra cada tamanho, acha a ULTIMA vez que ele
    apareceu (em qualquer pedido anterior, vizinho ou nao) e marca uma
    linha "Nove de Julho,1,<tamanho>,1" logo depois DAQUELE pedido --
    essa linha some junto com o resto na hora de montar a folha daquele
    tamanho, servindo de marcador visual so´ ali."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    tokens = request.form.getlist("tokens")
    status_filtro = str(request.form.get("status_filtro", "")).strip() or None
    arquivados = request.form.get("arquivados") == "1"
    if not tokens:
        return redirect(url_for("admin_pedidos", status=status_filtro, arquivados="1" if arquivados else None))

    linhas_por_pedido = []
    for token in tokens:
        pedido = obter_pedido(token)
        if pedido is None:
            continue
        _atribuir_numeros_modelo_personalizada(pedido)
        linhas_por_pedido.append(_linhas_csv_pedido(pedido))

    # pra cada tamanho, achar em que indice de pedido ele apareceu por
    # ultimo -- na proxima vez que reaparecer (nao precisa ser no pedido
    # seguinte), marca separador logo apos ESSE ultimo indice.
    ultima_ocorrencia: dict[str, int] = {}
    separadores_apos_indice: dict[int, set] = {}
    for indice, linhas in enumerate(linhas_por_pedido):
        tamanhos = {linha[2] for linha in linhas} & _TAMANHOS_COM_SEPARADOR_CSV_TOTAL
        for tamanho in tamanhos:
            if tamanho in ultima_ocorrencia:
                separadores_apos_indice.setdefault(ultima_ocorrencia[tamanho], set()).add(tamanho)
            ultima_ocorrencia[tamanho] = indice

    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(["Produto", "Modelo", "Variação", "Quantidade"])
    for indice, linhas in enumerate(linhas_por_pedido):
        for linha in linhas:
            escritor.writerow(linha)
        for tamanho in sorted(separadores_apos_indice.get(indice, ())):
            escritor.writerow(["Nove de Julho", 1, tamanho, 1])

    conteudo_bytes = buffer.getvalue().encode("utf-8-sig")
    resposta = Response(conteudo_bytes, mimetype="text/csv")
    resposta.headers["Content-Disposition"] = 'attachment; filename="pedidos-selecionados.csv"'
    return resposta


@app.route("/admin/pedidos/zip-personalizadas", methods=["POST"])
def admin_pedidos_zip_personalizadas():
    """Zip com as imagens 1:1 de producao (recorte, ver
    services/imagens_personalizadas.py) de TODAS as pecas personalizadas
    dos pedidos SELECIONADOS no painel -- mesmo nome de arquivo
    (personalizada_modelo_<numero>.png) que os links avulsos "Baixar
    imagem 1:1" ja usam (ver templates/admin_pedido_detalhe.html), pra
    quem baixa em massa reconhecer cada peca do mesmo jeito. Pedido sem
    nenhuma peca personalizada so nao contribui nada pro zip."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    tokens = request.form.getlist("tokens")
    status_filtro = str(request.form.get("status_filtro", "")).strip() or None
    arquivados = request.form.get("arquivados") == "1"
    if not tokens:
        return redirect(url_for("admin_pedidos", status=status_filtro, arquivados="1" if arquivados else None))

    buffer = io.BytesIO()
    total_imagens = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_arquivo:
        for token in tokens:
            pedido = obter_pedido(token)
            if pedido is None:
                continue
            _atribuir_numeros_modelo_personalizada(pedido)
            for item in pedido["itens"]:
                for numero, url in _recortes_personalizados_do_item(item):
                    if not url.startswith(_PREFIXO_IMAGEM_PERSONALIZADA):
                        continue
                    entrada = obter_imagem(url[len(_PREFIXO_IMAGEM_PERSONALIZADA):])
                    if entrada is None:
                        continue
                    dados, _mimetype, _nome_arquivo = entrada
                    zip_arquivo.writestr(f"personalizada_modelo_{numero}.png", dados)
                    total_imagens += 1

    if total_imagens == 0:
        return redirect(url_for("admin_pedidos", status=status_filtro, arquivados="1" if arquivados else None))

    buffer.seek(0)
    return send_file(buffer, mimetype="application/zip", as_attachment=True, download_name="personalizadas.zip")


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
    transportadora = str(request.form.get("transportadora", "")).strip() or None
    link_nota_fiscal = str(request.form.get("link_nota_fiscal", "")).strip() or None

    pedido_atualizado = atualizar_status(
        token,
        novo_status,
        codigo_rastreio=codigo_rastreio,
        link_rastreio=link_rastreio,
        transportadora=transportadora,
        link_nota_fiscal=link_nota_fiscal,
    )
    if pedido_atualizado is None:
        abort(400, description="Status inválido.")

    if novo_status == "enviado" and pedido_antes["status"] != "enviado":
        _reenviar_email_pedido_enviado(token)

    if novo_status == "entregue" and pedido_antes["status"] != "entregue":
        _enviar_email_avaliacao(token)

    # dispara so na PRIMEIRA vez que o link e´ preenchido (nao dispara
    # de novo se o admin so corrigir o link depois, ver conversa: "se
    # eu preencher o link com a nota, mande e-mail").
    if link_nota_fiscal and not pedido_antes.get("link_nota_fiscal"):
        _reenviar_email_nota_fiscal(token)

    return redirect(url_for("admin_pedido_detalhe", token=token))


@app.route("/admin/pedidos/<token>/editar-valor", methods=["POST"])
def admin_pedido_editar_valor(token: str):
    """Corrige o valor de um pedido ja existente (ver conversa -- admin
    digitou errado no confirmar-venda manual do WhatsApp e so percebeu
    depois de confirmado). Reconstroi total = subtotal + frete_preco
    (ver services.pedidos.editar_valor), nunca deixa a pagina do
    pedido mostrar uma quebra que nao bate. Nao muda nada em gateway
    de pagamento nenhum -- so corrige o registro aqui, a diferenca com
    o que foi cobrado de verdade (Pix/cartao/boleto) precisa ser
    resolvida por fora quando o pedido ja foi pago pelo site."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    pedido = obter_pedido(token)
    if pedido is None:
        abort(404)
    if pedido["status"] in ("whatsapp", "cancelado", "excluido"):
        abort(400, description="Esse pedido não pode ter o valor corrigido por aqui.")

    try:
        subtotal = float(str(request.form.get("subtotal", "")).replace(",", "."))
        frete_preco = float(str(request.form.get("frete_preco", "")).replace(",", "."))
    except ValueError:
        abort(400, description="Subtotal e frete precisam ser números válidos.")
    if subtotal < 0 or frete_preco < 0:
        abort(400, description="Subtotal e frete não podem ser negativos.")

    valor_pago_bruto = str(request.form.get("valor_pago", "")).strip()
    valor_pago = None
    if valor_pago_bruto:
        try:
            valor_pago = float(valor_pago_bruto.replace(",", "."))
        except ValueError:
            abort(400, description="Valor pago precisa ser um número válido.")
        if valor_pago < 0:
            abort(400, description="Valor pago não pode ser negativo.")

    editar_valor(token, subtotal=subtotal, frete_preco=frete_preco, valor_pago=valor_pago)
    return redirect(url_for("admin_pedido_detalhe", token=token))


# Formatos editaveis pelo painel (ver admin_pedido_editar_item_formato) --
# mesmos 6 formatos de sempre (_FORMATO_LABEL acima), sem as variantes
# "personalizada" (essas ja chegam com chave_preco certa desde a
# criacao, via /personalizada -- esse conserto e´ so pro item digitado a
# mao no "Pedido manual", ver admin_pedido_criar_manual).
_FORMATOS_ITEM_MANUAL = ("medalha", "entremeio", "chaveiro", "medalha_2lados", "entremeio_2lados", "chaveiro_2lados")


@app.route("/admin/pedidos/<token>/itens/<int:indice>/editar-formato", methods=["POST"])
def admin_pedido_editar_item_formato(token: str, indice: int):
    """Corrige formato/tamanho/cor (e por tabela, chave_preco) de um
    item -- pensado pro item do "Pedido manual" (ver
    admin_pedido_criar_manual), que salva chave_preco="" por nao ter
    como saber o material de verdade so com o texto digitado a mao.
    Sem chave_preco valida, a Tiny recebe codigo/descricao em branco
    pro produto (ver services/tiny.py:_chave_material -- so reconhece
    as chaves de services/pricing.py:CHAVES_PRECO) e a sincronizacao
    (admin_pedido_reenviar_tiny) nao manda o produto de verdade. Aqui o
    admin escolhe o formato certo, do mesmo jeito que o carrinho do
    site monta um item de catalogo -- nao mexe em quantidade nem no
    valor cobrado do cliente."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    pedido = obter_pedido(token)
    if pedido is None or not (0 <= indice < len(pedido["itens"])):
        abort(404)
    if pedido["status"] in ("cancelado", "excluido"):
        abort(400, description="Esse pedido não pode ter itens corrigidos por aqui.")

    produto_nome = str(request.form.get("produto_nome", "")).strip()
    formato = str(request.form.get("formato", ""))
    tamanho = str(request.form.get("tamanho", ""))
    cor = str(request.form.get("cor", ""))
    if formato not in _FORMATOS_ITEM_MANUAL:
        abort(400, description="Escolha um formato válido.")

    if formato == "medalha":
        if tamanho not in ("12mm", "16mm"):
            abort(400, description="Escolha o tamanho da medalha.")
        chave_preco = tamanho
        cor = ""
    elif formato == "medalha_2lados":
        if tamanho not in ("14mm", "18mm") or cor not in ("prata", "ouro_velho"):
            abort(400, description="Escolha o tamanho e a cor da medalha de 2 lados.")
        chave_preco = formato
    elif formato in ("entremeio", "entremeio_2lados"):
        if cor not in ("prata", "ouro_velho"):
            abort(400, description="Escolha a cor do entremeio.")
        chave_preco = formato
        tamanho = ""
    else:  # chaveiro / chaveiro_2lados -- sem tamanho nem cor
        chave_preco = formato
        tamanho = ""
        cor = ""

    item = dict(pedido["itens"][indice])
    item.update({
        "produtoNome": produto_nome, "modeloNome": "", "formato": formato,
        "tamanho": tamanho, "cor": cor, "chave_preco": chave_preco,
    })
    detalhe = _detalhe_formato_do_item(item)
    item["detalhe"] = detalhe
    item["descricao"] = " — ".join(p for p in (produto_nome, detalhe) if p) or detalhe

    editar_item_formato(token, indice, item=item)
    return redirect(url_for("admin_pedido_detalhe", token=token))


@app.route("/admin/pedidos/<token>/marcar-pago", methods=["POST"])
def admin_pedido_marcar_pago(token: str):
    """Confirma manualmente um pedido "pendente" criado pelo site (Pix/
    cartão via InfinitePay) -- pensado como escape hatch quando o
    webhook falha por qualquer motivo e o pagamento fica preso sem
    confirmar aqui, mesmo tendo sido aprovado de verdade (confira
    sempre no extrato/painel da InfinitePay antes de usar isso, não há
    nenhuma verificação além da senha do admin). Caso real que já
    aconteceu: um link de pagamento gerado ANTES de
    WEBHOOK_INFINITEPAY_SECRET ser configurado guarda a URL de
    callback antiga (sem a chave) -- essa chamada nunca mais vai bater
    com a chave exigida agora, então o webhook original nunca confirma
    esse pedido específico."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    pedido = obter_pedido(token)
    if pedido is None or pedido["status"] != "pendente":
        abort(400, description="Só é possível confirmar manualmente um pedido pendente.")

    pedido_pago = marcar_pago(
        token,
        forma_pagamento="manual",
        parcelas=None,
        valor_pago=pedido["total"],
        transaction_nsu="confirmado-manualmente",
    )
    _pos_pagamento_confirmado(pedido_pago, token)
    return redirect(url_for("admin_pedido_detalhe", token=token))


@app.route("/admin/tiny/buscar-contato", methods=["GET"])
def admin_tiny_buscar_contato():
    """Busca contatos ja cadastrados na Tiny (ver
    services/tiny.py:buscar_contatos_tiny) -- usado no formulario de
    "Confirmar venda" pra puxar o endereco de uma livraria que ja
    fecha pedido com regularidade, em vez de redigitar tudo na mao
    (ver conversa)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    termo = str(request.args.get("q", ""))
    resultado = buscar_contatos_tiny(termo)
    if "erro" in resultado:
        return jsonify(erro=resultado["erro"]), 502
    return jsonify(contatos=resultado["contatos"])


@app.route("/admin/pedidos/<token>/confirmar-venda", methods=["POST"])
def admin_pedido_confirmar_venda(token: str):
    """Promove um lead "whatsapp" (ver api_pedido_criar_whatsapp) pra
    "pago" quando a pessoa realmente fechou o pedido combinado na
    conversa -- os dados de cliente/endereco/frete/pagamento sao
    preenchidos na mao aqui (o WhatsApp nunca coletou isso). A partir
    daqui o pedido segue o mesmo fluxo de um pago pelo site (Tiny,
    timeline, e-mails -- ver _pos_pagamento_confirmado)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    pedido = obter_pedido(token)
    if pedido is None:
        abort(404)

    # Mesmas regras de tipo de pessoa/IE/validacao de documento e telefone
    # do checkout do site (ver _cliente_valido/_endereco_valido acima) --
    # usuaria pediu pra preencher pedido de WhatsApp com as mesmas funcoes
    # (ver conversa). So valida FORMATO (digito verificador/DDD real, ver
    # services/documentos.py) quando o campo vem preenchido -- documento e
    # telefone continuam opcionais aqui (lead do WhatsApp as vezes fecha
    # sem todo dado logo de cara), mas se vier tem que bater.
    cliente_tipo_pessoa = str(request.form.get("cliente_tipo_pessoa", "fisica")).strip()
    cliente_tipo_pessoa = cliente_tipo_pessoa if cliente_tipo_pessoa in ("fisica", "juridica") else "fisica"
    cliente_documento = str(request.form.get("cliente_documento", "")).strip()
    cliente_telefone = str(request.form.get("cliente_telefone", "")).strip()
    cliente_ie_isento = cliente_tipo_pessoa == "juridica" and bool(request.form.get("cliente_ie_isento"))
    cliente_inscricao_estadual = (
        "" if cliente_ie_isento else str(request.form.get("cliente_inscricao_estadual", "")).strip()
    ) if cliente_tipo_pessoa == "juridica" else ""
    cliente = {
        "nome": str(request.form.get("cliente_nome", "")).strip(),
        "tipo_pessoa": cliente_tipo_pessoa,
        "documento": cliente_documento,
        "telefone": cliente_telefone,
        "email": str(request.form.get("cliente_email", "")).strip(),
        "inscricao_estadual": cliente_inscricao_estadual,
        "ie_isento": cliente_ie_isento,
        "ie_nao_contribuinte": cliente_tipo_pessoa == "juridica" and bool(request.form.get("cliente_ie_nao_contribuinte")),
    }
    endereco = {
        "cep": str(request.form.get("endereco_cep", "")).strip(),
        "logradouro": str(request.form.get("endereco_logradouro", "")).strip(),
        "numero": str(request.form.get("endereco_numero", "")).strip(),
        "complemento": str(request.form.get("endereco_complemento", "")).strip(),
        "bairro": str(request.form.get("endereco_bairro", "")).strip(),
        "cidade": str(request.form.get("endereco_cidade", "")).strip(),
        "uf": str(request.form.get("endereco_uf", "")).strip(),
    }
    if not cliente["nome"]:
        abort(400, description="Informe ao menos o nome do cliente.")
    rotulo_documento = "CNPJ" if cliente_tipo_pessoa == "juridica" else "CPF"
    if cliente_documento and not documento_valido(cliente_tipo_pessoa, cliente_documento):
        abort(400, description=f"{rotulo_documento} do cliente inválido. Confira o número digitado.")
    if cliente_telefone and not telefone_valido(cliente_telefone):
        abort(400, description="Telefone do cliente inválido. Confira o DDD e o número digitado.")

    # Entrega em endereco diferente (ex: livraria que recebe por conta
    # de outra pessoa/paroquia, ver conversa) -- so monta o bloco
    # quando o admin realmente marcou/preencheu, senao a entrega usa o
    # endereco do cliente acima mesmo (mesmo criterio do checkout do
    # site, ver _endereco_valido).
    destinatario_nome = str(request.form.get("destinatario_nome", "")).strip()
    destinatario = None
    if destinatario_nome:
        destinatario_tipo_pessoa = str(request.form.get("destinatario_tipo_pessoa", "fisica")).strip()
        destinatario_tipo_pessoa = destinatario_tipo_pessoa if destinatario_tipo_pessoa in ("fisica", "juridica") else "fisica"
        destinatario_documento = str(request.form.get("destinatario_documento", "")).strip()
        destinatario_telefone = str(request.form.get("destinatario_telefone", "")).strip()
        rotulo_destinatario = "CNPJ" if destinatario_tipo_pessoa == "juridica" else "CPF"
        if destinatario_documento and not documento_valido(destinatario_tipo_pessoa, destinatario_documento):
            abort(400, description=f"{rotulo_destinatario} de quem recebe é inválido. Confira o número digitado.")
        if destinatario_telefone and not telefone_valido(destinatario_telefone):
            abort(400, description="Telefone de quem recebe é inválido. Confira o DDD e o número digitado.")
        destinatario = {
            "nome": destinatario_nome,
            "tipo_pessoa": destinatario_tipo_pessoa,
            "documento": destinatario_documento,
            "cep": str(request.form.get("destinatario_cep", "")).strip(),
            "logradouro": str(request.form.get("destinatario_logradouro", "")).strip(),
            "numero": str(request.form.get("destinatario_numero", "")).strip(),
            "complemento": str(request.form.get("destinatario_complemento", "")).strip(),
            "bairro": str(request.form.get("destinatario_bairro", "")).strip(),
            "cidade": str(request.form.get("destinatario_cidade", "")).strip(),
            "uf": str(request.form.get("destinatario_uf", "")).strip(),
            "telefone": destinatario_telefone,
        }

    try:
        frete_preco = float(request.form.get("frete_preco", "0").replace(",", "."))
    except ValueError:
        frete_preco = 0.0
    frete_descricao = str(request.form.get("frete_descricao", "")).strip()
    forma_pagamento = str(request.form.get("forma_pagamento", "")).strip()
    try:
        valor_pago = float(request.form.get("valor_pago", "0").replace(",", "."))
    except ValueError:
        valor_pago = round(pedido["subtotal"] + frete_preco, 2)
    try:
        frete_prazo_dias = int(request.form.get("frete_prazo_dias", ""))
    except ValueError:
        frete_prazo_dias = None

    pedido_pago = confirmar_venda_manual(
        token,
        cliente=cliente,
        endereco=endereco,
        frete_descricao=frete_descricao,
        frete_preco=frete_preco,
        frete_prazo_dias=frete_prazo_dias,
        forma_pagamento=forma_pagamento,
        valor_pago=valor_pago,
        destinatario=destinatario,
    )
    if pedido_pago is None or pedido_pago["status"] != "pago":
        abort(400, description="Esse pedido não é mais um lead do WhatsApp aguardando confirmação.")

    _pos_pagamento_confirmado(pedido_pago, token)

    return redirect(url_for("admin_pedido_detalhe", token=token))


@app.route("/admin/pedidos/novo-manual", methods=["GET"])
def admin_pedido_novo_manual():
    """Formulario pra registrar um pedido negociado por fora do site
    (ex: valor combinado abaixo do minimo de R$30 do checkout normal,
    ver conversa) -- item(ns) e valor digitados na mao pelo admin, sem
    passar pela validacao de minimo/pricing do carrinho (essa so faz
    sentido pro cliente montando o proprio carrinho sozinho). Cria um
    lead "whatsapp" igual ao de api_pedido_criar_whatsapp e cai no
    MESMO fluxo ja existente de "Confirmar venda" (ver
    admin_pedido_confirmar_venda) pra preencher cliente/endereco/frete/
    pagamento e finalizar."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    return render_template("admin_pedido_novo_manual.html")


@app.route("/admin/pedidos/novo-manual", methods=["POST"])
def admin_pedido_criar_manual():
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    descricoes = request.form.getlist("descricao")
    quantidades = request.form.getlist("quantidade")
    valores_unitarios = request.form.getlist("valor_unitario")

    itens = []
    subtotal = 0.0
    for descricao, quantidade_bruta, valor_bruto in zip(descricoes, quantidades, valores_unitarios):
        descricao = descricao.strip()
        if not descricao:
            continue
        try:
            quantidade = int(quantidade_bruta)
            valor_unitario = float(str(valor_bruto).replace(",", "."))
        except ValueError:
            abort(400, description="Quantidade e valor unitário precisam ser números válidos.")
        if quantidade <= 0 or valor_unitario < 0:
            abort(400, description="Quantidade precisa ser maior que zero e o valor não pode ser negativo.")
        itens.append({
            "produtoNome": descricao, "descricao": descricao, "modeloNome": "", "chave_preco": "",
            "quantidade": quantidade, "valor_unitario": valor_unitario,
        })
        subtotal += quantidade * valor_unitario

    if not itens:
        abort(400, description="Informe ao menos um item com descrição, quantidade e valor.")

    cliente_email = str(request.form.get("cliente_email", "")).strip()

    pedido = criar_pedido(
        itens=itens,
        subtotal=round(subtotal, 2),
        frete_descricao="",
        frete_preco=0.0,
        cliente={"email": cliente_email},
        endereco={},
        status_inicial="whatsapp",
    )
    return redirect(url_for("admin_pedido_detalhe", token=pedido["token"]))


@app.route("/admin/pedidos/<token>/descartar-whatsapp", methods=["POST"])
def admin_pedido_descartar_whatsapp(token: str):
    """Descarta um lead "whatsapp" que nao fechou -- reaproveita
    cancelar_pedido (mesma funcao usada no auto-cancelamento de pedido
    pendente abandonado, ver services/pedidos.py)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    if obter_pedido(token) is None:
        abort(404)
    cancelar_pedido(token)
    return redirect(url_for("admin_pedidos"))


@app.route("/admin/pedidos/<token>/excluir", methods=["POST"])
def admin_pedido_excluir(token: str):
    """Exclui um pedido do painel (ver conversa) -- motivo obrigatorio,
    avisa o cliente por e-mail explicando (ver
    services/email.py:enviar_pedido_excluido). NUNCA apaga a linha de
    verdade (ver services.pedidos.excluir_pedido -- so marca status
    "excluido", mantendo o historico)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    pedido = obter_pedido(token)
    if pedido is None:
        abort(404)
    motivo = str(request.form.get("motivo", "")).strip()
    if not motivo:
        abort(400, description="Informe o motivo da exclusão.")

    pedido_excluido = excluir_pedido(token, motivo=motivo)
    enviar_pedido_excluido(pedido_excluido, motivo, url_for("catalogo_completo", _external=True))

    return redirect(url_for("admin_pedidos"))


def _redirecionar_pos_arquivamento():
    """Volta pro mesmo filtro/aba de onde a acao de arquivar/desarquivar
    veio (ver botao individual na lista e o form da tela de detalhe) --
    mesmo padrao ja usado em admin_pedidos_acao_em_massa, pra nao jogar
    o admin de volta pra lista sem filtro nenhum."""
    status_filtro = str(request.form.get("status_filtro", "")).strip() or None
    arquivados = request.form.get("arquivados") == "1"
    if status_filtro or arquivados:
        return redirect(url_for("admin_pedidos", status=status_filtro, arquivados="1" if arquivados else None))
    return redirect(url_for("admin_pedidos"))


@app.route("/admin/pedidos/<token>/arquivar", methods=["POST"])
def admin_pedido_arquivar(token: str):
    """Tira o pedido da lista principal do painel, sem mudar status nem
    avisar o cliente (ver conversa: desafogar o painel de pedidos
    antigos/resolvidos, diferente de excluir). Reversivel a qualquer
    momento pelo filtro "Arquivados" (ver admin_pedido_desarquivar)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    if arquivar_pedido(token) is None:
        abort(404)
    return _redirecionar_pos_arquivamento()


@app.route("/admin/pedidos/<token>/desarquivar", methods=["POST"])
def admin_pedido_desarquivar(token: str):
    """Desfaz admin_pedido_arquivar -- volta o pedido pra lista principal."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    if desarquivar_pedido(token) is None:
        abort(404)
    return _redirecionar_pos_arquivamento()


def _sincronizar_pedido_tiny(token: str) -> str | None:
    """Sincroniza (ou tenta de novo) com a Tiny na mao -- usado pelo
    botao individual (admin_pedido_reenviar_tiny) e pela acao em massa
    (admin_pedidos_acao_em_massa), nunca duplicando essa logica.
    Devolve None se deu certo, ou uma mensagem de erro pra reportar."""
    pedido = obter_pedido(token)
    if pedido is None:
        return "Pedido não encontrado."
    if pedido["status"] not in ("pago", "faturado", "enviado", "entregue"):
        return "Só dá pra sincronizar com a Tiny um pedido já pago."

    if pedido.get("tiny_numero_pedido"):
        # JA tem um numero valido da Tiny -- nao reenvia. A API da Tiny
        # CRIA um pedido novo a cada chamada; ela nem sempre recusa como
        # duplicidade so por ter o mesmo numero_pedido_ecommerce (ver
        # conversa: um reenvio real duplicou o pedido #1119 como um novo
        # #1140 na Tiny, em vez de ser recusado). Entao a garantia contra
        # duplicidade precisa ser NOSSA, aqui, e nao depender da Tiny.
        return (
            f"Pedido já sincronizado com a Tiny (#{pedido['tiny_numero_pedido']}) -- "
            "não reenviado, pra evitar duplicidade."
        )

    try:
        resultado_tiny = criar_pedido_tiny(pedido)
    except Exception as exc:  # nunca deixa o operador numa tela de erro generica
        resultado_tiny = {"erro": f"Erro inesperado ao sincronizar: {exc}"}

    erro = resultado_tiny.get("erro")
    numero = resultado_tiny.get("numero")
    if erro and erro_e_duplicidade(erro) and pedido.get("tiny_numero_pedido"):
        # Defesa extra pra uma corrida rara (dois cliques quase juntos,
        # ou acao em massa com o mesmo pedido selecionado 2x): mesmo
        # tendo passado pelo guard acima, a Tiny ainda pode recusar como
        # duplicidade de verdade -- nesse caso mantem o numero ja
        # conhecido em vez de apagar com None (ver services/tiny.py:
        # erro_e_duplicidade).
        numero, erro = pedido["tiny_numero_pedido"], None

    marcar_tiny_sincronizado(token, numero_pedido=numero, erro=erro)
    return erro


def _reenviar_email_confirmacao(token: str) -> str | None:
    """Reenvia o e-mail de pagamento confirmado na mao -- usado pelo
    botao individual (admin_pedido_reenviar_email) e pela acao em massa
    (admin_pedidos_acao_em_massa). Devolve None se deu certo, ou uma
    mensagem de erro pra reportar."""
    pedido = obter_pedido(token)
    if pedido is None:
        return "Pedido não encontrado."
    if pedido["status"] == "pendente":
        return "Esse pedido ainda não foi pago."
    try:
        resultado_email = enviar_confirmacao_pedido(
            pedido, url_for("ver_pedido", token=token, _external=True)
        )
    except Exception as exc:  # nunca deixa o operador numa tela de erro generica
        resultado_email = {"erro": f"Erro inesperado ao enviar: {exc}"}
    marcar_email_enviado(token, erro=resultado_email.get("erro"))
    return resultado_email.get("erro")


def _reenviar_notificacao_venda(token: str) -> str | None:
    """Reenvia o AVISO INTERNO de venda (pro dono, ver
    services/email.py:enviar_notificacao_venda) -- diferente de
    _reenviar_email_confirmacao acima (esse e´ o e-mail pro CLIENTE).
    Usado pelo botao individual (admin_pedido_reenviar_notificacao_venda)."""
    pedido = obter_pedido(token)
    if pedido is None:
        return "Pedido não encontrado."
    if pedido["status"] == "pendente":
        return "Esse pedido ainda não foi pago."
    try:
        resultado_notificacao = enviar_notificacao_venda(
            pedido, url_for("admin_pedido_detalhe", token=token, _external=True)
        )
    except Exception as exc:  # nunca deixa o operador numa tela de erro generica
        resultado_notificacao = {"erro": f"Erro inesperado ao enviar: {exc}"}
    marcar_notificacao_venda_enviada(token, erro=resultado_notificacao.get("erro"))
    return resultado_notificacao.get("erro")


def _reenviar_email_pedido_enviado(token: str) -> str | None:
    """Reenvia o e-mail "Pedido enviado" na mao -- usado pelo botao
    individual (admin_pedido_reenviar_email_pedido_enviado) e pela
    transicao automatica pra status "enviado" (ver admin_pedido_status).
    Antes disso essa chamada nao tinha try/except NEM registro, entao
    uma falha ficava completamente invisivel (ver conversa)."""
    pedido = obter_pedido(token)
    if pedido is None:
        return "Pedido não encontrado."
    if pedido["status"] not in ("enviado", "entregue"):
        return "Esse pedido ainda não foi marcado como enviado."
    try:
        resultado_email = enviar_pedido_enviado(
            pedido,
            pedido.get("codigo_rastreio") or "",
            pedido.get("link_rastreio") or "",
            url_for("ver_pedido", token=token, _external=True),
            pedido.get("transportadora") or "",
        )
    except Exception as exc:  # nunca deixa o operador numa tela de erro generica
        resultado_email = {"erro": f"Erro inesperado ao enviar: {exc}"}
    marcar_email_pedido_enviado_enviado(token, erro=resultado_email.get("erro"))
    return resultado_email.get("erro")


def _reenviar_email_nota_fiscal(token: str) -> str | None:
    """Reenvia o e-mail "Nota fiscal disponível" na mao -- usado pelo
    botao individual (admin_pedido_reenviar_email_nota_fiscal) e pelo
    preenchimento do link (ver admin_pedido_status)."""
    pedido = obter_pedido(token)
    if pedido is None:
        return "Pedido não encontrado."
    if not pedido.get("link_nota_fiscal"):
        return "Esse pedido ainda não tem link de nota fiscal preenchido."
    try:
        resultado_email = enviar_nota_fiscal_disponivel(
            pedido, url_for("ver_pedido", token=token, _external=True)
        )
    except Exception as exc:  # nunca deixa o operador numa tela de erro generica
        resultado_email = {"erro": f"Erro inesperado ao enviar: {exc}"}
    marcar_email_nota_fiscal_enviado(token, erro=resultado_email.get("erro"))
    return resultado_email.get("erro")


@app.route("/admin/pedidos/<token>/reenviar-tiny", methods=["POST"])
def admin_pedido_reenviar_tiny(token: str):
    """Sincroniza (ou tenta de novo) com a Tiny na mao -- normalmente
    isso acontece sozinho quando o webhook da InfinitePay confirma o
    pagamento (ver webhook_infinitepay), mas so uma vez por pedido. Esse
    botao existe pra reprocessar quando a primeira tentativa falhou (ex:
    Tiny fora do ar, token invalido na hora) ou quando o pedido nunca
    passou pelo webhook (pagamento registrado por fora, teste manual)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    if obter_pedido(token) is None:
        abort(404)
    erro = _sincronizar_pedido_tiny(token)
    if erro == "Só dá pra sincronizar com a Tiny um pedido já pago.":
        abort(400, description=erro)
    return redirect(url_for("admin_pedido_detalhe", token=token, tiny_erro=erro))


@app.route("/admin/pedidos/<token>/reenviar-email", methods=["POST"])
def admin_pedido_reenviar_email(token: str):
    """Reenvia o e-mail de pagamento confirmado na mao -- util quando a
    primeira tentativa falhou por um motivo que ja foi resolvido (ex:
    Brevo bloqueou o IP do servidor por ser novo e precisar de
    autorizacao manual na conta -- depois de autorizado, os envios
    seguintes funcionam sozinhos; esse botao so serve pra reenviar o
    que ja tinha falhado antes da autorizacao)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    if obter_pedido(token) is None:
        abort(404)
    erro = _reenviar_email_confirmacao(token)
    if erro == "Esse pedido ainda não foi pago.":
        abort(400, description=erro)
    return redirect(url_for("admin_pedido_detalhe", token=token))


@app.route("/admin/pedidos/<token>/reenviar-notificacao-venda", methods=["POST"])
def admin_pedido_reenviar_notificacao_venda(token: str):
    """Reenvia o AVISO INTERNO de venda (pro dono da loja) na mao --
    ate essa notificacao ganhar rastreio (ver
    services/pedidos.py:notificacao_venda_enviada/notificacao_venda_erro),
    uma falha nela era invisivel: nenhum e-mail chegava e ninguem sabia
    o motivo nem tinha como reenviar."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    if obter_pedido(token) is None:
        abort(404)
    erro = _reenviar_notificacao_venda(token)
    if erro == "Esse pedido ainda não foi pago.":
        abort(400, description=erro)
    return redirect(url_for("admin_pedido_detalhe", token=token))


@app.route("/admin/pedidos/<token>/reenviar-email-enviado", methods=["POST"])
def admin_pedido_reenviar_email_enviado(token: str):
    """Reenvia o e-mail "Pedido enviado" na mao -- mesmo motivo do botao
    de notificação de venda acima: essa chamada nao tinha nenhum
    rastreio antes (ver services/pedidos.py:email_pedido_enviado_enviado/
    email_pedido_enviado_erro)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    if obter_pedido(token) is None:
        abort(404)
    erro = _reenviar_email_pedido_enviado(token)
    if erro == "Esse pedido ainda não foi marcado como enviado.":
        abort(400, description=erro)
    return redirect(url_for("admin_pedido_detalhe", token=token))


@app.route("/admin/pedidos/<token>/reenviar-email-nota-fiscal", methods=["POST"])
def admin_pedido_reenviar_email_nota_fiscal(token: str):
    """Reenvia o e-mail "Nota fiscal disponível" na mao."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    if obter_pedido(token) is None:
        abort(404)
    erro = _reenviar_email_nota_fiscal(token)
    if erro == "Esse pedido ainda não tem link de nota fiscal preenchido.":
        abort(400, description=erro)
    return redirect(url_for("admin_pedido_detalhe", token=token))


@app.route("/admin/pedidos/acao-em-massa", methods=["POST"])
def admin_pedidos_acao_em_massa():
    """Aplica uma acao a varios pedidos selecionados de uma vez (ver
    conversa) -- reaproveita as MESMAS funcoes dos botoes individuais
    pra nunca duplicar logica. Sempre volta pro painel com a mesma
    lista de status filtrada (?status=...), pra nao perder o contexto
    de onde a selecao foi feita."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    tokens = request.form.getlist("tokens")
    acao = str(request.form.get("acao", "")).strip()
    status_filtro = str(request.form.get("status_filtro", "")).strip() or None
    tiny_erro = None

    if tokens and acao == "tiny":
        # Erros ficam so pra mostrar como alerta pontual na volta (ver
        # template admin_pedidos.html) -- nunca escritos na tabela, so o
        # numero do pedido fica ali (ver conversa). Sem duplicar mensagem
        # repetida quando varios pedidos selecionados dao o MESMO erro.
        erros_encontrados = []
        for token in tokens:
            erro = _sincronizar_pedido_tiny(token)
            if erro and erro not in erros_encontrados:
                erros_encontrados.append(erro)
        if erros_encontrados:
            tiny_erro = "; ".join(erros_encontrados)
    elif tokens and acao == "email":
        for token in tokens:
            _reenviar_email_confirmacao(token)
    elif tokens and acao == "status":
        novo_status = str(request.form.get("novo_status", "")).strip()
        for token in tokens:
            atualizar_status(token, novo_status)
    elif tokens and acao == "excluir":
        motivo = str(request.form.get("motivo", "")).strip()
        if motivo:
            for token in tokens:
                pedido_excluido = excluir_pedido(token, motivo=motivo)
                if pedido_excluido:
                    enviar_pedido_excluido(pedido_excluido, motivo, url_for("catalogo_completo", _external=True))
    elif tokens and acao == "arquivar":
        for token in tokens:
            arquivar_pedido(token)
    elif tokens and acao == "desarquivar":
        for token in tokens:
            desarquivar_pedido(token)

    arquivados = request.form.get("arquivados") == "1"
    if status_filtro or arquivados:
        return redirect(
            url_for(
                "admin_pedidos",
                status=status_filtro,
                arquivados="1" if arquivados else None,
                tiny_erro=tiny_erro,
            )
        )
    return redirect(url_for("admin_pedidos", tiny_erro=tiny_erro))


@app.route("/api/pix/gerar", methods=["POST"])
@limiter.limit("15 per minute")
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
        "do pagamento (prazo que cresce com a quantidade total do pedido -- 500+ "
        "peças: 7 dias úteis; 1000+: 8 dias úteis; 2000+: 10 dias úteis), mais o "
        "prazo de transporte.",
    ),
]


_FORMATOS_PERSONALIZADA_VALIDOS = {
    "medalha", "entremeio", "chaveiro", "medalha_2lados", "entremeio_2lados", "chaveiro_2lados",
}


def _combo_2lados_para_js(combo_id: str) -> dict | None:
    """Resolve um combo de config.py:COMBOS_2LADOS_PRONTOS pro formato que
    static/js/personalizada.js:tentarAutoPreencherCombo espera -- inclui
    produto_nome/modelo_nome ja resolvidos aqui (o JS so precisa buscar a
    URL da imagem por /api/produto/<id>/modelos, nao o nome). Combo com id
    desconhecido, ou lado apontando pra produto/modelo que nao existe mais
    no catalogo, retorna None (personalizada abre normal, sem pre-preencher)."""
    combo = next((c for c in COMBOS_2LADOS_PRONTOS if c["id"] == combo_id), None)
    if combo is None:
        return None
    lados = {}
    for chave in ("lado1", "lado2"):
        produto = buscar_produto(combo[chave]["produto_id"])
        modelo = next((m for m in produto["modelos"] if m["id"] == combo[chave]["modelo_id"]), None) if produto else None
        if produto is None or modelo is None:
            return None
        lados[chave] = {
            "produto_id": produto["id"],
            "produto_nome": produto["nome"],
            "modelo_id": modelo["id"],
            "modelo_nome": modelo["nome"],
        }
    return lados


def _avaliacoes_por_formato_personalizada() -> dict[str, dict]:
    """Media/total/lista de avaliacoes aprovadas de cada formato de
    personalizada (config.py:PRODUTOS_PERSONALIZADOS) -- cada formato
    tem seu proprio produto_id (ver conversa), entao a secao de
    avaliacoes em /personalizada precisa mostrar um conjunto diferente
    quando o formato e´ trocado (ver static/js/personalizada.js, que
    alterna qual bloco fica visivel pelo `data-formato`)."""
    resultado = {}
    for p in PRODUTOS_PERSONALIZADOS:
        media, total = media_e_total_aprovadas(p["id"])
        resultado[p["formato"]] = {
            "produto_id": p["id"],
            "nome": p["nome"],
            "media": media,
            "total": total,
            "avaliacoes": listar_avaliacoes_aprovadas(p["id"]) if total else [],
        }
    return resultado


@app.route("/personalizada", methods=["GET"])
def personalizada():
    """`?formato=` (opcional) vem dos cards "produto" da personalizada no
    catalogo/busca (ver _itens_personalizados_do_grid) -- pre-seleciona o
    formato certo em vez de sempre abrir em "Medalha". `?combo=` (opcional,
    ver _itens_combos_do_grid/COMBOS_2LADOS_PRONTOS) pre-preenche os 2
    lados de uma dupla ja pronta -- forca formato_inicial pra
    medalha_2lados quando um combo valido vem sem `?formato=` explicito."""
    combo_id = request.args.get("combo", "")
    combo_2lados = _combo_2lados_para_js(combo_id) if combo_id else None

    formato_inicial = request.args.get("formato", "")
    if formato_inicial not in _FORMATOS_PERSONALIZADA_VALIDOS:
        formato_inicial = "medalha_2lados" if combo_2lados else "medalha"
    dados_breadcrumb = _dados_breadcrumb(
        [
            ("Catálogo", url_for("index", _external=True)),
            ("Medalha personalizada", url_for("personalizada", _external=True)),
        ]
    )
    return render_template(
        "personalizada.html",
        formato_inicial=formato_inicial,
        combo_2lados=combo_2lados,
        preco_varejo=preco_varejo(),
        preco_varejo_chaveiro=preco_varejo("chaveiro"),
        preco_varejo_2lados=preco_varejo("medalha_2lados"),
        dados_faq=_dados_faq(_FAQ_PERSONALIZADA),
        dados_breadcrumb=dados_breadcrumb,
        avaliacoes_por_formato=_avaliacoes_por_formato_personalizada(),
        produto_id_por_formato={p["formato"]: p["id"] for p in PRODUTOS_PERSONALIZADOS},
    )


@app.route("/api/produto/<produto_id>/modelos", methods=["GET"])
def api_produto_modelos(produto_id: str):
    """Modelos de um produto do catalogo, com a URL de cada imagem por
    formato (mesmo formato de dados ja usado em templates/produto.html:
    modelos-grid data-imagens) -- usado pelo "escolher um santo do
    catálogo" dentro do assistente de 2 lados (ver static/js/
    personalizada.js), pra deixar o cliente escolher o modelo especifico
    depois de achar o santo pela busca. "medalha_2lados_*" so existe nos
    modelos que ja foram regenerados no gabarito novo (ver conversa
    2026-09-02) -- .get() retorna None nos que ainda nao tem, e o
    personalizada.js esconde da lista quem vier sem essas 2 chaves."""
    produto = buscar_produto(produto_id)
    if produto is None:
        abort(404)

    def _url_opcional(modelo: dict, chave: str) -> str | None:
        caminho = modelo.get(chave)
        return url_for("static", filename=caminho) if caminho else None

    return jsonify(
        [
            {
                "id": modelo["id"],
                "nome": modelo["nome"],
                "imagens": {
                    "medalha": url_for("static", filename=modelo["imagem"]),
                    "entremeio_prata": url_for("static", filename=modelo["imagem_entremeio_prata"]),
                    "entremeio_ouro_velho": url_for("static", filename=modelo["imagem_entremeio_ouro_velho"]),
                    "chaveiro": url_for("static", filename=modelo["imagem_chaveiro"]),
                    "medalha_2lados_prata": _url_opcional(modelo, "imagem_medalha_2lados_prata"),
                    "medalha_2lados_ouro_velho": _url_opcional(modelo, "imagem_medalha_2lados_ouro_velho"),
                    "chaveiro_2lados": _url_opcional(modelo, "imagem_chaveiro_2lados"),
                },
            }
            for modelo in produto["modelos"]
        ]
    )


@app.route("/imagem-personalizada/<token>")
def servir_imagem_personalizada(token: str):
    """Serve a previa/recorte de uma medalha personalizada guardados de
    forma DURAVEL (ver services/imagens_personalizadas.py) -- o carrinho
    (localStorage) guarda so essa URL, precisa continuar funcionando
    toda vez que o item aparece na tela (carrinho, pagina do pedido,
    painel admin, botoes "baixar" da propria pagina /personalizada),
    inclusive dias depois. Token e´ imprevisivel (secrets.token_urlsafe),
    entao nao precisa de autenticacao -- mesmo criterio ja usado no
    token de acompanhamento do pedido.

    Antes disso existia um SEGUNDO mecanismo (`/download/<token>`) so
    pros botoes de download, guardado em memoria do processo (dict
    global) -- unificado aqui pra parar de duplicar toda previa/recorte
    gerado em RAM (ver conversa: contribuiu pro servico estourar o
    limite de memoria do Render num pico de acessos). `?baixar=1` forca
    o download (Content-Disposition + application/octet-stream, mesmo
    criterio de antes -- Safari do iOS as vezes so EXIBE a imagem em vez
    de salvar quando o Content-Type e´ image/*)."""
    entrada = obter_imagem(token)
    if entrada is None:
        abort(404)
    dados, mimetype, nome_arquivo = entrada
    if request.args.get("baixar"):
        resposta = send_file(
            io.BytesIO(dados), mimetype="application/octet-stream",
            as_attachment=True, download_name=nome_arquivo,
        )
    else:
        resposta = send_file(io.BytesIO(dados), mimetype=mimetype)
        resposta.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resposta


@app.route("/api/avaliacoes", methods=["POST"])
@limiter.limit("5 per minute")
def api_avaliacoes_criar():
    """Envio de avaliacao pelo cliente direto na pagina de produto (ver
    templates/produto.html + static/js/avaliacoes.js) ou de /avaliar
    (santo do catalogo OU peca personalizada, ver _produto_para_avaliar
    -- config.py:PRODUTOS_PERSONALIZADOS) -- nasce "pendente", so
    aparece pro publico depois de aprovada no painel admin (ver
    services/avaliacoes.py e /admin/avaliacoes abaixo)."""
    produto_id = str(request.form.get("produto_id", "")).strip()
    if _produto_para_avaliar(produto_id) is None:
        return jsonify(erro="Produto não encontrado."), 404

    nome_cliente = str(request.form.get("nome_cliente", "")).strip()
    if not nome_cliente:
        return jsonify(erro="Informe seu nome."), 400

    try:
        nota = int(request.form.get("nota", ""))
    except (TypeError, ValueError):
        return jsonify(erro="Escolha uma nota de 1 a 5."), 400
    if nota < 1 or nota > 5:
        return jsonify(erro="Escolha uma nota de 1 a 5."), 400

    formato = str(request.form.get("formato", "")).strip()
    if formato not in ("medalha", "entremeio", "chaveiro"):
        formato = ""

    texto = str(request.form.get("texto", "")).strip()[:1000]

    arquivo = request.files.get("foto")
    foto_data_uri = ""
    if arquivo and arquivo.filename:
        if not _extensao_valida(arquivo.filename):
            return jsonify(erro="Formato de imagem inválido. Aceitos: " + ", ".join(IMAGE_EXTENSIONS)), 400
        try:
            foto_data_uri = _foto_avaliacao_para_data_uri(arquivo)
        except Exception:
            return jsonify(erro="Não foi possível processar a foto enviada."), 400

    criar_avaliacao(
        produto_id=produto_id,
        formato=formato,
        nome_cliente=nome_cliente[:120],
        nota=nota,
        texto=texto,
        foto=foto_data_uri,
    )
    return jsonify(ok=True)


def _percentual(numerador: float | None, denominador: float | None) -> float | None:
    """Arredonda numerador/denominador em % -- None quando nao da pra
    calcular (denominador zero/vazio ou algum dos dois faltando), pra
    o template mostrar "—" em vez de um erro ou um 0% enganoso."""
    if not numerador and numerador != 0:
        return None
    if not denominador:
        return None
    return round(100 * numerador / denominador, 1)


_JANELAS_PERIODO_VENDAS = {"30d": 30, "6m": 182, "1a": 365}


def _intervalo_periodo_vendas(periodo: str, inicio_str: str, fim_str: str) -> tuple[datetime | None, datetime | None]:
    """Traduz o seletor de periodo do painel de vendas (ver templates/
    admin_analytics.html) em (desde, ate) pra produtos_mais_vendidos/
    quantidade_por_material -- "total" e´ (None, None) (sem limite em
    nenhuma ponta), "personalizado" usa as datas escolhidas (invalida ou
    faltando cai no padrao de 30 dias), as demais janelas sao fixas a
    partir de agora, sem limite superior (mesmo criterio ja usado nos
    outros cartoes de "vendas" desta pagina)."""
    if periodo == "total":
        return None, None
    if periodo == "personalizado":
        try:
            inicio = datetime.fromisoformat(inicio_str).replace(tzinfo=timezone.utc)
            # fim do dia escolhido -- senao "ate 10/06" nao inclui as
            # vendas do proprio dia 10/06 (qualquer hora depois de 00:00)
            fim = datetime.fromisoformat(fim_str).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            return inicio, fim
        except (TypeError, ValueError):
            pass  # datas invalidas/faltando -- cai no padrao de 30 dias abaixo
    dias = _JANELAS_PERIODO_VENDAS.get(periodo, 30)
    return datetime.now(timezone.utc) - timedelta(days=dias), None


@app.route("/admin/analytics", methods=["GET"])
def admin_analytics():
    """Dashboard de leitura do GA4 + do proprio banco de pedidos dentro
    do painel (ver services/analytics.py) -- visitas/pessoas/paginas
    mais vistas/quantas simularam frete/funil de conversao, sem
    precisar abrir o Google Analytics. O funil e as proporcoes usam a
    janela de 7 dias (mesma ja em destaque no resto da pagina) --
    cruza visita (GA4) com pedido de verdade (banco proprio, ver
    conversa)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de analytics"'}
        )

    # Estatisticas de VENDAS, direto do banco proprio de pedidos -- nao
    # dependem do GA4, entao sempre aparecem (mesmo sem GA4 configurado,
    # ver abaixo). Ver conversa: usuaria mandou print do dashboard da
    # Yampi como referencia (grafico de vendas por dia, pedidos por
    # estado, taxa de cancelamento, formas de pagamento, produtos mais
    # vendidos, clientes recorrentes) -- so entrou aqui o que da pra
    # calcular com dado real do proprio site (sem cupom/order bump, essas
    # duas features do print da Yampi simplesmente nao existem aqui).
    #
    # "Produtos mais vendidos" e "quantidade por material" tem janela
    # PROPRIA e selecionavel (pedido do usuario: 30 dias, 6 meses, 1
    # ano, total ou periodo personalizado) -- os outros cartoes de
    # vendas continuam fixos em 30 dias.
    periodo_vendas = request.args.get("periodo", "30d")
    inicio_vendas_str = request.args.get("inicio", "")
    fim_vendas_str = request.args.get("fim", "")
    desde_vendas, ate_vendas = _intervalo_periodo_vendas(periodo_vendas, inicio_vendas_str, fim_vendas_str)
    contexto_vendas = dict(
        vendas_30d=resumo_vendas_periodo(30),
        vendas_por_dia_30d=vendas_por_dia(30),
        pedidos_por_uf_30d=pedidos_por_uf(30),
        cancelamento_30d=taxa_cancelamento(30),
        formas_pagamento_30d=formas_pagamento_periodo(30),
        produtos_mais_vendidos=produtos_mais_vendidos(desde=desde_vendas, ate=ate_vendas),
        quantidade_por_material=quantidade_por_material(desde=desde_vendas, ate=ate_vendas),
        recorrencia_30d=taxa_clientes_recorrentes(30),
        periodo_vendas=periodo_vendas,
        inicio_vendas=inicio_vendas_str,
        fim_vendas=fim_vendas_str,
    )

    if not analytics.configurado():
        return render_template("admin_analytics.html", configurado=False, **contexto_vendas)

    resumo_7d = analytics.resumo_ultimos_dias(7)
    fretes_simulados_7d = analytics.contagem_evento("calculate_shipping", 7)
    pedidos_iniciados_7d = contagem_pedidos_por_status(7, ("pendente", "pago"))
    pedidos_pagos_7d = contagem_pedidos_por_status(7, ("pago",))
    vendas_7d = resumo_vendas_periodo(7)
    visitas_7d = resumo_7d["visitas"] if resumo_7d else None

    return render_template(
        "admin_analytics.html",
        configurado=True,
        **contexto_vendas,
        ao_vivo=analytics.usuarios_ativos_agora(),
        resumo_hoje=analytics.resumo_ultimos_dias(0),
        # "hoje" (acima) usa o relatorio PADRAO do GA4, que so fecha os
        # dados do dia atual no dia SEGUINTE -- na pratica fica em 0 (ou
        # quase) o dia inteiro, todo dia, e isso confunde quem olha o
        # painel achando que esta quebrado (ver conversa 2026-09-02:
        # "teve duas vendas hj" mas o cartao mostrava 0). "ontem" e´ o
        # numero mais recente CONFIAVEL desse mesmo relatorio -- ver
        # services/analytics.py:resumo_ontem.
        resumo_ontem=analytics.resumo_ontem(),
        resumo_7d=resumo_7d,
        resumo_30d=analytics.resumo_ultimos_dias(30),
        paginas_7d=analytics.paginas_mais_vistas(7, limite=8),
        fretes_simulados_hoje=analytics.contagem_evento("calculate_shipping", 0),
        fretes_simulados_ontem=analytics.contagem_evento_ontem("calculate_shipping"),
        fretes_simulados_7d=fretes_simulados_7d,
        fretes_simulados_30d=analytics.contagem_evento("calculate_shipping", 30),
        fretes_simulados_agora=analytics.contagem_evento_tempo_real("calculate_shipping"),
        pedidos_iniciados_7d=pedidos_iniciados_7d,
        pedidos_pagos_7d=pedidos_pagos_7d,
        vendas_7d=vendas_7d,
        funil_7d=[
            {"rotulo": "Visitas", "valor": visitas_7d, "pct": 100.0 if visitas_7d else None},
            {"rotulo": "Simularam frete", "valor": fretes_simulados_7d, "pct": _percentual(fretes_simulados_7d, visitas_7d)},
            {"rotulo": "Iniciaram pedido", "valor": pedidos_iniciados_7d, "pct": _percentual(pedidos_iniciados_7d, visitas_7d)},
            {"rotulo": "Compraram", "valor": pedidos_pagos_7d, "pct": _percentual(pedidos_pagos_7d, visitas_7d)},
        ],
        proporcao_simulacao_visita=_percentual(fretes_simulados_7d, visitas_7d),
        proporcao_pedido_visita=_percentual(pedidos_iniciados_7d, visitas_7d),
        proporcao_venda_visita=_percentual(pedidos_pagos_7d, visitas_7d),
        proporcao_venda_simulacao=_percentual(pedidos_pagos_7d, fretes_simulados_7d),
    )


@app.route("/admin/avaliacoes", methods=["GET"])
def admin_avaliacoes():
    """Fila de moderacao -- toda avaliacao enviada pelo site nasce
    pendente, so aparece pro publico depois de passar por aqui (ver
    services/avaliacoes.py)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de avaliações"'}
        )
    status_filtro = request.args.get("status") or None
    avaliacoes = listar_avaliacoes(status=status_filtro)
    return render_template("admin_avaliacoes.html", avaliacoes=avaliacoes, status_filtro=status_filtro)


@app.route("/admin/avaliacoes/<int:id_>/aprovar", methods=["POST"])
def admin_avaliacao_aprovar(id_: int):
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de avaliações"'}
        )
    atualizar_status_avaliacao(id_, "aprovada")
    return redirect(url_for("admin_avaliacoes"))


@app.route("/admin/avaliacoes/<int:id_>/recusar", methods=["POST"])
def admin_avaliacao_recusar(id_: int):
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de avaliações"'}
        )
    atualizar_status_avaliacao(id_, "recusada")
    return redirect(url_for("admin_avaliacoes"))


@app.route("/sw.js", methods=["GET"])
def service_worker():
    """Service worker so pra notificacao push (ver static/js/push.js e
    services/push.py) -- servido na raiz (nao em /static/) de proposito,
    pro escopo dele cobrir o site inteiro, nao so /static/."""
    return send_file(Path(app.root_path) / "static" / "sw.js", mimetype="application/javascript")


@app.route("/admin/push/inscrever", methods=["POST"])
def admin_push_inscrever():
    """Recebe a subscription do navegador (PushManager.subscribe(), ver
    static/js/push.js) depois que o admin ativa notificacoes -- guarda
    pra usar em services.push.enviar_notificacao quando uma venda for
    confirmada (ver webhook_infinitepay)."""
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    dados = request.get_json(silent=True) or {}
    endpoint = str(dados.get("endpoint", "")).strip()
    chaves = dados.get("keys") or {}
    p256dh = str(chaves.get("p256dh", "")).strip()
    auth = str(chaves.get("auth", "")).strip()
    if not endpoint or not p256dh or not auth:
        return jsonify(erro="Inscrição inválida."), 400
    salvar_push_subscription(endpoint=endpoint, p256dh=p256dh, auth=auth)
    return jsonify(ok=True)


@app.route("/admin/push/desinscrever", methods=["POST"])
def admin_push_desinscrever():
    if not _autenticacao_admin_valida(request.authorization):
        return Response(
            "Autenticação necessária.", 401, {"WWW-Authenticate": 'Basic realm="Painel de pedidos"'}
        )
    dados = request.get_json(silent=True) or {}
    endpoint = str(dados.get("endpoint", "")).strip()
    if endpoint:
        remover_push_subscription(endpoint)
    return jsonify(ok=True)


@app.route("/api/personalizada/preview", methods=["POST"])
@limiter.limit("15 per minute")
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
    if not _LIMITE_PROCESSAMENTO_IMAGEM_PESADO.acquire(timeout=_TIMEOUT_ESPERA_PROCESSAMENTO_SEGUNDOS):
        return jsonify(erro="Muita gente enviando foto agora, tenta de novo em alguns segundos."), 503
    try:
        with _salvar_temp(arquivo) as tmp:
            caminho = Path(tmp.name)
            try:
                box = _reduzir_temp_se_grande_demais(caminho, box)
                resultado = compose_medal(spec, caminho, crop_box=box)
                recorte = _crop_quadrada(caminho, box)
            except Exception as exc:
                return jsonify(erro=f"Erro ao gerar a simulação: {exc}"), 400
    finally:
        _LIMITE_PROCESSAMENTO_IMAGEM_PESADO.release()

    nome_base = _sem_extensao(arquivo.filename)
    imagem_bytes = _imagem_para_bytes(resultado)
    recorte_bytes = _imagem_para_bytes(recorte)

    # Guardado de forma DURAVEL (ver services/imagens_personalizadas.py,
    # SQLite -- nao em memoria do processo) -- o que vai pro item do
    # carrinho/pedido E pros botoes "baixar previa/recorte" desta
    # pagina, um unico mecanismo pras duas coisas (antes disso existia
    # um dict global em RAM so pro download, guardando previa+recorte
    # de CADA simulacao gerada -- contribuiu pro servico estourar o
    # limite de memoria do Render num pico de acessos, ver conversa).
    chave_imagem = salvar_imagem(imagem_bytes, "image/png", f"{nome_base}_{spec_id}.png", tipo="preview")
    chave_recorte = salvar_imagem(recorte_bytes, "image/png", f"{nome_base}_recorte.png", tipo="recorte")

    return jsonify(
        preview=url_for("servir_imagem_personalizada", token=chave_imagem),
        crop=url_for("servir_imagem_personalizada", token=chave_recorte),
        url_preview=url_for("servir_imagem_personalizada", token=chave_imagem, baixar=1),
        url_crop=url_for("servir_imagem_personalizada", token=chave_recorte, baixar=1),
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


# Rotulo por grupo de atacado (ver services/pricing.py) -- mesmo texto
# usado no nudge de desconto do carrinho (GRUPO_LABEL em
# static/js/carrinho_pagina.js), so que reaproveitado aqui pro
# empurrao pos-compra (pagina de obrigado + e-mail de oportunidade).
_GRUPO_LABEL = {"padrao": "medalhas/entremeios", "chaveiro": "chaveiros"}


def _oportunidades_upsell_do_pedido(pedido: dict) -> list[dict]:
    """Pra cada grupo de atacado com item nesse pedido, calcula quanto
    falta pro PROXIMO pedido cair numa faixa de desconto melhor --
    mesma logica de services.pricing.calcular_carrinho ja usada no
    nudge do carrinho, so que aplicada a um pedido ja fechado, como
    sugestao pra proxima compra (nunca muda o pedido em si). Devolve
    lista vazia se o pedido ja estava na melhor faixa em todos os
    grupos que comprou (nesse caso nao ha´ oportunidade real pra
    oferecer)."""
    resultado = calcular_carrinho(pedido["itens"])
    oportunidades = []
    for nome_grupo, grupo in resultado["grupos"].items():
        if grupo["quantidade_total"] == 0 or not grupo["proxima_faixa"]:
            continue
        oportunidades.append(
            {
                "label": _GRUPO_LABEL.get(nome_grupo, nome_grupo),
                "faltam": grupo["proxima_faixa"]["faltam"],
                "preco": grupo["proxima_faixa"]["preco"],
                "economia": grupo["proxima_faixa"]["economia"],
            }
        )
    return oportunidades


def _enviar_upsell_pedidos_pagos() -> None:
    """Job agendado (ver _iniciar_scheduler_jobs abaixo) -- roda a cada
    10min, manda o e-mail de oportunidade (empurrao pra proxima faixa
    de desconto no PROXIMO pedido) UPSELL_HORAS_APOS_PAGAMENTO horas
    depois do pagamento confirmado. So manda quando ha´ oportunidade
    real (ver _oportunidades_upsell_do_pedido) -- senao so marca como
    processado, sem mandar e-mail vazio."""
    if not CANONICAL_DOMAIN:
        return
    candidatos = listar_pedidos_pagos_para_upsell(UPSELL_HORAS_APOS_PAGAMENTO)
    if not candidatos:
        return
    with app.test_request_context(base_url=f"https://{CANONICAL_DOMAIN}"):
        url_catalogo = url_for("catalogo_completo", _external=True)
        for pedido in candidatos:
            oportunidades = _oportunidades_upsell_do_pedido(pedido)
            if not oportunidades:
                marcar_email_upsell_enviado(pedido["token"], erro=None)
                continue
            resultado_email = enviar_oportunidade_upsell(pedido, oportunidades, url_catalogo)
            marcar_email_upsell_enviado(pedido["token"], erro=resultado_email.get("erro"))


def _enviar_email_avaliacao(token: str) -> str | None:
    """Manda o e-mail pedindo avaliacao (ver services/email.py:
    enviar_pedido_avaliacao, ja convida a seguir/marcar @novedjulho no
    Instagram tambem), linkando pra pagina GERAL de avaliacao (/avaliar
    -- o cliente escolhe o produto na hora, ver conversa) -- chamado NA
    HORA que o pedido vira "entregue" (ver admin_pedido_status abaixo),
    sem prazo de espera (pedido do usuario: faz mais sentido pedir
    depois que o cliente RECEBEU a peca do que so depois que pagou).
    Devolve None se deu certo, ou uma mensagem de erro."""
    pedido = obter_pedido(token)
    if pedido is None:
        return "Pedido não encontrado."
    try:
        url_avaliar = url_for("avaliar_geral", _external=True)
        resultado_email = enviar_pedido_avaliacao(pedido, url_avaliar)
    except Exception as exc:  # nunca deixa a mudanca de status numa tela de erro generica
        resultado_email = {"erro": f"Erro inesperado ao enviar: {exc}"}
    marcar_email_avaliacao_enviado(token, erro=resultado_email.get("erro"))
    return resultado_email.get("erro")


def _enviar_seguimento_avaliacao_entregues() -> None:
    """Job agendado (ver _iniciar_scheduler_jobs abaixo) -- roda a cada
    10min, manda de novo o MESMO e-mail de avaliacao (ver
    _enviar_email_avaliacao acima) AVALIACAO_SEGUIMENTO_DIAS_APOS_ENTREGA
    dias depois da ENTREGA, pra quem ainda nao avaliou -- reforco unico
    (ver conversa: so esses 2 e-mails de avaliacao no total por pedido,
    o imediato e esse)."""
    if not CANONICAL_DOMAIN:
        return
    candidatos = listar_pedidos_entregues_para_seguimento_avaliacao(AVALIACAO_SEGUIMENTO_DIAS_APOS_ENTREGA)
    if not candidatos:
        return
    with app.test_request_context(base_url=f"https://{CANONICAL_DOMAIN}"):
        url_avaliar = url_for("avaliar_geral", _external=True)
        for pedido in candidatos:
            resultado_email = enviar_pedido_avaliacao(pedido, url_avaliar)
            marcar_email_avaliacao_seguimento_enviado(pedido["token"], erro=resultado_email.get("erro"))


def _enviar_emails_recompra_entregues() -> None:
    """Job agendado (ver _iniciar_scheduler_jobs abaixo) -- convite de
    recompra 30/60/90 dias depois da ENTREGA (ver conversa), 3 estagios
    INDEPENDENTES entre si (ESTAGIOS_RECOMPRA_DIAS, ver
    services/pedidos.py) -- quem nao abriu o de 30 dias ainda recebe o
    de 60. Quando o pedido tem pelo menos 1 item "repetivel" (santo do
    catalogo, ver _itens_repetiveis_do_pedido), o botao do e-mail leva
    direto pro carrinho ja´ preenchido (?repetir=1 em /pedido/<token>,
    ver templates/pedido.html); pedido so´ de peca personalizada leva
    pro catalogo geral em vez disso."""
    if not CANONICAL_DOMAIN:
        return
    with app.test_request_context(base_url=f"https://{CANONICAL_DOMAIN}"):
        url_catalogo = url_for("catalogo_completo", _external=True)
        for dias in ESTAGIOS_RECOMPRA_DIAS:
            for pedido in listar_pedidos_entregues_para_recompra(dias):
                tem_repetir = bool(_itens_repetiveis_do_pedido(pedido))
                url = (
                    url_for("ver_pedido", token=pedido["token"], repetir="1", _external=True)
                    if tem_repetir
                    else url_catalogo
                )
                resultado_email = enviar_pedido_recompra(pedido, dias, url, tem_repetir=tem_repetir)
                marcar_email_recompra_enviado(pedido["token"], dias, erro=resultado_email.get("erro"))


def _cancelar_pedidos_abandonados() -> None:
    """Job agendado (ver _iniciar_scheduler_jobs abaixo) -- roda a cada
    10min, cancela pedido "pendente" que continua sem pagar
    CANCELAMENTO_MINUTOS_APOS_LEMBRETE minutos depois do 2o link
    (lembrete) ter sido enviado, e manda um e-mail motivacional de
    recuperacao linkando de volta pro catalogo. Sem CANONICAL_DOMAIN
    configurado nao ha´ como montar um link de verdade pro e-mail,
    entao so nao faz nada nesse caso (mesmo criterio do lembrete)."""
    if not CANONICAL_DOMAIN:
        return
    candidatos = listar_pedidos_pendentes_para_cancelar(CANCELAMENTO_MINUTOS_APOS_LEMBRETE)
    if not candidatos:
        return
    with app.test_request_context(base_url=f"https://{CANONICAL_DOMAIN}"):
        for pedido in candidatos:
            cancelar_pedido(pedido["token"])
            resultado_email = enviar_pedido_cancelado(
                pedido,
                url_for("pedido_reativar_pix", token=pedido["token"], _external=True),
                url_for("pedido_reativar_boleto", token=pedido["token"], _external=True),
            )
            marcar_email_cancelado_enviado(pedido["token"], erro=resultado_email.get("erro"))


# Situacoes de cobranca confirmadas no PDF da API do Inter ("Recuperar
# cobranca") -- RECEBIDO/MARCADO_RECEBIDO contam como pago de verdade
# (a segunda e´ quando o proprio banco/lojista marca manualmente, ex:
# pagamento por outro meio); CANCELADO/EXPIRADO encerram sem pagar.
# A_RECEBER/ATRASADO/EM_PROCESSAMENTO/FALHA_EMISSAO/PROTESTO ainda nao
# tem desfecho -- so espera o proximo ciclo do job.
_SITUACOES_INTER_PAGO = ("RECEBIDO", "MARCADO_RECEBIDO")
_SITUACOES_INTER_ENCERRADO_SEM_PAGAR = ("CANCELADO", "EXPIRADO")


def _verificar_boletos_inter_pendentes() -> None:
    """Job agendado (ver _iniciar_scheduler_jobs abaixo) -- roda a cada
    10min, consulta o status de cada boleto Inter ainda "pendente"
    (polling, ver services/inter.py pro motivo de nao usar webhook) e
    confirma o pagamento ou cancela o pedido de acordo com a situacao
    real na Inter. Sem CANONICAL_DOMAIN configurado nao ha´ como montar
    um link de verdade pros e-mails disparados daqui, entao so nao faz
    nada nesse caso (mesmo criterio dos outros jobs)."""
    if not CANONICAL_DOMAIN:
        return
    candidatos = listar_pedidos_boleto_pendentes()
    if not candidatos:
        return
    with app.test_request_context(base_url=f"https://{CANONICAL_DOMAIN}"):
        for pedido in candidatos:
            dados = consultar_cobranca(pedido["inter_codigo_solicitacao"])
            if "erro" in dados:
                marcar_boleto_erro(pedido["token"], dados["erro"])
                continue

            situacao = (dados.get("cobranca") or {}).get("situacao", "")
            if situacao in _SITUACOES_INTER_PAGO:
                valor_recebido = (dados.get("cobranca") or {}).get("valorTotalRecebido") or pedido["total"]
                pedido_pago = marcar_pago(
                    pedido["token"],
                    forma_pagamento="boleto",
                    parcelas=None,
                    valor_pago=float(valor_recebido),
                    transaction_nsu=pedido["inter_codigo_solicitacao"],
                )
                _pos_pagamento_confirmado(pedido_pago, pedido["token"])
            elif situacao in _SITUACOES_INTER_ENCERRADO_SEM_PAGAR:
                cancelar_pedido(pedido["token"])
                resultado_email = enviar_pedido_cancelado(
                    pedido,
                    url_for("pedido_reativar_pix", token=pedido["token"], _external=True),
                    url_for("pedido_reativar_boleto", token=pedido["token"], _external=True),
                )
                marcar_email_cancelado_enviado(pedido["token"], erro=resultado_email.get("erro"))


def _limpar_imagens_personalizadas_antigas() -> None:
    """Job agendado (ver _iniciar_scheduler_jobs abaixo) -- roda 1x por
    dia, apaga simulacoes de medalha personalizada geradas (ver
    api_personalizada_preview) mas nunca adicionadas a um pedido de
    verdade, depois de 7 dias (ver
    services/imagens_personalizadas.py:purgar_imagens_antigas). Evita o
    banco crescer sem limite com foto de quem so testou a simulacao."""
    purgar_imagens_antigas(dias=7)


def _limpar_imagens_pedidos_cancelados() -> None:
    """Job agendado (ver _iniciar_scheduler_jobs abaixo) -- roda de hora
    em hora (nao 1x por dia como as outras limpezas, ver comentario em
    config.py:RETENCAO_IMAGENS_PEDIDO_CANCELADO_DIAS), apaga as imagens
    personalizadas (previa + recorte) de pedidos CANCELADOS ha´ mais de
    RETENCAO_IMAGENS_PEDIDO_CANCELADO_DIAS (config.py) que ninguem
    reativou (ver services/pedidos.py:reativar_pedido_cancelado, usado
    pelo e-mail de recuperacao) -- depois desse prazo a chance de
    recuperacao e´ baixa e a imagem so ocupa espaco a toa (ver
    conversa)."""
    for pedido in listar_pedidos_cancelados_para_limpar_imagens(RETENCAO_IMAGENS_PEDIDO_CANCELADO_DIAS):
        tokens = _tokens_imagens_personalizadas_do_pedido(pedido)
        if tokens:
            apagar_imagens(tokens)
        marcar_imagens_pedido_apagadas(pedido["token"])


def _iniciar_scheduler_jobs() -> None:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(_enviar_lembretes_pedidos_pendentes, "interval", minutes=10, id="lembretes_pedidos_pendentes")
    scheduler.add_job(_cancelar_pedidos_abandonados, "interval", minutes=10, id="cancelar_pedidos_abandonados")
    scheduler.add_job(_enviar_upsell_pedidos_pagos, "interval", minutes=10, id="upsell_pedidos_pagos")
    scheduler.add_job(
        _enviar_seguimento_avaliacao_entregues, "interval", minutes=10, id="seguimento_avaliacao_entregues"
    )
    scheduler.add_job(_enviar_emails_recompra_entregues, "interval", hours=1, id="emails_recompra_entregues")
    scheduler.add_job(_verificar_boletos_inter_pendentes, "interval", minutes=10, id="verificar_boletos_inter")
    scheduler.add_job(
        _limpar_imagens_personalizadas_antigas, "interval", hours=24, id="limpar_imagens_personalizadas"
    )
    scheduler.add_job(
        _limpar_imagens_pedidos_cancelados, "interval", hours=1, id="limpar_imagens_pedidos_cancelados"
    )
    # Codigos de /meus-pedidos vencem em 10 minutos (ver services/pedidos.py:
    # _CODIGO_VERIFICACAO_VALIDADE_MINUTOS) -- limpa a cada hora pra tabela
    # nunca acumular codigo vencido que ninguem verificou.
    scheduler.add_job(
        limpar_codigos_verificacao_expirados, "interval", hours=1, id="limpar_codigos_verificacao"
    )
    scheduler.start()


# So liga em producao de verdade (ENABLE_SCHEDULER=true no servidor) --
# nunca em teste/dev, senao sobe uma thread de fundo rodando de
# verdade a cada import do modulo (ver config.py).
#
# IMPORTANTE se um dia aumentar "--workers" no render.yaml (hoje fixo
# em 1 de proposito -- "--threads 8" com "--worker-class gthread", ver
# render.yaml, e´ SEGURO e nao conta pra essa restricao: sao varias
# threads dentro do MESMO processo, memoria compartilhada, entao nem o
# scheduler nem o limiter abaixo duplicam; foi ligado justamente pra
# imagem estatica parar de disputar o unico worker com pagina/API
# durante o carregamento da home, ver conversa "auditoria Claude in
# Chrome"): CADA worker (processo) do gunicorn importa esse modulo
# separado e subiria seu PROPRIO scheduler, duplicando (2x, 3x...)
# todo e-mail/job agendado daqui pra baixo. Rodar com `--preload`
# resolve ESSA parte (o modulo roda 1x so, no processo mestre, ANTES
# do fork -- thread de fundo nao sobrevive ao fork, entao so o mestre
# continua rodando os jobs), MAS o limiter.storage_uri="memory://" (ver
# inicio do arquivo) tambem depende de workers=1 (cada worker contaria
# limite de taxa separado, na pratica dobrando/triplicando o limite
# real) -- os DOIS precisam ser resolvidos juntos (preload + storage
# compartilhado tipo Redis pro limiter) antes de subir mais workers
# (processos) de verdade.
if ENABLE_SCHEDULER:
    _iniciar_scheduler_jobs()


if __name__ == "__main__":
    # so pra dev local (producao usa gunicorn, ver Procfile/render.yaml
    # -- esse bloco nunca roda la). debug=True por padrao pra manter o
    # fluxo de dev de sempre, mas de olho: nunca rodar `python3 app.py`
    # direto num ambiente exposto de verdade, o debugger do Werkzeug
    # permite executar codigo arbitrario.
    app.run(host="0.0.0.0", port=8000, debug=os.environ.get("FLASK_DEBUG", "1") != "0")
