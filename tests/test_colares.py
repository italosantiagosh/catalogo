from __future__ import annotations

import json
import re
import sqlite3

import pytest

from app import app
from services.avaliacoes import DB_PATH, inicializar_db
from services.colares import COLARES, colares_publicados
from services.pricing import calcular_carrinho, preco_varejo


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def _limpa_avaliacoes_de_teste():
    yield
    inicializar_db()
    conexao = sqlite3.connect(DB_PATH)
    conexao.execute("DELETE FROM avaliacoes WHERE produto_id = 'sagrado-coracao-de-jesus'")
    conexao.commit()
    conexao.close()


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


def test_pagina_colares_tem_json_ld_valido_por_peca(client):
    body = client.get("/colares").get_data(as_text=True)
    blocos = re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)
    assert len(blocos) >= 2  # breadcrumb + pelo menos 1 produto
    dados_produto = [json.loads(b) for b in blocos if '"@type": "Product"' in b]
    assert len(dados_produto) == 1
    assert dados_produto[0]["offers"]["price"] == "97.00"


def test_avaliar_pagina_isolada_aceita_colar(client):
    assert client.get("/avaliar/sagrado-coracao-de-jesus").status_code == 200
    assert client.get("/avaliar/nossa-senhora").status_code == 404  # nao publicado ainda


def test_envia_e_lista_avaliacao_de_colar(client):
    resposta = client.post(
        "/api/avaliacoes",
        data={"produto_id": "sagrado-coracao-de-jesus", "nome_cliente": "Ana Teste", "nota": "5", "texto": "Amei!"},
    )
    assert resposta.status_code == 200
    assert resposta.get_json() == {"ok": True}

    from services.avaliacoes import atualizar_status, listar_avaliacoes

    pendente = next(a for a in listar_avaliacoes(status="pendente") if a["produto_id"] == "sagrado-coracao-de-jesus")
    atualizar_status(pendente["id"], "aprovada")

    body = client.get("/colares").get_data(as_text=True)
    assert "Ana Teste" in body
    assert "Amei!" in body


def test_avaliacao_de_colar_nao_publicado_e_recusada(client):
    resposta = client.post(
        "/api/avaliacoes",
        data={"produto_id": "nossa-senhora", "nome_cliente": "Ana", "nota": "5"},
    )
    assert resposta.status_code == 404
