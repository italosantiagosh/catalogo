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


def test_sitemap_xml_tem_lastmod_changefreq_priority(client):
    corpo = client.get("/sitemap.xml").get_data(as_text=True)
    assert "<lastmod>" in corpo
    assert "<changefreq>weekly</changefreq>" in corpo
    assert "<priority>0.8</priority>" in corpo
    assert "<changefreq>monthly</changefreq>" in corpo


def test_llms_txt(client):
    resposta = client.get("/llms.txt")
    assert resposta.status_code == 200
    assert resposta.content_type.startswith("text/plain")
    corpo = resposta.get_data(as_text=True)
    assert "Nove de Julho" in corpo
    assert "/catalogo" in corpo
    assert "/sitemap.xml" in corpo


def test_home_tem_h1_semantico(client):
    corpo = client.get("/").get_data(as_text=True)
    assert "<h1" in corpo


def test_home_ordem_das_secoes(client):
    corpo = client.get("/").get_data(as_text=True)
    marcadores = [
        "vantagens", "Mais vendidos", "Quem faz a Nove de Julho", "Ano Jubilar",
        "Preço de atacado automático", "Novidades", "Kit Livraria Shalom",
        "Preços e frete grátis podem mudar", "Peças personalizadas: envie sua foto",
    ]
    posicoes = [corpo.find(m) for m in marcadores]
    assert all(p != -1 for p in posicoes), "algum marcador da home não foi encontrado"
    assert posicoes == sorted(posicoes), "seções da home fora da ordem esperada"


def test_personalizada_tem_breadcrumb(client):
    corpo = client.get("/personalizada").get_data(as_text=True)
    assert 'class="breadcrumbs"' in corpo
    assert "BreadcrumbList" in corpo


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


def test_api_busca_encontra_produtos_personalizados(client):
    """Ver conversa: os 5 "produtos" da personalizada (config.py:
    PRODUTOS_PERSONALIZADOS) tem que aparecer na busca tambem, pra quem
    nao sabe que a personalizada existe encontrar procurando -- url vai
    pra /personalizada com o formato certo, nao pra /produto/<id>."""
    resposta = client.get("/api/busca?q=personalizada")
    dados = resposta.get_json()
    nomes = {item["nome"] for item in dados}
    assert "Medalha de 2 lados Personalizada" in nomes
    item = next(i for i in dados if i["nome"] == "Medalha de 2 lados Personalizada")
    assert item["url"] == "/personalizada?formato=medalha_2lados"


def test_catalogo_completo_lista_produtos_personalizados_com_categoria_propria(client):
    resposta = client.get("/catalogo").get_data(as_text=True)
    assert "Entremeio de 2 lados Personalizado" in resposta
    assert 'href="/personalizada?formato=entremeio_2lados"' in resposta
    assert "Personalizada</a>" in resposta  # chip de categoria


def test_catalogo_completo_lista_chaveiro_2lados_personalizado(client):
    """Ver conversa 2026-09-03: novo "produto" personalizada, mesmo
    padrao dos outros 5 ja existentes."""
    resposta = client.get("/catalogo").get_data(as_text=True)
    assert "Chaveiro de 2 lados Personalizado" in resposta
    assert 'href="/personalizada?formato=chaveiro_2lados"' in resposta
    assert "img/personalizada-chaveiro-2lados.jpg" in resposta


def test_personalizada_tem_opcao_chaveiro_2lados(client):
    resposta = client.get("/personalizada").get_data(as_text=True)
    assert 'value="chaveiro_2lados"' in resposta
    assert "Chaveiro 2 lados" in resposta


def test_personalizada_preseleciona_formato_da_query_string(client):
    resposta = client.get("/personalizada?formato=medalha_2lados").get_data(as_text=True)
    assert "window.FORMATO_INICIAL" in resposta
    assert "medalha_2lados" in resposta


