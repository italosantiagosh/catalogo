from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import services.pedidos as pedidos
from app import app, _cancelar_pedidos_abandonados


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _corpo_valido(**overrides):
    base = dict(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"}],
        frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0},
        cliente={"nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "12345678900",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def _marcar_lembrete_antigo(token: str, minutos: int) -> None:
    passado = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
    with pedidos._conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_lembrete_enviado = 1, email_lembrete_enviado_em = ? WHERE token = ?",
            (passado, token),
        )


def test_sem_canonical_domain_nao_faz_nada(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "")
    with patch("app.enviar_pedido_cancelado") as mock_email:
        _cancelar_pedidos_abandonados()
    mock_email.assert_not_called()


def test_cancela_e_manda_email_uma_vez(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _marcar_lembrete_antigo(criado["token"], 40)

    with patch("app.enviar_pedido_cancelado", return_value={"ok": True}) as mock_email:
        _cancelar_pedidos_abandonados()

    assert mock_email.call_count == 1
    url_catalogo = mock_email.call_args.args[1]
    assert "/catalogo" in url_catalogo

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "cancelado"
    assert pedido["cancelado_em"]
    assert pedido["email_cancelado_enviado"] == 1

    # rodar de novo nao deve cancelar/mandar de novo (ja nao esta mais pendente)
    with patch("app.enviar_pedido_cancelado") as mock_email2:
        _cancelar_pedidos_abandonados()
    mock_email2.assert_not_called()


def test_pedido_sem_lembrete_nao_e_cancelado(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.enviar_pedido_cancelado") as mock_email:
        _cancelar_pedidos_abandonados()
    mock_email.assert_not_called()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "pendente"


def test_lembrete_recente_nao_e_cancelado(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _marcar_lembrete_antigo(criado["token"], 5)

    with patch("app.enviar_pedido_cancelado") as mock_email:
        _cancelar_pedidos_abandonados()
    mock_email.assert_not_called()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "pendente"


def test_pedido_ja_pago_nao_e_cancelado(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _marcar_lembrete_antigo(criado["token"], 40)
    pedidos.marcar_pago(
        criado["token"], forma_pagamento="pix", parcelas=None, valor_pago=100.0, transaction_nsu="123"
    )

    with patch("app.enviar_pedido_cancelado") as mock_email:
        _cancelar_pedidos_abandonados()
    mock_email.assert_not_called()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "pago"
