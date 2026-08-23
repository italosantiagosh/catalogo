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
    assert "/catalogo<" in corpo


def test_categoria_existente(client):
    resposta = client.get("/categoria/nossa-senhora")
    assert resposta.status_code == 200
    assert "Nossa Senhora".encode() in resposta.data


def test_categoria_inexistente_404(client):
    resposta = client.get("/categoria/nao-existe")
    assert resposta.status_code == 404


def test_home_nao_tem_a_grade_completa_mas_linka_o_catalogo(client):
    # a home virou landing page (hero, vantagens, destaques, 4 santos +
    # botao) -- a grade dos 130+ produtos e o filtro por categoria saem
    # daqui e vao pra /catalogo.
    resposta = client.get("/").get_data(as_text=True)
    assert 'id="grid-produtos"' not in resposta
    assert 'id="filtros-categoria"' not in resposta
    assert 'href="/catalogo"' in resposta


def test_catalogo_completo_tem_grade_e_links_de_categoria(client):
    resposta = client.get("/catalogo").get_data(as_text=True)
    assert 'id="grid-produtos"' in resposta
    assert "/categoria/" in resposta
    assert "São José" in resposta or "sao-jose" in resposta


def test_catalogo_completo_aceita_termo_de_busca_na_url(client):
    resposta = client.get("/catalogo?q=jose").get_data(as_text=True)
    assert resposta  # so confirma que nao quebra com o parametro


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


def test_open_graph_presente_em_toda_pagina(client):
    for rota in ["/", "/carrinho", "/produto/sao-jose", "/categoria/nossa-senhora"]:
        html = client.get(rota).get_data(as_text=True)
        assert 'property="og:title"' in html, rota
        assert 'property="og:image"' in html, rota
        assert 'name="twitter:card"' in html, rota


def test_open_graph_produto_usa_imagem_do_produto(client):
    html = client.get("/produto/sao-jose").get_data(as_text=True)
    m = re.search(r'property="og:image" content="([^"]+)"', html)
    assert m is not None
    assert "sao_jose" in m.group(1)


def test_breadcrumb_schema_na_pagina_de_produto(client):
    html = client.get("/produto/sao-jose").get_data(as_text=True)
    blocos = _blocos_json_ld(html)
    breadcrumbs = [b for b in blocos if b.get("@type") == "BreadcrumbList"]
    assert len(breadcrumbs) == 1
    itens = breadcrumbs[0]["itemListElement"]
    assert [i["name"] for i in itens] == ["Catálogo", "Santos", "São José"]


def test_breadcrumb_visual_na_pagina_de_categoria(client):
    html = client.get("/categoria/nossa-senhora").get_data(as_text=True)
    assert 'class="breadcrumbs"' in html
    assert "Nossa Senhora" in html


def test_produtos_relacionados_na_pagina_de_produto(client):
    html = client.get("/produto/sao-jose").get_data(as_text=True)
    assert 'class="relacionados"' in html
    assert "Outros santos de Santos" in html


def test_barra_fixa_comprar_presente_na_pagina_de_produto(client):
    html = client.get("/produto/sao-jose").get_data(as_text=True)
    assert 'id="barra-fixa-comprar"' in html
    assert 'id="barra-fixa-btn-adicionar"' in html


def test_preview_preco_presente_na_pagina_de_produto(client):
    html = client.get("/produto/sao-jose").get_data(as_text=True)
    assert 'id="preview-preco"' in html
