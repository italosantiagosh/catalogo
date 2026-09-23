from __future__ import annotations

import re

import pytest
from markupsafe import escape

from app import app
from services.blog import ARTIGOS_BLOG, artigo_por_produto_id
from services.catalogo import buscar_produto, carregar_produtos


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_todos_os_artigos_tem_produto_relacionado_valido():
    """ver services/blog.py -- cada artigo precisa apontar pra um santo
    que realmente existe no catalogo, senao o CTA principal do artigo
    (e a pagina inteira, via _thumbnail_do_artigo) quebra. Artigo sem
    produto de catalogo (ex: a historia da propria loja) precisa ter
    cta_endpoint valido e imagem_manual no lugar."""
    for slug, artigo in ARTIGOS_BLOG.items():
        produto_id = artigo["produto_relacionado_id"]
        if produto_id is None:
            assert artigo.get("cta_endpoint") in app.view_functions, f"{slug}: cta_endpoint inválido"
            assert artigo.get("imagem_manual"), f"{slug}: falta imagem_manual"
            continue
        produto = buscar_produto(produto_id)
        assert produto is not None, f"{slug}: produto_relacionado_id inválido"


def test_indice_lista_todos_os_artigos(client):
    """`escape()` porque o Jinja escapa aspas simples (ex: "d'Ávila" vira
    "d&#39;Ávila" no HTML renderizado) -- comparar a string crua contra
    a pagina falha pra qualquer titulo com apostrofo, mesmo estando
    tudo certo (ver conversa 2026-09-24)."""
    resposta = client.get("/blog")
    assert resposta.status_code == 200
    pagina = resposta.get_data(as_text=True)
    for artigo in ARTIGOS_BLOG.values():
        assert str(escape(artigo["titulo"])) in pagina


def test_artigo_existe_renderiza_200(client):
    slug = next(iter(ARTIGOS_BLOG))
    resposta = client.get(f"/blog/{slug}")
    assert resposta.status_code == 200
    pagina = resposta.get_data(as_text=True)
    assert ARTIGOS_BLOG[slug]["titulo"] in pagina


def test_artigo_inexistente_404(client):
    resposta = client.get("/blog/nao-existe")
    assert resposta.status_code == 404


def test_artigo_linka_pro_produto_relacionado(client):
    slug, artigo = next(iter(ARTIGOS_BLOG.items()))
    resposta = client.get(f"/blog/{slug}")
    pagina = resposta.get_data(as_text=True)
    assert f"/produto/{artigo['produto_relacionado_id']}" in pagina
    assert "__URL_PRODUTO__" not in pagina  # placeholder sempre substituido


def test_artigo_tem_schema_blogposting(client):
    slug = next(iter(ARTIGOS_BLOG))
    resposta = client.get(f"/blog/{slug}")
    pagina = resposta.get_data(as_text=True)
    assert '"@type": "BlogPosting"' in pagina


def test_produto_com_artigo_mostra_link_pro_blog(client):
    slug, artigo = next(iter(ARTIGOS_BLOG.items()))
    resposta = client.get(f"/produto/{artigo['produto_relacionado_id']}")
    assert resposta.status_code == 200
    pagina = resposta.get_data(as_text=True)
    assert f"/blog/{slug}" in pagina


def test_produto_sem_artigo_nao_mostra_link_pro_blog(client):
    ids_com_artigo = {a["produto_relacionado_id"] for a in ARTIGOS_BLOG.values()}
    todos_ids = {p["id"] for p in carregar_produtos()}
    sem_artigo = next(iter(todos_ids - ids_com_artigo))
    resposta = client.get(f"/produto/{sem_artigo}")
    pagina = resposta.get_data(as_text=True)
    assert "link-blog-relacionado" not in pagina


def test_blog_aparece_no_sitemap(client):
    resposta = client.get("/sitemap.xml")
    corpo = resposta.get_data(as_text=True)
    assert "/blog</loc>" in corpo
    for slug in ARTIGOS_BLOG:
        assert f"/blog/{slug}</loc>" in corpo


def test_blog_aparece_no_rodape(client):
    resposta = client.get("/")
    assert "/blog" in resposta.get_data(as_text=True)


def test_artigo_por_produto_id_acha_o_slug_certo():
    slug, artigo = next(iter(ARTIGOS_BLOG.items()))
    encontrado = artigo_por_produto_id(artigo["produto_relacionado_id"])
    assert encontrado == (slug, artigo)


