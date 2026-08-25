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
        cliente={"nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "12345678900",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def test_criar_pedido_com_link_mockado(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}) as mock_link:
        resposta = client.post("/api/pedido/criar", json=_corpo_valido())
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["url"] == "https://checkout.infinitepay.io/abc"
    assert len(dados["token"]) > 20
    assert len(dados["codigo"]) == 6

    corpo_infinitepay = mock_link.call_args.kwargs
    assert corpo_infinitepay["order_nsu"] == dados["token"]
    # subtotal (10x R$5,00 = R$50) + frete R$10 = 1 item de produto + 1 de frete
    descricoes = [item["description"] for item in corpo_infinitepay["itens_pagamento"]]
    assert "Correios PAC — R$ 10,00" in descricoes
    assert any("São José" in d for d in descricoes)


def test_criar_pedido_carrinho_vazio_400(client):
    resposta = client.post("/api/pedido/criar", json=_corpo_valido(itens=[]))
    assert resposta.status_code == 400


def test_criar_pedido_abaixo_do_minimo_400(client):
    resposta = client.post("/api/pedido/criar", json=_corpo_valido(
        itens=[{"chave_preco": "16mm", "quantidade": 1, "produtoNome": "São José"}]
    ))
    assert resposta.status_code == 400


def test_criar_pedido_sem_frete_400(client):
    resposta = client.post("/api/pedido/criar", json=_corpo_valido(frete={}))
    assert resposta.status_code == 400


def test_criar_pedido_sem_cliente_400(client):
    resposta = client.post("/api/pedido/criar", json=_corpo_valido(cliente={"nome": "Maria"}))
    assert resposta.status_code == 400


def test_criar_pedido_sem_endereco_400(client):
    resposta = client.post("/api/pedido/criar", json=_corpo_valido(endereco={"cep": "59000000"}))
    assert resposta.status_code == 400


def test_criar_pedido_erro_da_infinitepay_502(client):
    with patch("app.criar_link_pagamento", return_value={"erro": "falhou"}):
        resposta = client.post("/api/pedido/criar", json=_corpo_valido())
    assert resposta.status_code == 502


def test_pagina_de_pedido_mostra_status_pendente(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    pagina = client.get(f"/pedido/{criado['token']}")
    assert pagina.status_code == 200
    corpo = pagina.get_data(as_text=True)
    assert criado["codigo"] in corpo
    assert "Aguardando confirmação" in corpo


def test_pagina_de_pedido_inexistente_404(client):
    resposta = client.get("/pedido/token-que-nao-existe")
    assert resposta.status_code == 404


def test_webhook_confirma_pagamento_e_pedido_passa_a_pago(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    resposta_webhook = client.post(
        "/webhook/infinitepay",
        json={
            "order_nsu": criado["token"],
            "amount": 6000,
            "paid_amount": 6000,  # R$50 (produtos) + R$10 (frete) = R$60 -> 6000 centavos
            "capture_method": "pix",
            "installments": None,
            "transaction_nsu": "tx-abc",
        },
    )
    assert resposta_webhook.status_code == 200

    pagina = client.get(f"/pedido/{criado['token']}")
    corpo = pagina.get_data(as_text=True)
    assert "Pagamento confirmado" in corpo


def test_webhook_valor_insuficiente_nao_confirma(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    resposta_webhook = client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 100, "capture_method": "pix"},
    )
    assert resposta_webhook.status_code == 200

    pagina = client.get(f"/pedido/{criado['token']}")
    assert "Aguardando confirmação" in pagina.get_data(as_text=True)


def test_webhook_pedido_desconhecido_404(client):
    resposta = client.post("/webhook/infinitepay", json={"order_nsu": "nao-existe", "paid_amount": 100})
    assert resposta.status_code == 404


def test_webhook_confirmado_sincroniza_com_a_tiny_uma_vez(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    corpo_webhook = {
        "order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix", "transaction_nsu": "tx-abc",
    }
    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 42, "id": 7}) as mock_tiny:
        client.post("/webhook/infinitepay", json=corpo_webhook)
        # webhook repetido (comum em integracoes de pagamento) nao deve
        # sincronizar com a Tiny de novo
        client.post("/webhook/infinitepay", json=corpo_webhook)

    assert mock_tiny.call_count == 1

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["tiny_sincronizado"] == 1
    assert pedido["tiny_numero_pedido"] == "42"


def test_webhook_falha_na_tiny_nao_impede_confirmacao_do_pagamento(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.criar_pedido_tiny", return_value={"erro": "CPF inválido"}):
        resposta_webhook = client.post(
            "/webhook/infinitepay",
            json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
        )
    assert resposta_webhook.status_code == 200

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "pago"
    assert pedido["tiny_sincronizado"] == 1
    assert pedido["tiny_erro"] == "CPF inválido"


def test_webhook_confirmado_envia_email_uma_vez(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    corpo_webhook = {"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"}
    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 1}), \
         patch("app.enviar_confirmacao_pedido", return_value={"ok": True}) as mock_email:
        client.post("/webhook/infinitepay", json=corpo_webhook)
        client.post("/webhook/infinitepay", json=corpo_webhook)

    assert mock_email.call_count == 1
    url_enviada = mock_email.call_args.args[1]
    assert criado["token"] in url_enviada

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_enviado"] == 1


def test_webhook_falha_no_email_nao_impede_confirmacao_do_pagamento(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 1}), \
         patch("app.enviar_confirmacao_pedido", return_value={"erro": "falha no envio"}):
        resposta_webhook = client.post(
            "/webhook/infinitepay",
            json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
        )
    assert resposta_webhook.status_code == 200

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "pago"
    assert pedido["email_enviado"] == 1
    assert pedido["email_erro"] == "falha no envio"


def test_webhook_e_idempotente_nao_reprocessa(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    corpo_webhook = {
        "order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix", "transaction_nsu": "primeiro",
    }
    client.post("/webhook/infinitepay", json=corpo_webhook)
    client.post("/webhook/infinitepay", json={**corpo_webhook, "transaction_nsu": "segundo"})

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["transaction_nsu"] == "primeiro"
