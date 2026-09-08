from __future__ import annotations

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
    (e a pagina inteira, via _thumbnail_do_artigo) quebra."""
    for slug, artigo in ARTIGOS_BLOG.items():
        produto = buscar_produto(artigo["produto_relacionado_id"])
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
