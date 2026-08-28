from __future__ import annotations

from unittest.mock import Mock, patch

import services.email as email


def _pedido_exemplo(**overrides):
    base = dict(
        codigo="ABC123",
        itens=[{"chave_preco": "16mm", "quantidade": 10, "descricao": "São José — Modelo 1"}],
        subtotal=50.0,
        frete_descricao="Correios PAC — R$ 10,00",
        frete_preco=10.0,
        total=60.0,
        cliente_nome="Maria Teste",
        cliente_email="maria@example.com",
    )
    base.update(overrides)
    return base


def test_sem_api_key_devolve_erro(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "")
    resultado = email.enviar_confirmacao_pedido(_pedido_exemplo(), "https://site/pedido/token")
    assert "erro" in resultado


def test_pedido_sem_email_devolve_erro(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resultado = email.enviar_confirmacao_pedido(_pedido_exemplo(cliente_email=""), "https://site/pedido/token")
    assert "erro" in resultado


def test_envia_com_payload_correto(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "EMAIL_REMETENTE", "9djulho@gmail.com")
    monkeypatch.setattr(email, "EMAIL_REMETENTE_NOME", "Nove de Julho")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        resultado = email.enviar_confirmacao_pedido(_pedido_exemplo(), "https://site/pedido/token")

    assert resultado == {"ok": True}
    corpo = post_mock.call_args.kwargs["json"]
    assert corpo["sender"] == {"name": "Nove de Julho", "email": "9djulho@gmail.com"}
    assert corpo["to"] == [{"email": "maria@example.com", "name": "Maria Teste"}]
    assert "ABC123" in corpo["subject"]
    assert "https://site/pedido/token" in corpo["htmlContent"]
    assert "R$ 60,00" in corpo["htmlContent"]
    assert "produção" in corpo["htmlContent"]
    assert post_mock.call_args.kwargs["headers"]["api-key"] == "segredo"


def test_com_previsao_de_entrega_mostra_aviso_de_transportadora(monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    pedido = _pedido_exemplo(pago_em=datetime(2024, 11, 4, tzinfo=timezone.utc).isoformat(), frete_prazo_dias=7)
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(pedido, "https://site/pedido/token")

    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert "entrega prevista" in corpo
    assert "prazo de entrega é uma estimativa da transportadora" in corpo


def test_erro_de_rede(monkeypatch):
    import requests

    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    with patch("services.email.requests.post", side_effect=requests.RequestException("timeout")):
        resultado = email.enviar_confirmacao_pedido(_pedido_exemplo(), "https://site/pedido/token")
    assert "erro" in resultado


def test_link_pagamento_sem_api_key_devolve_erro(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "")
    resultado = email.enviar_link_pagamento(
        _pedido_exemplo(), "https://checkout.infinitepay.io/abc", "https://site/pedido/token"
    )
    assert "erro" in resultado


def test_link_pagamento_envia_com_payload_correto(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        resultado = email.enviar_link_pagamento(
            _pedido_exemplo(), "https://checkout.infinitepay.io/abc", "https://site/pedido/token"
        )

    assert resultado == {"ok": True}
    corpo = post_mock.call_args.kwargs["json"]
    assert "ABC123" in corpo["subject"]
    assert "https://checkout.infinitepay.io/abc" in corpo["htmlContent"]
    assert "https://site/pedido/token" in corpo["htmlContent"]


def test_link_de_acompanhamento_e_um_botao_nao_link_cru(monkeypatch):
    """Ver conversa: link repetido como texto cru pesa mal em filtro de
    spam e passa despercebido no celular -- vira um botao com fundo."""
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(_pedido_exemplo(), "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert "background-color:#14335c" in corpo
    assert "Clique aqui e acompanhe" in corpo
    assert corpo.count("https://site/pedido/token") == 1  # nao repete a URL como texto visivel


def test_lembrete_sem_api_key_devolve_erro(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "")
    resultado = email.enviar_lembrete_pedido_pendente(
        _pedido_exemplo(), "https://checkout.infinitepay.io/novo", "https://site/pedido/token"
    )
    assert "erro" in resultado


def test_lembrete_envia_com_payload_correto(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        resultado = email.enviar_lembrete_pedido_pendente(
            _pedido_exemplo(), "https://checkout.infinitepay.io/novo", "https://site/pedido/token"
        )

    assert resultado == {"ok": True}
    corpo = post_mock.call_args.kwargs["json"]
    assert "ainda não foi pago" in corpo["subject"]
    assert "https://checkout.infinitepay.io/novo" in corpo["htmlContent"]


def test_pedido_enviado_com_link_de_rastreio(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        resultado = email.enviar_pedido_enviado(
            _pedido_exemplo(), "BR123456789BR", "https://rastreio.exemplo/BR123", "https://site/pedido/token"
        )

    assert resultado == {"ok": True}
    corpo = post_mock.call_args.kwargs["json"]
    assert "enviado" in corpo["subject"].lower()
    assert "BR123456789BR" in corpo["htmlContent"]
    assert "https://rastreio.exemplo/BR123" in corpo["htmlContent"]


def test_pedido_enviado_sem_link_de_rastreio(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_pedido_enviado(_pedido_exemplo(), "BR123456789BR", "", "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]
    assert "BR123456789BR" in corpo["htmlContent"]
