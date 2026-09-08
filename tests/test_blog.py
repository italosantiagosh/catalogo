from __future__ import annotations

import re

import pytest

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
    resposta = client.get("/blog")
    assert resposta.status_code == 200
    pagina = resposta.get_data(as_text=True)
    for artigo in ARTIGOS_BLOG.values():
        assert artigo["titulo"] in pagina


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
    nenhum desses links crus aponta pra um id/slug que nao existe."""
    ids_validos = {p["id"] for p in carregar_produtos()}
    slugs_validos = set(ARTIGOS_BLOG.keys())
    for slug, artigo in ARTIGOS_BLOG.items():
        corpo = artigo["corpo_html"]
        for pid in re.findall(r'/produto/([a-z0-9\-]+)', corpo):
            assert pid in ids_validos, f"{slug}: link inline /produto/{pid} não existe"
        for slug_inline in re.findall(r'/blog/([a-z0-9\-]+)', corpo):
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
        "nossa-senhora-titulos-e-aparicoes": [],
        "santo-antonio-de-padua-santo-casamenteiro": [],
        "sao-jorge-cavaleiro-e-martir": [],
        "santo-expedito-santo-das-causas-urgentes": [],
        "santa-dulce-dos-pobres-primeira-santa-brasileira": [],
        "sao-joao-paulo-ii-o-papa-viajante": [],
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


def test_historia_da_loja_e_personalizacao_linkam_entre_si(client):
    resposta = client.get("/blog/por-que-personalizar-uma-medalha")
    pagina = resposta.get_data(as_text=True)
    assert "/blog/a-historia-da-nove-de-julho" in pagina
