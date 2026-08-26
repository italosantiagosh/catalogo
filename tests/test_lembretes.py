from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import services.pedidos as pedidos
from app import app, _enviar_lembretes_pedidos_pendentes


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


def _envelhecer(token: str, minutos: int) -> None:
    passado = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
    with pedidos._conexao() as conexao:
        conexao.execute("UPDATE pedidos SET criado_em = ? WHERE token = ?", (passado, token))


def test_sem_canonical_domain_nao_faz_nada(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "")
    with patch("app.enviar_lembrete_pedido_pendente") as mock_email:
        _enviar_lembretes_pedidos_pendentes()
    mock_email.assert_not_called()


def test_manda_lembrete_pro_pedido_antigo_e_marca_uma_vez(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/original"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _envelhecer(criado["token"], 40)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/novo"}) as mock_link, \
         patch("app.enviar_lembrete_pedido_pendente", return_value={"ok": True}) as mock_email:
        _enviar_lembretes_pedidos_pendentes()

    assert mock_link.call_count == 1
    assert mock_email.call_count == 1
    url_enviada = mock_email.call_args.args[1]
    assert url_enviada == "https://checkout.infinitepay.io/novo"

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_lembrete_enviado"] == 1

    # rodar de novo nao deve mandar duas vezes
    with patch("app.criar_link_pagamento") as mock_link2, \
         patch("app.enviar_lembrete_pedido_pendente") as mock_email2:
        _enviar_lembretes_pedidos_pendentes()
    mock_link2.assert_not_called()
    mock_email2.assert_not_called()


def test_pedido_recente_nao_recebe_lembrete(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        client.post("/api/pedido/criar", json=_corpo_valido())

    with patch("app.enviar_lembrete_pedido_pendente") as mock_email:
        _enviar_lembretes_pedidos_pendentes()
    mock_email.assert_not_called()


def test_falha_ao_gerar_link_marca_erro_sem_mandar_email(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _envelhecer(criado["token"], 40)

    with patch("app.criar_link_pagamento", return_value={"erro": "InfinitePay fora do ar"}), \
         patch("app.enviar_lembrete_pedido_pendente") as mock_email:
        _enviar_lembretes_pedidos_pendentes()
    mock_email.assert_not_called()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_lembrete_enviado"] == 1
    assert pedido["email_lembrete_erro"] == "InfinitePay fora do ar"
