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


def test_sem_credenciais_configuradas_bloqueia_mesmo_com_login_certo(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "")
    resposta = client.get("/admin/pedidos", auth=("qualquer", "coisa"))
    assert resposta.status_code == 401


def test_sem_autenticacao_devolve_401(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    resposta = client.get("/admin/pedidos")
    assert resposta.status_code == 401
    assert "Basic" in resposta.headers.get("WWW-Authenticate", "")


def test_credenciais_erradas_devolve_401(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    resposta = client.get("/admin/pedidos", auth=("admin", "senha-errada"))
    assert resposta.status_code == 401


def test_credenciais_certas_lista_pedidos(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    resposta = client.get("/admin/pedidos", auth=("admin", "segredo123"))
    assert resposta.status_code == 200
    corpo = resposta.get_data(as_text=True)
    assert criado["codigo"] in corpo
    assert "Maria Teste" in corpo


def test_filtro_por_status(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        pendente = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
        pago = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.criar_pedido_tiny", return_value={"erro": "não configurado"}), \
         patch("app.enviar_confirmacao_pedido", return_value={"erro": "não configurado"}):
        client.post(
            "/webhook/infinitepay",
            json={"order_nsu": pago["token"], "paid_amount": 6000, "capture_method": "pix"},
        )

    resposta_pagos = client.get("/admin/pedidos?status=pago", auth=("admin", "segredo123"))
    corpo_pagos = resposta_pagos.get_data(as_text=True)
    assert pago["codigo"] in corpo_pagos
    assert pendente["codigo"] not in corpo_pagos

    resposta_pendentes = client.get("/admin/pedidos?status=pendente", auth=("admin", "segredo123"))
    corpo_pendentes = resposta_pendentes.get_data(as_text=True)
    assert pendente["codigo"] in corpo_pendentes
    assert pago["codigo"] not in corpo_pendentes


def test_sem_pedidos_mostra_mensagem_vazia(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    resposta = client.get("/admin/pedidos", auth=("admin", "segredo123"))
    assert "Nenhum pedido ainda." in resposta.get_data(as_text=True)


def _preparar_admin(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")


def test_detalhe_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    resposta = client.get(f"/admin/pedidos/{criado['token']}")
    assert resposta.status_code == 401


def test_detalhe_pedido_inexistente_404(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.get("/admin/pedidos/token-que-nao-existe", auth=("admin", "segredo123"))
    assert resposta.status_code == 404


def test_detalhe_mostra_dados_do_pedido(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    resposta = client.get(f"/admin/pedidos/{criado['token']}", auth=("admin", "segredo123"))
    assert resposta.status_code == 200
    assert "Maria Teste" in resposta.get_data(as_text=True)


def test_alterar_status_para_faturado(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    resposta = client.post(
        f"/admin/pedidos/{criado['token']}/status", data={"status": "faturado"}, auth=("admin", "segredo123")
    )
    assert resposta.status_code == 302

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "faturado"


def test_alterar_status_para_enviado_dispara_email_uma_vez(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.enviar_pedido_enviado", return_value={"ok": True}) as mock_email:
        client.post(
            f"/admin/pedidos/{criado['token']}/status",
            data={"status": "enviado", "codigo_rastreio": "BR123456789BR", "link_rastreio": "https://rastreio.exemplo/BR123"},
            auth=("admin", "segredo123"),
        )
    assert mock_email.call_count == 1
    assert mock_email.call_args.args[1] == "BR123456789BR"
    assert mock_email.call_args.args[2] == "https://rastreio.exemplo/BR123"

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "enviado"
    assert pedido["codigo_rastreio"] == "BR123456789BR"

    # reenviar o mesmo status (ex: form reenviado) nao dispara o e-mail de novo
    with patch("app.enviar_pedido_enviado") as mock_email2:
        client.post(
            f"/admin/pedidos/{criado['token']}/status",
            data={"status": "enviado", "codigo_rastreio": "BR123456789BR"},
            auth=("admin", "segredo123"),
        )
    mock_email2.assert_not_called()


def test_alterar_status_para_enviado_salva_e_envia_transportadora(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.enviar_pedido_enviado", return_value={"ok": True}) as mock_email:
        client.post(
            f"/admin/pedidos/{criado['token']}/status",
            data={
                "status": "enviado",
                "transportadora": "Correios",
                "codigo_rastreio": "BR123456789BR",
                "link_rastreio": "https://rastreio.exemplo/BR123",
            },
            auth=("admin", "segredo123"),
        )
    assert mock_email.call_args.args[4] == "Correios"

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["transportadora"] == "Correios"


def test_alterar_status_para_faturado_salva_link_da_nota_fiscal(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    resposta = client.post(
        f"/admin/pedidos/{criado['token']}/status",
        data={"status": "faturado", "link_nota_fiscal": "https://tiny.exemplo/nf/123.pdf"},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "faturado"
    assert pedido["link_nota_fiscal"] == "https://tiny.exemplo/nf/123.pdf"

    detalhe = client.get(f"/admin/pedidos/{criado['token']}", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "https://tiny.exemplo/nf/123.pdf" in detalhe

    pagina_cliente = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "https://tiny.exemplo/nf/123.pdf" in pagina_cliente
    assert "Baixar nota fiscal" in pagina_cliente


def test_alterar_status_para_faturado_sem_link_nao_mostra_botao_de_nota(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    client.post(
        f"/admin/pedidos/{criado['token']}/status", data={"status": "faturado"}, auth=("admin", "segredo123")
    )

    pagina_cliente = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "Baixar nota fiscal" not in pagina_cliente


def _criar_lead_whatsapp(client, **overrides):
    corpo = {
        "itens": [{"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"}],
        "frete": {},
    }
    corpo.update(overrides)
    return client.post("/api/pedido/criar-whatsapp", json=corpo).get_json()


def test_painel_lista_leads_do_whatsapp_separados(client, monkeypatch):
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)

    resposta = client.get("/admin/pedidos?status=whatsapp", auth=("admin", "segredo123"))
    corpo = resposta.get_data(as_text=True)
    assert lead["codigo"] in corpo

    detalhe = client.get(f"/admin/pedidos/{lead['token']}", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "Confirmar venda" in detalhe
    assert "Alterar status" not in detalhe


def test_confirmar_venda_manual_promove_lead_pra_pago(client, monkeypatch):
    """Ver conversa: admin preenche os dados na mao quando a venda
    combinada no WhatsApp realmente fecha -- a partir dai o pedido
    segue o fluxo normal (Tiny, e-mail, timeline)."""
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)

    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 55, "id": 1}) as mock_tiny, \
         patch("app.enviar_confirmacao_pedido", return_value={"ok": True}), \
         patch("app.enviar_notificacao_venda", return_value={"ok": True}), \
         patch("app.enviar_notificacao_push", return_value={"ok": True}):
        resposta = client.post(
            f"/admin/pedidos/{lead['token']}/confirmar-venda",
            data={
                "cliente_nome": "Maria Teste", "cliente_documento": "12345678900",
                "cliente_telefone": "84999999999", "cliente_email": "maria@example.com",
                "endereco_cep": "59000000", "endereco_logradouro": "Rua Teste", "endereco_numero": "100",
                "endereco_bairro": "Centro", "endereco_cidade": "Natal", "endereco_uf": "RN",
                "frete_descricao": "Combinado no WhatsApp", "frete_preco": "15,00",
                "forma_pagamento": "Pix", "valor_pago": "65,00",
            },
            auth=("admin", "segredo123"),
        )
    assert resposta.status_code == 302
    assert mock_tiny.call_count == 1

    pedido = pedidos.obter_pedido(lead["token"])
    assert pedido["status"] == "pago"
    assert pedido["cliente_nome"] == "Maria Teste"
    assert pedido["endereco_cidade"] == "Natal"
    assert pedido["frete_preco"] == 15.0
    assert pedido["forma_pagamento"] == "Pix"
    assert pedido["valor_pago"] == 65.0
    assert pedido["tiny_sincronizado"] == 1


def test_confirmar_venda_sem_nome_400(client, monkeypatch):
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)
    resposta = client.post(
        f"/admin/pedidos/{lead['token']}/confirmar-venda", data={}, auth=("admin", "segredo123")
    )
    assert resposta.status_code == 400


def test_confirmar_venda_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)
    resposta = client.post(
        f"/admin/pedidos/{lead['token']}/confirmar-venda", data={"cliente_nome": "Maria"}
    )
    assert resposta.status_code == 401


def test_descartar_lead_whatsapp_vira_cancelado(client, monkeypatch):
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)

    resposta = client.post(
        f"/admin/pedidos/{lead['token']}/descartar-whatsapp", auth=("admin", "segredo123")
    )
    assert resposta.status_code == 302

    pedido = pedidos.obter_pedido(lead["token"])
    assert pedido["status"] == "cancelado"


def test_reenviar_tiny_manualmente(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    with patch("app.criar_pedido_tiny", return_value={"erro": "Tiny fora do ar"}), \
         patch("app.enviar_confirmacao_pedido", return_value={"ok": True}):
        client.post(
            "/webhook/infinitepay",
            json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
        )
    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["tiny_erro"] == "Tiny fora do ar"

    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 99, "id": 1}) as mock_tiny:
        resposta = client.post(
            f"/admin/pedidos/{criado['token']}/reenviar-tiny", auth=("admin", "segredo123")
        )
    assert resposta.status_code == 302
    assert mock_tiny.call_count == 1

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["tiny_erro"] is None
    assert pedido["tiny_numero_pedido"] == "99"


def test_reenviar_tiny_com_excecao_inesperada_nao_500(client, monkeypatch):
    """Se criar_pedido_tiny estourar uma excecao nao prevista (ex: o bug
    real do formato de registros da Tiny), o operador nunca deve cair
    numa tela de Internal Server Error -- o erro fica registrado no
    pedido e a pagina redireciona normalmente."""
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    with patch("app.criar_pedido_tiny", return_value={"ok": True}), \
         patch("app.enviar_confirmacao_pedido", return_value={"ok": True}):
        client.post(
            "/webhook/infinitepay",
            json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
        )

    with patch("app.criar_pedido_tiny", side_effect=KeyError(0)):
        resposta = client.post(
            f"/admin/pedidos/{criado['token']}/reenviar-tiny", auth=("admin", "segredo123")
        )
    assert resposta.status_code == 302

    pedido = pedidos.obter_pedido(criado["token"])
    assert "Erro inesperado" in pedido["tiny_erro"]


def test_reenviar_tiny_exige_pedido_pago(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    resposta = client.post(f"/admin/pedidos/{criado['token']}/reenviar-tiny", auth=("admin", "segredo123"))
    assert resposta.status_code == 400


def test_reenviar_tiny_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    resposta = client.post(f"/admin/pedidos/{criado['token']}/reenviar-tiny")
    assert resposta.status_code == 401


def test_reenviar_email_manualmente(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    with patch("app.criar_pedido_tiny", return_value={"ok": True}), \
         patch("app.enviar_confirmacao_pedido", return_value={"erro": "IP não autorizado na Brevo"}):
        client.post(
            "/webhook/infinitepay",
            json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
        )
    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_erro"] == "IP não autorizado na Brevo"

    with patch("app.enviar_confirmacao_pedido", return_value={"ok": True}) as mock_email:
        resposta = client.post(
            f"/admin/pedidos/{criado['token']}/reenviar-email", auth=("admin", "segredo123")
        )
    assert resposta.status_code == 302
    assert mock_email.call_count == 1

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_erro"] is None


def test_reenviar_email_exige_pedido_nao_pendente(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    resposta = client.post(f"/admin/pedidos/{criado['token']}/reenviar-email", auth=("admin", "segredo123"))
    assert resposta.status_code == 400


def test_reenviar_email_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    resposta = client.post(f"/admin/pedidos/{criado['token']}/reenviar-email")
    assert resposta.status_code == 401


def test_alterar_status_invalido_400(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    resposta = client.post(
        f"/admin/pedidos/{criado['token']}/status", data={"status": "invalido"}, auth=("admin", "segredo123")
    )
    assert resposta.status_code == 400


def test_alterar_status_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    resposta = client.post(f"/admin/pedidos/{criado['token']}/status", data={"status": "faturado"})
    assert resposta.status_code == 401
