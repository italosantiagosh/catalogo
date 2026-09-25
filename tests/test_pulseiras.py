from __future__ import annotations

import pytest

from app import app
from services.pulseiras import PULSEIRAS, pulseiras_publicadas
from services.pricing import calcular_carrinho, preco_varejo


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_pulseira_consagracao_esta_publicada():
    publicadas = pulseiras_publicadas()
    assert [p["id"] for p in publicadas] == ["consagracao-nossa-senhora"]
    assert len(PULSEIRAS) == 1


def test_rota_pulseiras_redireciona_pra_linha_premium(client):
    resposta = client.get("/pulseiras")
    assert resposta.status_code == 301
    assert resposta.headers["Location"] == "/linha-premium"


def test_pagina_da_pulseira_mostra_a_publicada(client):
    resposta = client.get("/linha-premium/consagracao-nossa-senhora")
    body = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "Pulseira de Consagração a Nossa Senhora" in body
    assert "R$ 197,00" in body


def test_home_mostra_card_da_pulseira(client):
    body = client.get("/").get_data(as_text=True)
    assert "Linha Premium" in body
    assert "/linha-premium/consagracao-nossa-senhora" in body


def test_pulseira_tem_preco_fixo_sem_faixa_de_atacado():
    assert preco_varejo("pulseira_consagracao_nossa_senhora") == 197.0
    resultado = calcular_carrinho([{"chave_preco": "pulseira_consagracao_nossa_senhora", "quantidade": 10}])
    assert resultado["itens"][0]["preco_unitario"] == 197.0
    assert resultado["grupos"]["pulseiras"]["proxima_faixa"] is None


def test_pulseira_e_colar_nao_se_misturam_na_mesma_faixa():
    resultado = calcular_carrinho(
        [
            {"chave_preco": "colar_sagrado_coracao_de_jesus", "quantidade": 3},
            {"chave_preco": "pulseira_consagracao_nossa_senhora", "quantidade": 2},
        ]
    )
    assert resultado["grupos"]["colares"]["quantidade_total"] == 3
    assert resultado["grupos"]["pulseiras"]["quantidade_total"] == 2
    assert resultado["subtotal_total"] == round(97.0 * 3 + 197.0 * 2, 2)


def test_carrinho_vazio_nao_quebra_com_grupo_pulseiras():
    resultado = calcular_carrinho([])
    assert resultado["grupos"]["pulseiras"]["quantidade_total"] == 0


def test_api_calcular_carrinho_aceita_pulseira(client):
    resposta = client.post(
        "/api/carrinho/calcular",
        json={"itens": [{"chave_preco": "pulseira_consagracao_nossa_senhora", "quantidade": 1}]},
    )
    dados = resposta.get_json()
    assert resposta.status_code == 200
    assert dados["subtotal_total"] == 197.0
