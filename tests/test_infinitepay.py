from __future__ import annotations

from unittest.mock import Mock, patch

import services.infinitepay as infinitepay


def _chamada_exemplo(**overrides):
    base = dict(
        order_nsu="token123",
        redirect_url="https://atacado.lojanovedejulho.com.br/pedido/token123",
        webhook_url="https://atacado.lojanovedejulho.com.br/webhook/infinitepay",
        itens_pagamento=[{"id": "16mm", "description": "São José", "quantity": 30, "price": 400}],
        cliente={"nome": "Maria", "email": "maria@example.com", "telefone": "84999999999", "documento": "12345678900"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def test_criar_link_pagamento_sem_handle_devolve_erro(monkeypatch):
    monkeypatch.setattr(infinitepay, "INFINITEPAY_HANDLE", "")
    resultado = infinitepay.criar_link_pagamento(**_chamada_exemplo())
    assert "erro" in resultado


def test_criar_link_pagamento_monta_payload_correto(monkeypatch):
    monkeypatch.setattr(infinitepay, "INFINITEPAY_HANDLE", "novedejulho")
    monkeypatch.setattr(infinitepay, "INFINITEPAY_API_TOKEN", "")
    resposta_mock = Mock()
    resposta_mock.json.return_value = {"url": "https://checkout.infinitepay.io/abc"}
    resposta_mock.raise_for_status = Mock()
    with patch("services.infinitepay.requests.post", return_value=resposta_mock) as post_mock:
        resultado = infinitepay.criar_link_pagamento(**_chamada_exemplo())

    assert resultado == {"url": "https://checkout.infinitepay.io/abc"}
    corpo_enviado = post_mock.call_args.kwargs["json"]
    assert corpo_enviado["handle"] == "novedejulho"
    assert corpo_enviado["order_nsu"] == "token123"
    assert corpo_enviado["items"][0]["price"] == 400
    assert corpo_enviado["customer"]["email"] == "maria@example.com"
    assert "Authorization" not in post_mock.call_args.kwargs["headers"]


def test_criar_link_pagamento_manda_bearer_token_quando_configurado(monkeypatch):
    monkeypatch.setattr(infinitepay, "INFINITEPAY_HANDLE", "novedejulho")
    monkeypatch.setattr(infinitepay, "INFINITEPAY_API_TOKEN", "segredo123")
    resposta_mock = Mock()
    resposta_mock.json.return_value = {"url": "https://checkout.infinitepay.io/abc"}
    resposta_mock.raise_for_status = Mock()
    with patch("services.infinitepay.requests.post", return_value=resposta_mock) as post_mock:
        infinitepay.criar_link_pagamento(**_chamada_exemplo())

    assert post_mock.call_args.kwargs["headers"]["Authorization"] == "Bearer segredo123"


def test_criar_link_pagamento_resposta_sem_url_e_erro(monkeypatch):
    monkeypatch.setattr(infinitepay, "INFINITEPAY_HANDLE", "novedejulho")
    resposta_mock = Mock()
    resposta_mock.json.return_value = {"algo_inesperado": True}
    resposta_mock.raise_for_status = Mock()
    with patch("services.infinitepay.requests.post", return_value=resposta_mock):
        resultado = infinitepay.criar_link_pagamento(**_chamada_exemplo())
    assert "erro" in resultado


def test_criar_link_pagamento_erro_de_rede(monkeypatch):
    import requests

    monkeypatch.setattr(infinitepay, "INFINITEPAY_HANDLE", "novedejulho")
    with patch("services.infinitepay.requests.post", side_effect=requests.RequestException("timeout")):
        resultado = infinitepay.criar_link_pagamento(**_chamada_exemplo())
    assert "erro" in resultado
