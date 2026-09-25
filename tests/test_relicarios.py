from __future__ import annotations

import json
import re
import sqlite3

import pytest

from app import app
from services.avaliacoes import DB_PATH, inicializar_db
from services.relicarios import RELICARIOS, relicarios_publicados, relicario_por_id
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
    conexao.execute("DELETE FROM avaliacoes WHERE produto_id = 'coracao-banhado-a-ouro'")
    conexao.commit()
    conexao.close()


def test_todos_os_relicarios_estao_publicados():
    publicados = relicarios_publicados()
    assert {r["id"] for r in publicados} == {
        "coracao-banhado-a-ouro",
        "redondo-prata-zirconia",
        "oval-familia",
    }
    assert len(RELICARIOS) == len(publicados)


def test_apenas_os_dois_relicarios_de_pingente_sao_personalizaveis():
    assert relicario_por_id("coracao-banhado-a-ouro")["personalizavel"] is True
    assert relicario_por_id("redondo-prata-zirconia")["personalizavel"] is True
    assert relicario_por_id("oval-familia")["personalizavel"] is False


def test_todos_os_3_relicarios_tem_corrente_companheira():
    # Correcao 2026-09-25 (2a parte da conversa): o oval-familia NAO vem
    # com corrente inclusa (era um engano baseado so na foto de uso da
    # Parresia) -- usa a mesma corrente banhada a ouro do relicario coracao.
    assert relicario_por_id("coracao-banhado-a-ouro")["corrente"]["chave_preco"] == "corrente_veneziana_ouro"
    assert relicario_por_id("redondo-prata-zirconia")["corrente"]["chave_preco"] == "corrente_veneziana_prata"
    assert relicario_por_id("oval-familia")["corrente"]["chave_preco"] == "corrente_veneziana_ouro"


def test_rota_relicarios_redireciona_pra_linha_premium(client):
    resposta = client.get("/relicarios")
    assert resposta.status_code == 301
    assert resposta.headers["Location"] == "/linha-premium"


def test_cada_relicario_tem_a_propria_pagina_de_produto_com_preco(client):
    for relicario_id, nome, preco_str in [
        ("coracao-banhado-a-ouro", "Relicário Coração Banhado a Ouro Personalizado", "R$ 97,00"),
        ("redondo-prata-zirconia", "Relicário Redondo Prata com Zircônia Coração", "R$ 277,00"),
        ("oval-familia", "Pingente Relicário Oval Família Coração", "R$ 117,00"),
    ]:
        resposta = client.get(f"/linha-premium/{relicario_id}")
        body = resposta.get_data(as_text=True)
        assert resposta.status_code == 200
        assert nome in body
        assert preco_str in body


def test_pagina_linha_premium_lista_os_3_relicarios(client):
    body = client.get("/linha-premium").get_data(as_text=True)
    assert "Relicário Coração Banhado a Ouro Personalizado" in body
    assert "Relicário Redondo Prata com Zircônia Coração" in body
    assert "Pingente Relicário Oval Família Coração" in body


def test_pagina_do_relicario_mostra_upload_so_pros_personalizaveis(client):
    body_ouro = client.get("/linha-premium/coracao-banhado-a-ouro").get_data(as_text=True)
    assert "personalizacao-input" in body_ouro

    body_oval = client.get("/linha-premium/oval-familia").get_data(as_text=True)
    assert "personalizacao-input" not in body_oval


def test_pagina_de_cada_relicario_mostra_compre_junto_da_propria_corrente(client):
    body_ouro = client.get("/linha-premium/coracao-banhado-a-ouro").get_data(as_text=True)
    assert "compre-junto-card" in body_ouro
    assert "Corrente Veneziana Fio Fechada (40+5cm) Banhada a Ouro" in body_ouro

    body_prata = client.get("/linha-premium/redondo-prata-zirconia").get_data(as_text=True)
    assert "compre-junto-card" in body_prata
    assert "Corrente Prata Veneziana Diamantada (45cm)" in body_prata

    body_oval = client.get("/linha-premium/oval-familia").get_data(as_text=True)
    assert "compre-junto-card" in body_oval
    assert "Corrente Veneziana Fio Fechada (40+5cm) Banhada a Ouro" in body_oval


def test_home_mostra_card_do_relicario(client):
    body = client.get("/").get_data(as_text=True)
    assert "Linha Premium" in body
    assert "/linha-premium/coracao-banhado-a-ouro" in body


def test_relicario_tem_preco_fixo_sem_faixa_de_atacado():
    assert preco_varejo("relicario_coracao_ouro") == 97.0
    assert preco_varejo("relicario_redondo_prata") == 277.0
    assert preco_varejo("relicario_oval_familia") == 117.0
    resultado = calcular_carrinho([{"chave_preco": "relicario_redondo_prata", "quantidade": 20}])
    assert resultado["itens"][0]["preco_unitario"] == 277.0
    assert resultado["grupos"]["relicarios"]["proxima_faixa"] is None