def test_artigo_por_produto_id_sem_artigo_devolve_none():
    assert artigo_por_produto_id("produto-sem-artigo-nenhum") is None


def test_links_internos_dos_artigos_apontam_pra_coisas_reais():
    """Artigos "misturados" citam varios produtos/outros artigos dentro
    do texto (ver conversa) com link cru (<a href="/produto/...">,
    "/blog/..."), sem passar por url_for -- essa checagem garante que
    nenhum desses links crus aponta pra um id/slug que nao existe.
    Ancorado em `href="` (nao so "/produto/"/"/blog/" soltos) pra nao
    confundir link INTERNO com um link EXTERNO que por coincidencia
    tem "/blog/" no proprio caminho (ex: as novenas citam
    https://.../blog/novena-..., um artigo de outro site, ver
    conversa 2026-09-24)."""
    ids_validos = {p["id"] for p in carregar_produtos()}
    slugs_validos = set(ARTIGOS_BLOG.keys())
    for slug, artigo in ARTIGOS_BLOG.items():
        corpo = artigo["corpo_html"]
        for pid in re.findall(r'href="/produto/([a-z0-9\-]+)"', corpo):
            assert pid in ids_validos, f"{slug}: link inline /produto/{pid} não existe"
        for slug_inline in re.findall(r'href="/blog/([a-z0-9\-]+)"', corpo):
            assert slug_inline in slugs_validos, f"{slug}: link inline /blog/{slug_inline} não existe"


def test_artigos_misturados_carregam_200_e_linkam_produtos_citados(client):
    """Ver conversa: artigos que citam mais de um santo/beato/produto no
    corpo (nao so o produto_relacionado_id principal)."""
    casos = {
        "jovens-santos-e-beatos": ["sao-pier-giorgio-frassati", "chiara-luce"],
        "santos-carmelitas-espiritualidade-do-carmelo": ["santa-teresa-davila", "sao-joao-da-cruz", "edith-stein"],
        "titulos-de-sao-jose": ["castissimo-coracao-de-sao-jose", "sao-jose-dormindo"],
        "santa-faustina-e-jesus-misericordioso": ["jesus-misericordioso"],
        "arcanjos-miguel-gabriel-rafael": ["sao-gabriel", "sao-rafael"],
        "familia-martin-pais-de-santa-teresinha": [],
        "santos-martires-de-cunhau-e-uruacu": [],
        "beata-nha-chica-baependi": [],
        "padre-cicero-e-frei-damiao-devocao-nordestina": ["frei-damiao"],
        "francisco-e-jacinta-pastorinhos-de-fatima": [],
        "espirito-santo-pentecostes-santissima-trindade": ["pentecostes", "santissima-trindade"],
        "nossa-senhora-titulos-e-aparicoes": [
            "nossa-senhora-de-lourdes", "nossa-senhora-de-guadalupe",
            "nossa-senhora-do-perpetuo-socorro", "nossa-senhora-do-carmo",
        ],
        "santo-antonio-de-padua-santo-casamenteiro": [],
        "sao-jorge-cavaleiro-e-martir": [],
        "santo-expedito-santo-das-causas-urgentes": [],
        "santa-dulce-dos-pobres-primeira-santa-brasileira": [],
        "sao-joao-paulo-ii-o-papa-viajante": [],
        "imaculado-coracao-de-maria-significado": ["sagrado-coracao-de-jesus"],
        "castissimo-coracao-de-sao-jose-devocao": ["sagrado-coracao-de-jesus", "imaculado-coracao-de-maria"],
        "presente-de-santo-para-quem-e-ocasiao": [
            "nossa-senhora-desatadora-dos-nos", "sao-judas-tadeu", "nossa-senhora-de-fatima",
        ],
        "como-comprar-artigos-religiosos-no-atacado": [
            "sao-judas-tadeu", "nossa-senhora-aparecida", "sao-bento", "carlo-acutis",
        ],
    }
    for slug, ids_citados in casos.items():
        resposta = client.get(f"/blog/{slug}")
        assert resposta.status_code == 200
        pagina = resposta.get_data(as_text=True)
        for pid in ids_citados:
            assert f"/produto/{pid}" in pagina


