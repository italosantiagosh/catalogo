from __future__ import annotations

import re

import pytest

from app import app
from services.catalogo import carregar_produtos, categorias_com_slug
from services.landing_paginas import PAGINAS_LANDING


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_produtos_destaque_existem_no_catalogo():
    ids_validos = {p["id"] for p in carregar_produtos()}
    for slug, pagina in PAGINAS_LANDING.items():
        for pid in pagina["produtos_destaque"]:
            assert pid in ids_validos, f"{slug}: produtos_destaque cita {pid}, que não existe"


def test_links_internos_das_landing_pages_apontam_pra_coisas_reais():
    ids_validos = {p["id"] for p in carregar_produtos()}
    slugs_categoria_validos = {c["slug"] for c in categorias_com_slug(carregar_produtos())}
    for slug, pagina in PAGINAS_LANDING.items():
        corpo = pagina["corpo_html"]
        for pid in re.findall(r'/produto/([a-z0-9\-]+)', corpo):
            assert pid in ids_validos, f"{slug}: link inline /produto/{pid} não existe"
        for cat_slug in re.findall(r'/categoria/([a-z0-9\-]+)', corpo):
            assert cat_slug in slugs_categoria_validos, f"{slug}: link inline /categoria/{cat_slug} não existe"


def test_landing_pagina_existe_renderiza_200(client):
    for slug, pagina in PAGINAS_LANDING.items():
        resposta = client.get(f"/para/{slug}")
        assert resposta.status_code == 200
        corpo = resposta.get_data(as_text=True)
        assert pagina["titulo"] in corpo


def test_landing_pagina_inexistente_404(client):
    resposta = client.get("/para/nao-existe")
    assert resposta.status_code == 404


def test_landing_pagina_aparece_no_sitemap(client):
    corpo = client.get("/sitemap.xml").get_data(as_text=True)
    for slug in PAGINAS_LANDING:
        assert f"/para/{slug}" in corpo


def test_landing_pagina_aparece_no_llms_txt(client):
    corpo = client.get("/llms.txt").get_data(as_text=True)
    for slug in PAGINAS_LANDING:
        assert f"/para/{slug}" in corpo


def test_landing_pagina_aparece_no_rodape(client):
    corpo = client.get("/").get_data(as_text=True)
    for slug in PAGINAS_LANDING:
        assert f"/para/{slug}" in corpo


def test_landing_pagina_tem_link_pro_catalogo_ou_kit_ou_personalizada():
    """Toda landing page precisa terminar num CTA de conversao real."""
    for slug, pagina in PAGINAS_LANDING.items():
        corpo = pagina["corpo_html"]
        assert any(
            alvo in corpo for alvo in ("/catalogo", "/kit-livraria-shalom", "/personalizada")
        ), f"{slug}: sem CTA de conversão"
