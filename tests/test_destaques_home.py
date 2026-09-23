from __future__ import annotations

from app import _itens_do_grid, _montar_destaques, app, carregar_produtos


def _montar_sagrados_coracoes():
    with app.test_request_context():
        produtos = carregar_produtos()
        itens_por_id = {item["id"]: item for item in _itens_do_grid(produtos)}
        destaques = _montar_destaques(produtos, itens_por_id)
    return next(d for d in destaques if d["chave"] == "sagrados_coracoes")


def test_sagrados_coracoes_usa_modelo_2_pro_jesus_e_pra_maria():
    """ver conversa 2026-09-22: a colecao "Sagrados Coracoes" precisa
    mostrar SO o coracao nos cards -- Sagrado Coracao de Jesus e
    Imaculado Coracao de Maria tem um Modelo 1 com a figura inteira
    (Jesus/Maria) e um Modelo 2 so com o coracao, entao esse destaque
    precisa forcar o modelo 2 desses dois sem mudar o modelo padrao
    usado no resto do site (grade do catalogo, busca etc.)."""
    destaque = _montar_sagrados_coracoes()
    produtos_por_id = {p["id"]: p for p in destaque["produtos"]}

    assert produtos_por_id["sagrado-coracao-de-jesus"]["nome"] == "Sagrado Coração de Jesus - Modelo 2"
    assert "modelo_2" in produtos_por_id["sagrado-coracao-de-jesus"]["thumbnail"]

    assert produtos_por_id["imaculado-coracao-de-maria"]["nome"] == "Imaculado Coração de Maria - Modelo 2"
    assert "modelo_2" in produtos_por_id["imaculado-coracao-de-maria"]["thumbnail"]


def test_sagrados_coracoes_nao_mexe_nos_produtos_sem_override():
    """Três Corações e Castíssimo Coração de São José só têm modelo 1 --
    continuam usando a foto/nome normais (sem override)."""
    destaque = _montar_sagrados_coracoes()
    produtos_por_id = {p["id"]: p for p in destaque["produtos"]}

    assert produtos_por_id["tres-coracoes"]["nome"] == "Três Corações"
    assert produtos_por_id["castissimo-coracao-de-sao-jose"]["nome"] == "Castíssimo Coração de São José"


def test_catalogo_grid_continua_no_modelo_1_pro_jesus():
    """O override e´ so pra esse destaque especifico -- a grade normal do
    catalogo continua mostrando o modelo 1 (comportamento padrao,
    inalterado)."""
    produtos = carregar_produtos()
    itens = {item["id"]: item for item in _itens_do_grid(produtos)}
    assert "modelo_1" in itens["sagrado-coracao-de-jesus"]["thumbnail"]


def _montar_novidades():
    with app.test_request_context():
        produtos = carregar_produtos()
        itens_por_id = {item["id"]: item for item in _itens_do_grid(produtos)}
        destaques = _montar_destaques(produtos, itens_por_id)
    return next(d for d in destaques if d["chave"] == "novidades")


def test_novidades_usa_formato_por_produto():
    """ver conversa 2026-09-24: cards de "Novidades" variam o FORMATO
    mostrado (nao so medalha) pra alguns produtos -- Sandra Sabattini e
    Moscatti em chaveiro, Filho Pródigo em entremeio ouro velho, Chiara
    Luce em entremeio prata."""
    destaque = _montar_novidades()
    produtos_por_id = {p["id"]: p for p in destaque["produtos"]}

    assert "chaveiro" in produtos_por_id["beata-sandra-sabatine"]["thumbnail"]
    assert "chaveiro" in produtos_por_id["sao-jose-moscatti"]["thumbnail"]
    assert "entremeio_ouro_velho" in produtos_por_id["filho-prodigo-acamps"]["thumbnail"]
    assert "entremeio_prata" in produtos_por_id["chiara-luce"]["thumbnail"]

    # nome do produto continua normal (sem sufixo de modelo, diferente
    # do modelo_por_produto -- aqui e´ o mesmo modelo, so outro formato)
    assert produtos_por_id["beata-sandra-sabatine"]["nome"] == "Beata Sandra Sabattini"


def test_novidades_nao_mexe_nos_produtos_sem_override():
    destaque = _montar_novidades()
    produtos_por_id = {p["id"]: p for p in destaque["produtos"]}
    assert "medalha" in produtos_por_id["santa-bakhita"]["thumbnail"]