def test_personalizada_tem_atalho_lado2_igual_ao_lado1(client):
    """Ver conversa: no lado 2 de um item de 2 lados, botao pra dizer
    "e´ igual ao lado 1" e ir direto pra previa combinada, sem repetir
    upload/recorte/escolha do catalogo (ver static/js/personalizada.js:
    btnLadoIgual)."""
    resposta = client.get("/personalizada").get_data(as_text=True)
    assert 'id="btn-lado-igual"' in resposta
    assert "Lado 2 é igual ao lado 1" in resposta


def test_personalizada_ignora_formato_invalido_na_query_string(client):
    resposta = client.get("/personalizada?formato=algo-invalido")
    assert resposta.status_code == 200


def test_destaque_novidades_mostra_combos_2lados_prontos(client):
    """Ver conversa 2026-09-02: cards de combo "medalha de 2 lados" pronta
    (config.py:COMBOS_2LADOS_PRONTOS) tem que aparecer no destaque
    "Novidades" da home, ao lado dos santos normais."""
    resposta = client.get("/").get_data(as_text=True)
    assert "Santa Teresinha &amp; Sagrada Face" in resposta or "Santa Teresinha & Sagrada Face" in resposta
    assert 'href="/personalizada?formato=medalha_2lados&amp;combo=combo-teresinha-sagrada-face"' in resposta
    assert "img/combo-faustina-misericordioso.jpg" in resposta


def test_personalizada_combo_valido_preenche_formato_e_window_combo(client):
    resposta = client.get("/personalizada?combo=combo-teresinha-sagrada-face").get_data(as_text=True)
    assert 'window.FORMATO_INICIAL = "medalha_2lados"' in resposta
    assert "window.COMBO_2LADOS" in resposta
    assert "santa-teresinha" in resposta
    assert "sagrada-face-de-jesus" in resposta
    assert "Santa Teresinha" in resposta


def test_personalizada_combo_invalido_nao_quebra_pagina(client):
    resposta = client.get("/personalizada?combo=nao-existe")
    assert resposta.status_code == 200
    assert "window.COMBO_2LADOS = null" in resposta.get_data(as_text=True)


def test_api_produto_modelos_devolve_imagens_por_formato(client):
    """Usado pelo "escolher um santo do catálogo" dentro do assistente
    de 2 lados (ver static/js/personalizada.js) -- mesmo formato de
    dados ja usado em templates/produto.html:modelos-grid.
    medalha_2lados_prata/ouro_velho tambem vem preenchidas pra sao-jose
    (regenerado no gabarito novo, ver conversa 2026-09-02)."""
    resposta = client.get("/api/produto/sao-jose/modelos")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert len(dados) >= 1
    modelo = dados[0]
    assert {"id", "nome", "imagens"} <= modelo.keys()
    chaves_esperadas = {
        "medalha", "entremeio_prata", "entremeio_ouro_velho", "chaveiro",
        "medalha_2lados_prata", "medalha_2lados_ouro_velho",
    }
    assert chaves_esperadas <= modelo["imagens"].keys()
    assert modelo["imagens"]["entremeio_prata"].startswith("/static/")
    assert modelo["imagens"]["medalha_2lados_prata"].startswith("/static/")
    # chaveiro_2lados (pedido 2026-09-03) tambem regenerado pro
    # catalogo inteiro -- so uma cor (prata/inox), sem sufixo.
    assert "chaveiro_2lados" in modelo["imagens"]
    assert modelo["imagens"]["chaveiro_2lados"].startswith("/static/")


def test_api_produto_modelos_produto_inexistente_404(client):
    resposta = client.get("/api/produto/nao-existe/modelos")
    assert resposta.status_code == 404


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


