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
    assert corpo_infinitepay["redirect_url"].endswith(f"/pedido/{dados['token']}?obrigado=1")


def test_item_medalha_guarda_tamanho_na_descricao_e_detalhe(client):
    corpo = _corpo_valido(itens=[{
        "chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1",
        "formato": "medalha", "tamanho": "16mm", "imagem": "/static/img/produtos/sao-jose-1.jpg",
    }])
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    pedido = pedidos.obter_pedido(criado["token"])
    item = pedido["itens"][0]
    assert item["detalhe"] == "Medalha · 1,6 cm"
    assert "1,6 cm" in item["descricao"]
    assert item["imagem"] == "/static/img/produtos/sao-jose-1.jpg"


def test_item_entremeio_guarda_cor_na_descricao_e_detalhe(client):
    corpo = _corpo_valido(itens=[{
        "chave_preco": "entremeio", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1",
        "formato": "entremeio", "cor": "ouro_velho",
    }])
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    pedido = pedidos.obter_pedido(criado["token"])
    item = pedido["itens"][0]
    assert item["detalhe"] == "Entremeio · Ouro velho"
    assert "Ouro velho" in item["descricao"]
    assert item["cor"] == "ouro_velho"


def test_item_chaveiro_detalhe_simples(client):
    corpo = _corpo_valido(itens=[{
        "chave_preco": "chaveiro", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1",
        "formato": "chaveiro",
    }])
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["itens"][0]["detalhe"] == "Chaveiro"


def test_admin_csv_exige_autenticacao(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    resposta = client.get(f"/admin/pedidos/{criado['token']}/csv")
    assert resposta.status_code == 401


def test_admin_csv_conteudo(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    corpo = _corpo_valido(itens=[{
        "chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1",
        "formato": "medalha", "tamanho": "16mm",
    }])
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    resposta = client.get(f"/admin/pedidos/{criado['token']}/csv", auth=("admin", "segredo123"))
    assert resposta.status_code == 200
    assert resposta.mimetype == "text/csv"
    corpo_csv = resposta.get_data().decode("utf-8-sig")
    assert "Produto;Modelo;Variação;Quantidade" in corpo_csv
    assert "São José;Modelo 1;Medalha · 1,6 cm;10" in corpo_csv


def test_criar_pedido_envia_email_com_link_uma_vez(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}), \
         patch("app.enviar_link_pagamento", return_value={"ok": True}) as mock_email:
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    assert mock_email.call_count == 1
    url_pagamento_enviada = mock_email.call_args.args[1]
    assert url_pagamento_enviada == "https://checkout.infinitepay.io/abc"

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_pedido_criado_enviado"] == 1


def test_criar_pedido_com_erro_no_email_nao_impede_criacao(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}), \
         patch("app.enviar_link_pagamento", return_value={"erro": "falha no envio"}):
        resposta = client.post("/api/pedido/criar", json=_corpo_valido())
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["url"] == "https://checkout.infinitepay.io/abc"

    pedido = pedidos.obter_pedido(dados["token"])
    assert pedido["email_pedido_criado_erro"] == "falha no envio"


def test_novo_link_gera_outro_link_pro_pedido_pendente(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/primeiro"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/segundo"}) as mock_link:
        resposta = client.post(f"/api/pedido/{criado['token']}/novo-link")
    assert resposta.status_code == 200
    assert resposta.get_json()["url"] == "https://checkout.infinitepay.io/segundo"
    assert mock_link.call_args.kwargs["order_nsu"] == criado["token"]


def test_novo_link_pedido_inexistente_404(client):
    resposta = client.post("/api/pedido/token-que-nao-existe/novo-link")
    assert resposta.status_code == 404


def test_novo_link_pedido_ja_pago_400(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    with patch("app.criar_pedido_tiny", return_value={"erro": "não configurado"}), \
         patch("app.enviar_confirmacao_pedido", return_value={"erro": "não configurado"}):
        client.post(
            "/webhook/infinitepay",
            json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
        )

    resposta = client.post(f"/api/pedido/{criado['token']}/novo-link")
    assert resposta.status_code == 400


def test_criar_pedido_com_destinatario_diferente(client):
    corpo = _corpo_valido(endereco={
        "cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
        "bairro": "Centro", "cidade": "Natal", "uf": "RN",
        "destinatario_nome": "Ana Coordenadora", "destinatario_tipo_pessoa": "fisica",
        "destinatario_documento": "98765432100",
    })
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()
    assert criado.get("token")

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["endereco_destinatario_nome"] == "Ana Coordenadora"
    assert pedido["endereco_destinatario_tipo_pessoa"] == "fisica"
    assert pedido["endereco_destinatario_documento"] == "98765432100"

    pagina = client.get(f"/pedido/{criado['token']}")
    assert "Ana Coordenadora" in pagina.get_data(as_text=True)


def test_criar_pedido_sem_destinatario_fica_vazio(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["endereco_destinatario_nome"] == ""


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


def test_obrigado_aparece_so_com_query_param_e_pedido_pago(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix", "transaction_nsu": "tx-abc"},
    )

    com_param = client.get(f"/pedido/{criado['token']}?obrigado=1").get_data(as_text=True)
    assert "Obrigado pela sua compra!" in com_param

    sem_param = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "Obrigado pela sua compra!" not in sem_param


def test_obrigado_nao_aparece_se_pedido_nao_esta_pago(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    corpo = client.get(f"/pedido/{criado['token']}?obrigado=1").get_data(as_text=True)
    assert "Obrigado pela sua compra!" not in corpo


def test_webhook_confirma_pagamento_dispara_notificacao_de_venda_uma_vez(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    corpo_webhook = {
        "order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix", "transaction_nsu": "tx-abc",
    }
    with patch("app.enviar_notificacao_venda", return_value={"ok": True}) as mock_notificacao:
        client.post("/webhook/infinitepay", json=corpo_webhook)
        # webhook repetido nao deve notificar de novo
        client.post("/webhook/infinitepay", json=corpo_webhook)

    assert mock_notificacao.call_count == 1
    assert mock_notificacao.call_args.args[0]["codigo"] == criado["codigo"]


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
