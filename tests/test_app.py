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
    # a home virou landing page (hero, vantagens, destaques, busca ao
    # vivo, chips de categoria, 4 santos + botao) -- so a grade dos 130+
    # produtos sai daqui e vai pra /catalogo.
    resposta = client.get("/").get_data(as_text=True)
    assert 'id="grid-produtos"' not in resposta
    assert 'id="filtros-categoria"' in resposta
    assert 'id="busca-home-resultados"' in resposta
    assert 'href="/catalogo"' in resposta


def test_home_mostra_so_4_cards_no_final(client):
    resposta = client.get("/").get_data(as_text=True)
    assert resposta.count('class="card-produto"') == 4


def test_home_banners_usam_imagem_em_vez_de_texto(client):
    resposta = client.get("/").get_data(as_text=True)
    assert "img/banner-atacado.jpg" in resposta
    assert "img/banner-kit.jpg" in resposta
    assert "img/banner-personalizada.jpg" in resposta


def test_rodape_icones_de_contato(client):
    resposta = client.get("/").get_data(as_text=True)
    assert "img/icone-whatsapp.png" in resposta
    assert "img/icone-instagram.png" in resposta


def test_destaque_ano_jubilar_mostra_modelos_de_sao_francisco(client):
    resposta = client.get("/").get_data(as_text=True)
    assert "São Francisco — Modelo 1" in resposta
    assert "São Francisco — Modelo 4" in resposta
    assert "Santa Clara" not in resposta


def test_kit_livraria_shalom_tem_banner_nao_clicavel_no_topo(client):
    resposta = client.get("/kit-livraria-shalom").get_data(as_text=True)
    assert "img/banner-kit.jpg" in resposta
    # na home essa mesma imagem fica dentro de <a class="banner-kit">
    # (clicavel); na propria pagina do kit nao deve virar link.
    assert 'class="banner-kit"' not in resposta


def test_api_busca_encontra_por_nome_sem_acento(client):
    resposta = client.get("/api/busca?q=jose")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert any(item["nome"] == "São José" for item in dados)
    assert all({"id", "nome", "thumbnail", "url"} <= item.keys() for item in dados)


def test_api_busca_sem_termo_retorna_vazio(client):
    resposta = client.get("/api/busca")
    assert resposta.get_json() == []


def test_kit_livraria_shalom_lista_todos_os_itens_configurados(client):
    from config import KIT_LIVRARIA_SHALOM

    resposta = client.get("/kit-livraria-shalom")
    assert resposta.status_code == 200
    corpo = resposta.get_data(as_text=True)
    assert corpo.count('class="kit-item"') == len(KIT_LIVRARIA_SHALOM)
    assert "Nossa Senhora Porta do Céu" in corpo
    assert "modelo longe" in corpo and "modelo perto" in corpo


def test_kit_livraria_shalom_soma_a_quantidade_sugerida_total(client):
    from config import KIT_LIVRARIA_SHALOM

    esperado = sum(item["quantidade_sugerida"] for item in KIT_LIVRARIA_SHALOM)
    resposta = client.get("/kit-livraria-shalom").get_data(as_text=True)
    assert f"{esperado} unidades no total" in resposta


def test_produto_novo_porta_do_ceu_acessivel(client):
    resposta = client.get("/produto/nossa-senhora-porta-do-ceu")
    assert resposta.status_code == 200
    assert "Nossa Senhora Porta do Céu".encode() in resposta.data


def test_esposa_do_espirito_foi_renomeada(client):
    resposta = client.get("/produto/esposa-do-espirito")
    assert resposta.status_code == 200
    assert "Nossa Senhora Esposa do Espírito".encode() in resposta.data


def test_sitemap_xml_inclui_o_kit(client):
    resposta = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/kit-livraria-shalom" in resposta