def test_corrente_tem_preco_fixo_e_grupo_isolado_do_relicario():
    assert preco_varejo("corrente_veneziana_ouro") == 112.0
    assert preco_varejo("corrente_veneziana_prata") == 132.0
    resultado = calcular_carrinho(
        [
            {"chave_preco": "relicario_coracao_ouro", "quantidade": 1},
            {"chave_preco": "corrente_veneziana_ouro", "quantidade": 1},
        ]
    )
    assert resultado["grupos"]["relicarios"]["quantidade_total"] == 1
    assert resultado["grupos"]["correntes"]["quantidade_total"] == 1
    assert resultado["subtotal_total"] == 97.0 + 112.0


def test_relicario_nao_soma_na_faixa_de_atacado_de_medalha():
    resultado = calcular_carrinho(
        [
            {"chave_preco": "16mm", "quantidade": 19},
            {"chave_preco": "relicario_coracao_ouro", "quantidade": 5},
        ]
    )
    item_medalha = next(i for i in resultado["itens"] if i["chave_preco"] == "16mm")
    assert item_medalha["preco_unitario"] == 5.0
    assert resultado["grupos"]["padrao"]["quantidade_total"] == 19


def test_carrinho_vazio_nao_quebra_com_grupos_relicarios_e_correntes():
    resultado = calcular_carrinho([])
    assert resultado["grupos"]["relicarios"]["quantidade_total"] == 0
    assert resultado["grupos"]["correntes"]["quantidade_total"] == 0
    assert resultado["grupos"]["relicarios"]["proxima_faixa"] is None
    assert resultado["grupos"]["correntes"]["proxima_faixa"] is None


def test_api_calcular_carrinho_aceita_relicario_e_corrente(client):
    resposta = client.post(
        "/api/carrinho/calcular",
        json={
            "itens": [
                {"chave_preco": "relicario_redondo_prata", "quantidade": 1},
                {"chave_preco": "corrente_veneziana_prata", "quantidade": 1},
            ]
        },
    )
    dados = resposta.get_json()
    assert resposta.status_code == 200
    assert dados["subtotal_total"] == 277.0 + 132.0


def test_pagina_do_relicario_tem_json_ld_valido(client):
    body = client.get("/linha-premium/coracao-banhado-a-ouro").get_data(as_text=True)
    blocos = re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)
    dados_produto = [json.loads(b) for b in blocos if '"@type": "Product"' in b]
    assert len(dados_produto) == 1
    assert dados_produto[0]["offers"]["price"] == "97.00"


def test_avaliar_pagina_isolada_aceita_relicario(client):
    assert client.get("/avaliar/coracao-banhado-a-ouro").status_code == 200
    assert client.get("/avaliar/relicario-que-nao-existe").status_code == 404


def test_envia_e_lista_avaliacao_de_relicario(client):
    resposta = client.post(
        "/api/avaliacoes",
        data={"produto_id": "coracao-banhado-a-ouro", "nome_cliente": "Ana Teste", "nota": "5", "texto": "Lindo!"},
    )
    assert resposta.status_code == 200
    assert resposta.get_json() == {"ok": True}

    from services.avaliacoes import atualizar_status, listar_avaliacoes

    pendente = next(a for a in listar_avaliacoes(status="pendente") if a["produto_id"] == "coracao-banhado-a-ouro")
    atualizar_status(pendente["id"], "aprovada")

    body = client.get("/linha-premium/coracao-banhado-a-ouro").get_data(as_text=True)
    assert "Ana Teste" in body
    assert "Lindo!" in body


def test_itens_com_descricao_guarda_personalizacao_do_relicario(client):
    resposta = client.post(
        "/api/pedido/criar-whatsapp",
        json={
            "cliente_telefone": "84991234567",
            "itens": [
                {
                    "chave_preco": "relicario_coracao_ouro",
                    "quantidade": 1,
                    "produtoNome": "Relicário Coração Banhado a Ouro Personalizado",
                    "produtoId": "coracao-banhado-a-ouro",
                    "formato": "relicario",
                    "personalizavel": True,
                    "personalizacaoFoto": "data:image/jpeg;base64,AAAA",
                },
            ],
            "frete": {"preco": 0, "texto": "Retirada no local", "prazo_dias": 1},
        },
    )
    assert resposta.status_code == 200
    token = resposta.get_json()["token"]

    from services.pedidos import obter_pedido

    pedido = obter_pedido(token)
    item = pedido["itens"][0]
    assert item["detalhe"] == "Relicário"
    assert item["personalizavel"] is True
    assert item["personalizacaoFoto"] == "data:image/jpeg;base64,AAAA"

    conexao = sqlite3.connect(DB_PATH)
    conexao.execute("DELETE FROM pedidos WHERE token = ?", (token,))
    conexao.commit()
    conexao.close()