def test_feed_produtos_xml_bem_formado_e_uma_variacao_por_modelo(client):
    import xml.etree.ElementTree as ET

    from services.catalogo import carregar_produtos

    produtos = carregar_produtos()
    total_modelos = sum(len(p["modelos"]) for p in produtos)
    resposta = client.get("/feed-produtos.xml")
    assert resposta.status_code == 200
    assert resposta.mimetype == "application/xml"
    raiz = ET.fromstring(resposta.get_data(as_text=True))
    ns = {"g": "http://base.google.com/ns/1.0"}
    itens = raiz.findall("./channel/item")
    # 5 variacoes por modelo: medalha 12mm, medalha 16mm, entremeio
    # prata, entremeio ouro velho, chaveiro (ver _VARIANTES_FEED)
    assert len(itens) == total_modelos * 5
    primeiro = itens[0]
    assert primeiro.find("g:id", ns) is not None
    assert primeiro.find("g:item_group_id", ns) is not None
    assert primeiro.find("g:price", ns).text.endswith("BRL")
    assert primeiro.find("g:availability", ns).text == "in stock"
    assert primeiro.find("link").text.startswith("http")
    assert "Modelo 1" in primeiro.find("title").text
    assert raiz.find("./channel/language").text == "pt-BR"


def test_feed_produtos_sao_jose_tem_30_variacoes_agrupadas(client):
    import xml.etree.ElementTree as ET

    ns = {"g": "http://base.google.com/ns/1.0"}
    resposta = client.get("/feed-produtos.xml")
    raiz = ET.fromstring(resposta.get_data(as_text=True))
    itens_sao_jose = [
        item for item in raiz.findall("./channel/item") if item.find("g:id", ns).text.startswith("sao-jose-modelo")
    ]
    # 6 modelos x 5 variacoes
    assert len(itens_sao_jose) == 30
    assert all(item.find("g:item_group_id", ns).text == "sao-jose" for item in itens_sao_jose)

    precos = {item.find("g:id", ns).text: item.find("g:price", ns).text for item in itens_sao_jose}
    assert precos["sao-jose-modelo1-medalha-12mm"] == "5.00 BRL"
    assert precos["sao-jose-modelo1-chaveiro"] == "15.00 BRL"

    medalha_16mm = next(i for i in itens_sao_jose if i.find("g:id", ns).text == "sao-jose-modelo1-medalha-16mm")
    assert medalha_16mm.find("g:size", ns).text == "1,6 cm"
    entremeio_ouro = next(
        i for i in itens_sao_jose if i.find("g:id", ns).text == "sao-jose-modelo1-entremeio-ouro-velho"
    )
    assert entremeio_ouro.find("g:color", ns).text == "Ouro velho"


def test_feed_produtos_tem_rotulo_de_conjunto_pra_colecoes(client):
    import xml.etree.ElementTree as ET

    ns = {"g": "http://base.google.com/ns/1.0"}
    resposta = client.get("/feed-produtos.xml")
    raiz = ET.fromstring(resposta.get_data(as_text=True))
    itens_sao_jose = {
        item.find("g:id", ns).text: item
        for item in raiz.findall("./channel/item")
        if item.find("g:id", ns).text.startswith("sao-jose-modelo1-")
    }
    assert itens_sao_jose["sao-jose-modelo1-medalha-12mm"].find("g:custom_label_0", ns).text == "Medalha"
    assert itens_sao_jose["sao-jose-modelo1-entremeio-prata"].find("g:custom_label_0", ns).text == "Entremeio"
    assert itens_sao_jose["sao-jose-modelo1-chaveiro"].find("g:custom_label_0", ns).text == "Chaveiro"
    assert itens_sao_jose["sao-jose-modelo1-chaveiro"].find("g:product_type", ns).text == "Santos > Chaveiro"


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