def test_normalizar_dominio_tolera_esquema_e_barra_no_final():
    from config import _normalizar_dominio

    esperado = "atacado.lojanovedejulho.com.br"
    assert _normalizar_dominio("atacado.lojanovedejulho.com.br") == esperado
    assert _normalizar_dominio("https://atacado.lojanovedejulho.com.br") == esperado
    assert _normalizar_dominio("http://atacado.lojanovedejulho.com.br") == esperado
    assert _normalizar_dominio("https://atacado.lojanovedejulho.com.br/") == esperado
    assert _normalizar_dominio("  https://atacado.lojanovedejulho.com.br/  ") == esperado


def test_feed_produtos_xml_bem_formado_e_com_todos_os_produtos(client):
    import xml.etree.ElementTree as ET

    from services.catalogo import carregar_produtos

    produtos = len(carregar_produtos())
    resposta = client.get("/feed-produtos.xml")
    assert resposta.status_code == 200
    assert resposta.mimetype == "application/xml"
    raiz = ET.fromstring(resposta.get_data(as_text=True))
    ns = {"g": "http://base.google.com/ns/1.0"}
    itens = raiz.findall("./channel/item")
    # 3 itens por produto: medalha, entremeio e chaveiro (ver _FORMATOS_FEED)
    assert len(itens) == produtos * 3
    primeiro = itens[0]
    assert primeiro.find("g:id", ns) is not None
    assert primeiro.find("g:price", ns).text.endswith("BRL")
    assert primeiro.find("g:availability", ns).text == "in stock"
    assert primeiro.find("link").text.startswith("http")
    assert primeiro.find("title").text.startswith("Medalha de ")
    assert raiz.find("./channel/language").text == "pt-BR"


def test_feed_produtos_chaveiro_tem_preco_diferente_de_medalha(client):
    import xml.etree.ElementTree as ET

    ns = {"g": "http://base.google.com/ns/1.0"}
    resposta = client.get("/feed-produtos.xml")
    raiz = ET.fromstring(resposta.get_data(as_text=True))
    itens_sao_jose = [
        item for item in raiz.findall("./channel/item") if item.find("g:id", ns).text.startswith("sao-jose-")
    ]
    precos = {item.find("g:id", ns).text: item.find("g:price", ns).text for item in itens_sao_jose}
    assert precos["sao-jose-medalha"] == "5.00 BRL"
    assert precos["sao-jose-entremeio"] == "5.00 BRL"
    assert precos["sao-jose-chaveiro"] == "15.00 BRL"


def test_healthz_sempre_200(client):
    resposta = client.get("/healthz")
    assert resposta.status_code == 200


def test_sem_canonical_domain_configurado_nao_redireciona(client):
    # comportamento padrao (CANONICAL_DOMAIN vazio) -- e o que todos os
    # outros testes deste arquivo ja assumem implicitamente.
    resposta = client.get("/", headers={"Host": "catalogo-medalhas.onrender.com"})
    assert resposta.status_code == 200


def test_com_canonical_domain_redireciona_host_diferente(client, monkeypatch):
    monkeypatch.setattr("app.CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    resposta = client.get(
        "/produto/sao-jose?ref=teste", headers={"Host": "catalogo-medalhas.onrender.com"}
    )
    assert resposta.status_code == 301
    assert resposta.headers["Location"] == "https://atacado.lojanovedejulho.com.br/produto/sao-jose?ref=teste"


def test_com_canonical_domain_nao_redireciona_o_proprio_dominio(client, monkeypatch):
    monkeypatch.setattr("app.CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    resposta = client.get("/", headers={"Host": "atacado.lojanovedejulho.com.br"})
    assert resposta.status_code == 200


def test_com_canonical_domain_healthz_e_api_ficam_de_fora(client, monkeypatch):
    monkeypatch.setattr("app.CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    assert client.get("/healthz", headers={"Host": "catalogo-medalhas.onrender.com"}).status_code == 200
    resposta = client.post(
        "/api/carrinho/calcular", json={"itens": []}, headers={"Host": "catalogo-medalhas.onrender.com"}
    )
    assert resposta.status_code == 200


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
