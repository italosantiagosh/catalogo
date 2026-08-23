from __future__ import annotations

import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_robots_txt(client):
    resposta = client.get("/robots.txt")
    assert resposta.status_code == 200
    assert resposta.mimetype == "text/plain"
    assert "Sitemap:" in resposta.get_data(as_text=True)
    assert "sitemap.xml" in resposta.get_data(as_text=True)


def test_sitemap_xml_inclui_home_e_paginas_de_categoria(client):
    resposta = client.get("/sitemap.xml")
    assert resposta.status_code == 200
    assert resposta.mimetype == "application/xml"
    corpo = resposta.get_data(as_text=True)
    assert "<urlset" in corpo
    assert "/categoria/nossa-senhora" in corpo
    assert "/produto/sao-jose" in corpo


def test_categoria_existente(client):
    resposta = client.get("/categoria/nossa-senhora")
    assert resposta.status_code == 200
    assert "Nossa Senhora".encode() in resposta.data


def test_categoria_inexistente_404(client):
    resposta = client.get("/categoria/nao-existe")
    assert resposta.status_code == 404


def test_home_linka_paginas_de_categoria(client):
    resposta = client.get("/")
    assert b"/categoria/" in resposta.data


def test_produto_tem_meta_description(client):
    resposta = client.get("/produto/sao-jose")
    assert b'name="description"' in resposta.data
