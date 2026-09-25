from __future__ import annotations

import pytest

from app import app
from services.colares import COLARES, colares_publicados
from services.pricing import calcular_carrinho, preco_varejo


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_so_sagrado_coracao_esta_publicado():
    publicados = colares_publicados()
    assert [c["id"] for c in publicados] == ["sagrado-coracao-de-jesus"]
    ids_todos = {c["id"] for c in COLARES}
    assert ids_todos == {"sagrado-coracao-de-jesus", "nossa-senhora", "sao-jose"}


def test_pagina_colares_mostra_o_publicado_e_omite_os_pendentes(client):
    resposta = client.get("/colares")
    body = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "Colar Sagrado Coração de Jesus" in body
    assert "Nossa Senhora" not in body
    assert "São José" not in body
    assert "R$ 97,00" in body


def test_home_mostra_card_do_colar_publicado(client):
    body = client.get("/").get_data(as_text=True)
    assert "Colares" in body
    assert "/colares#colar-sagrado-coracao-de-jesus" in body


def test_colar_tem_preco_fixo_sem_faixa_de_atacado():
    preco_1 = preco_varejo("colar_sagrado_coracao_de_jesus")
    assert preco_1 == 97.0
    resultado = calcular_carrinho([{"chave_preco": "colar_sagrado_coracao_de_jesus", "quantidade": 50}])
    assert resultado["itens"][0]["preco_unitario"] == 97.0
    assert resultado["grupos"]["colares"]["proxima_faixa"] is None


def test_colar_nao_soma_na_faixa_de_atacado_de_medalha():
    resultado = calcular_carrinho(
        [
            {"chave_preco": "16mm", "quantidade": 19},
            {"chave_preco": "colar_sagrado_coracao_de_jesus", "quantidade": 5},
        ]
    )
    # 19 medalhas 16mm sozinhas ainda estao na faixa "1" (R$5,00) -- o
    # colar nao pode empurrar esse grupo pra faixa de atacado.
    item_medalha = next(i for i in resultado["itens"] if i["chave_preco"] == "16mm")
    assert item_medalha["preco_unitario"] == 5.0
    assert resultado["grupos"]["padrao"]["quantidade_total"] == 19


def test_carrinho_vazio_nao_quebra_com_grupo_colares():
    resultado = calcular_carrinho([])
    assert resultado["grupos"]["colares"]["quantidade_total"] == 0
    assert resultado["grupos"]["colares"]["proxima_faixa"] is None


def test_api_calcular_carrinho_aceita_colar(client):
    resposta = client.post(
        "/api/carrinho/calcular",
        json={"itens": [{"chave_preco": "colar_sagrado_coracao_de_jesus", "quantidade": 2}]},
    )
    dados = resposta.get_json()
    assert resposta.status_code == 200
    assert dados["subtotal_total"] == 194.0
    assert dados["atinge_minimo"] is True