def test_carrinho_expoe_producao_dias_uteis_pro_js(client):
    """Ver conversa: prazo de entrega estimado (producao + transportadora)
    mostrado junto de cada opcao de frete (static/js/carrinho_pagina.js:
    textoPrazoComProducao) precisa saber PRODUCAO_DIAS_UTEIS do lado do
    cliente."""
    from config import PRODUCAO_DIAS_UTEIS

    resposta = client.get("/carrinho").get_data(as_text=True)
    assert f"window.PRODUCAO_DIAS_UTEIS = {PRODUCAO_DIAS_UTEIS};" in resposta


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
    assert produto["brand"] == {"@type": "Brand", "name": "Nove de Julho"}
    assert produto["offers"]["priceCurrency"] == "BRL"
    assert produto["offers"]["availability"] == "https://schema.org/InStock"
    assert produto["image"].startswith("http")

    # Search Console (Listagens do comerciante) reportava validFrom,
    # hasMerchantReturnPolicy e shippingDetails ausentes em "offers", e
    # depois validThrough/priceValidUntil + merchantReturnDays.
    assert produto["offers"]["validFrom"]
    assert produto["offers"]["priceValidUntil"]
    devolucao = produto["offers"]["hasMerchantReturnPolicy"]
    assert devolucao["@type"] == "MerchantReturnPolicy"
    assert devolucao["applicableCountry"] == "BR"
    assert devolucao["merchantReturnDays"] == 7
    envio = produto["offers"]["shippingDetails"]
    assert envio["@type"] == "OfferShippingDetails"
    assert envio["shippingDestination"]["addressCountry"] == "BR"
    assert envio["deliveryTime"]["handlingTime"]["minValue"] > 0
    assert envio["deliveryTime"]["transitTime"]["maxValue"] == 20


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


def test_breadcrumb_schema_no_catalogo_completo_e_no_kit(client):
    for rota, esperado in [
        ("/catalogo", ["Início", "Catálogo completo"]),
        ("/kit-livraria-shalom", ["Início", "Kit Livraria Shalom"]),
    ]:
        html = client.get(rota).get_data(as_text=True)
        blocos = _blocos_json_ld(html)
        breadcrumbs = [b for b in blocos if b.get("@type") == "BreadcrumbList"]
        assert len(breadcrumbs) == 1, rota
        assert [i["name"] for i in breadcrumbs[0]["itemListElement"]] == esperado


def test_website_searchaction_em_toda_pagina(client):
    for rota in ["/", "/carrinho", "/produto/sao-jose"]:
        html = client.get(rota).get_data(as_text=True)
        blocos = _blocos_json_ld(html)
        websites = [b for b in blocos if b.get("@type") == "WebSite"]
        assert len(websites) == 1, rota
        acao = websites[0]["potentialAction"]
        assert acao["@type"] == "SearchAction"
        assert "/catalogo?q=" in acao["target"]["urlTemplate"]


def test_pagina_perguntas_frequentes_existe_com_faq_schema(client):
    resposta = client.get("/atendimento/perguntas-frequentes")
    assert resposta.status_code == 200
    corpo = resposta.get_data(as_text=True)
    assert "liga de zinco" in corpo
    assert "ouro velho" in corpo and "prata antigo" in corpo
    assert "aço inoxidável" in corpo
    blocos = _blocos_json_ld(corpo)
    faqs = [b for b in blocos if b.get("@type") == "FAQPage"]
    assert len(faqs) == 1
    assert len(faqs[0]["mainEntity"]) == 6


def test_perguntas_frequentes_no_rodape_e_no_sitemap(client):
    rodape = client.get("/").get_data(as_text=True)
    assert "/atendimento/perguntas-frequentes" in rodape
    sitemap = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/atendimento/perguntas-frequentes" in sitemap


def test_personalizada_tem_conteudo_e_faq_schema(client):
    resposta = client.get("/personalizada")
    corpo = resposta.get_data(as_text=True)
    assert "devoção católica" in corpo
    assert "relicário" in corpo.lower()
    assert "santo menos conhecido" in corpo.lower()
    blocos = _blocos_json_ld(corpo)
    faqs = [b for b in blocos if b.get("@type") == "FAQPage"]
    assert len(faqs) == 1
    assert len(faqs[0]["mainEntity"]) == 5


def test_pagina_404_personalizada(client):
    resposta = client.get("/rota-que-nao-existe-nunca")
    assert resposta.status_code == 404
    corpo = resposta.get_data(as_text=True)
    assert "Essa página não existe" in corpo
    assert 'href="/catalogo"' in corpo
    assert "Rua Furnas" in corpo  # confirma que usa o rodape/base.html normal, nao a pagina padrao do Flask