def test_artigo_sem_produto_usa_cta_endpoint_manual(client):
    """ver conversa: historia da propria loja e o texto sobre
    personalizacao nao tem UM santo especifico -- o CTA principal
    linka pra /personalizada (cta_endpoint) em vez de /produto/<id>."""
    for slug in ("a-historia-da-nove-de-julho", "por-que-personalizar-uma-medalha"):
        artigo = ARTIGOS_BLOG[slug]
        assert artigo["produto_relacionado_id"] is None
        resposta = client.get(f"/blog/{slug}")
        assert resposta.status_code == 200
        pagina = resposta.get_data(as_text=True)
        assert "/personalizada" in pagina
        assert "__URL_PRODUTO__" not in pagina


def test_artigos_de_colecionar_presentear_e_atacado_usam_catalogo_completo(client):
    """ver conversa 2026-09-24: nao sao sobre UM santo especifico -- CTA
    principal linka pro catalogo inteiro em vez de /produto/<id>, mesmo
    padrao de cta_endpoint dos artigos "sem produto" acima."""
    slugs = (
        "colecionar-medalhas-de-santos-tradicao",
        "presente-de-santo-para-quem-e-ocasiao",
        "como-comprar-artigos-religiosos-no-atacado",
        "atacado-para-paroquias-e-eventos",
    )
    for slug in slugs:
        artigo = ARTIGOS_BLOG[slug]
        assert artigo["produto_relacionado_id"] is None
        assert artigo["cta_endpoint"] == "catalogo_completo"
        resposta = client.get(f"/blog/{slug}")
        assert resposta.status_code == 200
        pagina = resposta.get_data(as_text=True)
        assert "/catalogo" in pagina
        assert "__URL_PRODUTO__" not in pagina


def test_artigos_de_atacado_linkam_pra_pagina_de_revendedores(client):
    resposta = client.get("/blog/como-comprar-artigos-religiosos-no-atacado")
    pagina = resposta.get_data(as_text=True)
    assert "/para/livrarias-e-revendedores" in pagina


def test_novenas_tem_os_9_dias_e_citam_a_fonte(client):
    """ver conversa 2026-09-24: pedido explicito da usuaria de citar a
    fonte quando o texto vem do comshalom.org (ou de outro site, quando
    o comshalom nao tinha aquela novena especifica -- ver services/blog.py)."""
    casos = {
        "novena-de-santa-teresinha": "comshalom.org",
        "novena-de-sao-francisco-de-assis": "Canção Nova",
        "novena-de-santa-teresa-davila": "comshalom.org",
        "novena-de-sao-joao-paulo-ii": "comshalom.org",
        "novena-de-sao-carlo-acutis": "comshalom.org",
        "novena-de-nossa-senhora-aparecida": "padrepauloricardo.org",
    }
    for slug, fonte_esperada in casos.items():
        resposta = client.get(f"/blog/{slug}")
        assert resposta.status_code == 200
        pagina = resposta.get_data(as_text=True)
        assert pagina.count('class="novena-dia"') == 9, f"{slug}: não tem os 9 dias"
        assert fonte_esperada in pagina, f"{slug}: não cita a fonte {fonte_esperada}"


def test_historia_da_loja_e_personalizacao_linkam_entre_si(client):
    resposta = client.get("/blog/por-que-personalizar-uma-medalha")
    pagina = resposta.get_data(as_text=True)
    assert "/blog/a-historia-da-nove-de-julho" in pagina


def test_artigo_de_confianca_cita_dados_reais_e_linka_pro_catalogo(client):
    """ver conversa: artigo pensado pra quem pesquisa no Google "a loja
    e confiavel?" -- precisa citar CNPJ/endereco reais (mesmos do
    rodape, ver templates/base.html) e levar pro catalogo no final."""
    resposta = client.get("/blog/nove-de-julho-e-confiavel")
    assert resposta.status_code == 200
    pagina = resposta.get_data(as_text=True)
    assert "39.390.354/0001-25" in pagina
    assert "/atendimento/trocas-e-devolucao" in pagina
    assert "/blog/a-historia-da-nove-de-julho" in pagina
    assert "/catalogo" in pagina


def test_historia_da_loja_mostra_foto_real_de_producao(client):
    """ver conversa 2026-09-24: foto real da producao (medalhas prontas
    pra envio) no artigo da historia, pedido da usuaria."""
    resposta = client.get("/blog/a-historia-da-nove-de-julho")
    pagina = resposta.get_data(as_text=True)
    assert "medalhas-prontas.jpg" in pagina
