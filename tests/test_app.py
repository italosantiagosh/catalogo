from __future__ import annotations

import json
import re

import pytest

from app import app


def _blocos_json_ld(html: str) -> list[dict]:
    return [
        json.loads(bloco)
        for bloco in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    ]


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


def test_produto_tem_descricoes_de_formato(client):
    resposta = client.get("/produto/sao-jose")
    assert b"formato-info-medalha" in resposta.data
    assert b"formato-info-entremeio" in resposta.data
    assert b"formato-info-chaveiro" in resposta.data


def test_pagina_atendimento_existente(client):
    resposta = client.get("/atendimento/quem-somos")
    assert resposta.status_code == 200
    assert "32 anos".encode() in resposta.data


def test_pagina_atendimento_inexistente_404(client):
    resposta = client.get("/atendimento/nao-existe")
    assert resposta.status_code == 404


def test_termos_privacidade_cita_lgpd_nao_lei_portuguesa(client):
    resposta = client.get("/atendimento/termos-e-privacidade")
    corpo = resposta.get_data(as_text=True)
    assert "LGPD" in corpo
    assert "13.709" in corpo
    assert "67/98" not in corpo  # lei de Portugal do texto original, corrigida


def test_sitemap_xml_inclui_paginas_de_atendimento(client):
    resposta = client.get("/sitemap.xml")
    corpo = resposta.get_data(as_text=True)
    assert "/atendimento/envio-e-prazo-de-entrega" in corpo
    assert "/atendimento/termos-e-privacidade" in corpo


def test_rodape_tem_cnpj_endereco_e_links_institucionais(client):
    resposta = client.get("/")
    corpo = resposta.get_data(as_text=True)
    assert "39.390.354/0001-25" in corpo
    assert "Rua Furnas" in corpo
    assert "/atendimento/quem-somos" in corpo
    assert "instagram.com/novedjulho" in corpo


def test_rodape_nao_aparece_duplicado_no_carrinho(client):
    # o carrinho esconde os botoes flutuantes (whatsapp/video), mas o
    # rodape institucional deve continuar aparecendo normalmente
    resposta = client.get("/carrinho")
    assert "39.390.354/0001-25".encode() in resposta.data


def test_schema_org_organizacao_em_toda_pagina(client):
    for rota in ["/", "/carrinho", "/produto/sao-jose"]:
        html = client.get(rota).get_data(as_text=True)
        blocos = _blocos_json_ld(html)
        organizacoes = [b for b in blocos if b.get("@type") == "Organization"]
        assert len(organizacoes) == 1, f"schema Organization ausente/duplicado em {rota}"
        org = organizacoes[0]
        assert org["taxID"] == "39.390.354/0001-25"
        assert org["address"]["streetAddress"] == "Rua Furnas, 4835"


def test_schema_org_product_na_pagina_de_produto(client):
    html = client.get("/produto/sao-jose").get_data(as_text=True)
    blocos = _blocos_json_ld(html)
    produtos = [b for b in blocos if b.get("@type") == "Product"]
    assert len(produtos) == 1
    produto = produtos[0]
    assert produto["name"] == "São José"
    assert produto["offers"]["priceCurrency"] == "BRL"
    assert produto["offers"]["availability"] == "https://schema.org/InStock"
    assert produto["image"].startswith("http")
