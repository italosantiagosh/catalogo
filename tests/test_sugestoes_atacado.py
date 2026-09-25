from __future__ import annotations

import pytest

from app import app
from services.catalogo import carregar_produtos


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_distribui_as_unidades_que_faltam_entre_ate_3_produtos(client):
    resposta = client.get("/api/carrinho/sugestoes-atacado?formato=medalha&chave_preco=16mm&faltam=10")
    dados = resposta.get_json()
    assert resposta.status_code == 200
    assert 1 <= len(dados["sugestoes"]) <= 3
    assert sum(s["quantidade"] for s in dados["sugestoes"]) == 10
    for sugestao in dados["sugestoes"]:
        assert sugestao["formato"] == "medalha"
        assert sugestao["chave_preco"] == "16mm"
        assert sugestao["cor"] is None


def test_usa_a_imagem_certa_por_formato_e_cor(client):
    produtos_por_id = {p["id"]: p for p in carregar_produtos()}

    resposta_entremeio = client.get(
        "/api/carrinho/sugestoes-atacado?formato=entremeio&chave_preco=entremeio&cor=ouro_velho&faltam=5"
    )
    sugestao_entremeio = resposta_entremeio.get_json()["sugestoes"][0]
    modelo_entremeio = produtos_por_id[sugestao_entremeio["id"]]["modelos"][0]
    assert modelo_entremeio["imagem_entremeio_ouro_velho"] in sugestao_entremeio["thumbnail"]

    resposta_chaveiro = client.get("/api/carrinho/sugestoes-atacado?formato=chaveiro&chave_preco=chaveiro&faltam=3")
    sugestao_chaveiro = resposta_chaveiro.get_json()["sugestoes"][0]
    modelo_chaveiro = produtos_por_id[sugestao_chaveiro["id"]]["modelos"][0]
    assert modelo_chaveiro["imagem_chaveiro"] in sugestao_chaveiro["thumbnail"]


def test_nao_sugere_produto_ja_no_carrinho(client):
    produtos = carregar_produtos()
    ids_pra_excluir = [produtos[0]["id"], produtos[1]["id"], produtos[2]["id"]]
    resposta = client.get(
        f"/api/carrinho/sugestoes-atacado?formato=medalha&chave_preco=12mm&faltam=6&excluir={','.join(ids_pra_excluir)}"
    )
    dados = resposta.get_json()
    sugeridos = {s["id"] for s in dados["sugestoes"]}
    assert sugeridos.isdisjoint(ids_pra_excluir)


def test_prioriza_produtos_mais_vendidos_recentemente(client, monkeypatch):
    produtos = carregar_produtos()
    mais_vendido = produtos[-1]["id"]
    monkeypatch.setattr("app.unidades_vendidas_por_produto", lambda dias: {mais_vendido: 999})

    resposta = client.get("/api/carrinho/sugestoes-atacado?formato=medalha&chave_preco=12mm&faltam=6")
    dados = resposta.get_json()

    assert dados["sugestoes"][0]["id"] == mais_vendido


def test_faltam_zero_nao_sugere_nada(client):
    resposta = client.get("/api/carrinho/sugestoes-atacado?formato=medalha&chave_preco=12mm&faltam=0")
    assert resposta.get_json()["sugestoes"] == []


def test_formato_invalido_400(client):
    resposta = client.get("/api/carrinho/sugestoes-atacado?formato=medalha_2lados&chave_preco=medalha_2lados&faltam=5")
    assert resposta.status_code == 400


def test_chave_preco_invalida_400(client):
    resposta = client.get("/api/carrinho/sugestoes-atacado?formato=medalha&chave_preco=lixo&faltam=5")
    assert resposta.status_code == 400
