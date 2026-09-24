from __future__ import annotations

from unittest.mock import patch

import pytest

import services.carrinhos_abandonados as carrinhos_abandonados
import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(pedidos, "DB_PATH", db_path)
    monkeypatch.setattr(carrinhos_abandonados, "DB_PATH", db_path)
    app.config["TESTING"] = True
    return app.test_client()


def _corpo_valido(**overrides):
    base = dict(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "produtoId": "sao-jose",
                "produtoNome": "São José", "modeloId": "modelo-1", "modeloNome": "Modelo 1"}],
        frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0},
        cliente={"nome": "Maria Aparecida Silva", "tipo_pessoa": "fisica", "documento": "11144477735",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def _criar(client, **overrides) -> str:
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido(**overrides)).get_json()
    return criado["token"]


def test_saudacao_usa_so_o_primeiro_nome(client):
    token = _criar(client)
    html = client.get(f"/pedido/{token}").data.decode()
    assert "Olá, Maria!" in html
    assert "Olá, Maria Aparecida Silva!" not in html


def test_botao_rastrear_maiusculo_e_destacado(client):
    token = _criar(client)
    pedidos.marcar_pago(token, forma_pagamento="pix", parcelas=None, valor_pago=100.0, transaction_nsu="n1")
    pedidos.atualizar_status(
        token, "enviado", codigo_rastreio="BR123", link_rastreio="https://rastreio.exemplo/BR123",
        transportadora="Correios",
    )
    html = client.get(f"/pedido/{token}").data.decode()
    assert '<a href="https://rastreio.exemplo/BR123" target="_blank" rel="noopener" class="botao-rastrear">RASTREAR</a>' in html


def test_forma_pagamento_usa_rotulo_bonito(client):
    token = _criar(client)
    pedidos.marcar_pago(token, forma_pagamento="credit_card", parcelas=3, valor_pago=100.0, transaction_nsu="n1")
    html = client.get(f"/pedido/{token}").data.decode()
    assert "Cartão de crédito" in html
    assert "credit_card" not in html


def test_repetir_pedido_tem_texto_explicativo(client):
    token = _criar(client)
    html = client.get(f"/pedido/{token}").data.decode()
    assert "Reaproveite os itens, as imagens e os dados de entrega" in html
