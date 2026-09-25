from __future__ import annotations

import pytest

from app import app
from services.catalogo import carregar_produtos
from services.pricing import preco_varejo


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_sugere_ate_3_produtos_com_preco_do_menor_formato(client):
    resposta = client.get("/api/carrinho/sugestoes-pedido-minimo")
    dados = resposta.get_json()
    assert resposta.status_code == 200
    assert 1 <= len(dados["sugestoes"]) <= 3
    for sugestao in dados["sugestoes"]:
        assert sugestao["preco"] == preco_varejo("12mm")
        assert sugestao["thumbnail"].startswith("/static/")


def test_nao_sugere_produto_ja_no_carrinho(client):
    produtos = carregar_produtos()
    ids_pra_excluir = [produtos[0]["id"], produtos[1]["id"], produtos[2]["id"]]
    resposta = client.get(f"/api/carrinho/sugestoes-pedido-minimo?excluir={','.join(ids_pra_excluir)}")
    dados = resposta.get_json()
    sugeridos = {s["id"] for s in dados["sugestoes"]}
    assert sugeridos.isdisjoint(ids_pra_excluir)


def test_prioriza_produtos_mais_vendidos_recentemente(client, monkeypatch):
    produtos = carregar_produtos()
    mais_vendido = produtos[-1]["id"]  # ultimo da lista, sem chance de vir por ordem natural
    monkeypatch.setattr("app.unidades_vendidas_por_produto", lambda dias: {mais_vendido: 999})

    resposta = client.get("/api/carrinho/sugestoes-pedido-minimo")
    dados = resposta.get_json()

    assert dados["sugestoes"][0]["id"] == mais_vendido
