from __future__ import annotations

from unittest.mock import patch

import pytest

import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _corpo_valido(**overrides):
    base = dict(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"}],
        frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0},
        cliente={"nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "11144477735",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def _criar_e_cancelar(client) -> str:
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/original"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    pedidos.cancelar_pedido(criado["token"])
    return criado["token"]


# ---- reativar via Pix ----

def test_reativar_pix_reativa_e_redireciona_pro_pagamento(client):
    token = _criar_e_cancelar(client)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/novo"}) as mock_link:
        resposta = client.get(f"/pedido/{token}/reativar-pix")

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "https://checkout.infinitepay.io/novo"
    assert mock_link.call_count == 1

    pedido = pedidos.obter_pedido(token)
    assert pedido["status"] == "pendente"
    assert pedido["cancelado_em"] is None


def test_reativar_pix_pedido_ja_pago_nao_gera_link_novo(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    pedidos.marcar_pago(criado["token"], forma_pagamento="pix", parcelas=None, valor_pago=78.65, transaction_nsu="tx")

    with patch("app.criar_link_pagamento") as mock_link:
        resposta = client.get(f"/pedido/{criado['token']}/reativar-pix")

    assert resposta.status_code == 302
    assert f"/pedido/{criado['token']}" in resposta.headers["Location"]
    mock_link.assert_not_called()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "pago"  # nunca mexeu


def test_reativar_pix_token_desconhecido_404(client):
    resposta = client.get("/pedido/token-que-nao-existe/reativar-pix")
    assert resposta.status_code == 404


def test_reativar_pix_ja_reativado_gera_outro_link_sem_recancelar(client):
    """2o clique no mesmo link (o pedido ja esta´ "pendente" de novo) --
    ainda funciona, so gera outro link, sem tentar reativar de novo."""
    token = _criar_e_cancelar(client)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/1"}):
        client.get(f"/pedido/{token}/reativar-pix")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/2"}) as mock_link:
        resposta = client.get(f"/pedido/{token}/reativar-pix")

    assert resposta.headers["Location"] == "https://checkout.infinitepay.io/2"
    assert mock_link.call_count == 1
    assert pedidos.obter_pedido(token)["status"] == "pendente"


# ---- reativar via boleto ----

def test_reativar_boleto_reativa_e_salva_dados(client):
    token = _criar_e_cancelar(client)

    with patch("app.emitir_boleto", return_value={"codigo_solicitacao": "abc-uuid"}), \
         patch("app.consultar_cobranca", return_value={
             "boleto": {"linhaDigitavel": "123456", "codigoBarras": "789"},
             "pix": {"pixCopiaECola": "00020126..."},
         }):
        resposta = client.get(f"/pedido/{token}/reativar-boleto")

    assert resposta.status_code == 302
    assert f"/pedido/{token}" in resposta.headers["Location"]

    pedido = pedidos.obter_pedido(token)
    assert pedido["status"] == "pendente"
    assert pedido["inter_codigo_solicitacao"] == "abc-uuid"
    assert pedido["inter_linha_digitavel"] == "123456"


def test_reativar_boleto_pedido_ja_pago_nao_emite_nada(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    pedidos.marcar_pago(criado["token"], forma_pagamento="pix", parcelas=None, valor_pago=78.65, transaction_nsu="tx")

    with patch("app.emitir_boleto") as mock_boleto:
        resposta = client.get(f"/pedido/{criado['token']}/reativar-boleto")

    assert resposta.status_code == 302
    mock_boleto.assert_not_called()


def test_reativar_boleto_ja_emitido_nao_emite_de_novo(client):
    token = _criar_e_cancelar(client)
    with patch("app.emitir_boleto", return_value={"codigo_solicitacao": "abc-uuid"}), \
         patch("app.consultar_cobranca", return_value={"boleto": {}, "pix": {}}):
        client.get(f"/pedido/{token}/reativar-boleto")

    with patch("app.emitir_boleto") as mock_boleto2:
        resposta = client.get(f"/pedido/{token}/reativar-boleto")

    assert resposta.status_code == 302
    mock_boleto2.assert_not_called()
