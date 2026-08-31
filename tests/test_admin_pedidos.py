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


def test_painel_mostra_estatisticas_de_hoje(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        pago = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    with patch("app.criar_pedido_tiny", return_value={"erro": "não configurado"}), \
         patch("app.enviar_confirmacao_pedido", return_value={"erro": "não configurado"}), \
         patch("app.enviar_notificacao_venda", return_value={"ok": True}), \
         patch("app.enviar_notificacao_push", return_value={"ok": True}):
        client.post(
            "/webhook/infinitepay",
            json={"order_nsu": pago["token"], "paid_amount": 6000, "capture_method": "pix"},
        )

    resposta = client.get("/admin/pedidos", auth=("admin", "segredo123"))
    corpo = resposta.get_data(as_text=True)
    assert "Pedidos hoje" in corpo
    assert "Faturado hoje (1 venda)" in corpo


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


def test_detalhe_telefone_e_link_clicavel_pro_whatsapp(client, monkeypatch):
    """Ver conversa: usuario quer poder clicar no telefone do cliente
    no painel pra abrir o WhatsApp direto, em vez de copiar o numero
    na mao."""
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    detalhe = client.get(f"/admin/pedidos/{criado['token']}", auth=("admin", "segredo123")).get_data(as_text=True)
    assert 'href="https://wa.me/5584999999999"' in detalhe


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


def test_alterar_status_para_enviado_registra_falha_no_email(client, monkeypatch):
    """Ate isso ser corrigido (ver conversa: usuario relatou que o
    painel nao mostrava nada sobre o e-mail de "enviado"), uma falha
    aqui era completamente invisivel -- sem try/except nem registro."""
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.enviar_pedido_enviado", return_value={"erro": "falha no envio"}):
        client.post(
            f"/admin/pedidos/{criado['token']}/status",
            data={"status": "enviado", "codigo_rastreio": "BR123456789BR"},
            auth=("admin", "segredo123"),
        )

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_pedido_enviado_enviado"] == 1
    assert pedido["email_pedido_enviado_erro"] == "falha no envio"

    detalhe = client.get(f"/admin/pedidos/{criado['token']}", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "falha no envio" in detalhe
    assert "E-mail de pedido enviado" in detalhe


def test_admin_reenvia_email_pedido_enviado(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    with patch("app.enviar_pedido_enviado", return_value={"erro": "falhou"}):
        client.post(
            f"/admin/pedidos/{criado['token']}/status",
            data={"status": "enviado", "codigo_rastreio": "BR123456789BR"},
            auth=("admin", "segredo123"),
        )

    with patch("app.enviar_pedido_enviado", return_value={"ok": True}) as mock_reenvio:
        resposta = client.post(
            f"/admin/pedidos/{criado['token']}/reenviar-email-enviado", auth=("admin", "segredo123")
        )
    assert resposta.status_code in (302, 303)
    mock_reenvio.assert_called_once()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_pedido_enviado_erro"] is None


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


def test_preencher_link_nota_fiscal_dispara_email_uma_vez(client, monkeypatch):
    """Ver conversa: "se eu preencher o link com a nota, mande e-mail"."""
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.enviar_nota_fiscal_disponivel", return_value={"ok": True}) as mock_email:
        client.post(
            f"/admin/pedidos/{criado['token']}/status",
            data={"status": "faturado", "link_nota_fiscal": "https://tiny.exemplo/nf/123.pdf"},
            auth=("admin", "segredo123"),
        )
    assert mock_email.call_count == 1

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_nota_fiscal_enviado"] == 1

    # corrigir o link depois (mesmo link ou outro) nao dispara de novo
    with patch("app.enviar_nota_fiscal_disponivel") as mock_email2:
        client.post(
            f"/admin/pedidos/{criado['token']}/status",
            data={"status": "faturado", "link_nota_fiscal": "https://tiny.exemplo/nf/123-corrigido.pdf"},
            auth=("admin", "segredo123"),
        )
    mock_email2.assert_not_called()


def test_admin_reenvia_email_nota_fiscal(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    with patch("app.enviar_nota_fiscal_disponivel", return_value={"erro": "falhou"}):
        client.post(
            f"/admin/pedidos/{criado['token']}/status",
            data={"status": "faturado", "link_nota_fiscal": "https://tiny.exemplo/nf/123.pdf"},
            auth=("admin", "segredo123"),
        )

    with patch("app.enviar_nota_fiscal_disponivel", return_value={"ok": True}) as mock_reenvio:
        resposta = client.post(
            f"/admin/pedidos/{criado['token']}/reenviar-email-nota-fiscal", auth=("admin", "segredo123")
        )
    assert resposta.status_code in (302, 303)
    mock_reenvio.assert_called_once()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_nota_fiscal_erro"] is None


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
                "cliente_nome": "Maria Teste", "cliente_documento": "11144477735",
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


def test_confirmar_venda_com_destinatario_diferente(client, monkeypatch):
    """Ver conversa: as vezes quem recebe e´ uma livraria, endereco
    diferente de quem fechou a compra."""
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)

    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 55, "id": 1}), \
         patch("app.enviar_confirmacao_pedido", return_value={"ok": True}), \
         patch("app.enviar_notificacao_venda", return_value={"ok": True}), \
         patch("app.enviar_notificacao_push", return_value={"ok": True}):
        resposta = client.post(
            f"/admin/pedidos/{lead['token']}/confirmar-venda",
            data={
                "cliente_nome": "Paróquia São José", "cliente_tipo_pessoa": "juridica",
                "cliente_documento": "11222333000181",
                "endereco_cep": "59000000", "endereco_logradouro": "Rua Teste", "endereco_numero": "100",
                "endereco_bairro": "Centro", "endereco_cidade": "Natal", "endereco_uf": "RN",
                "destinatario_nome": "Livraria Shalom", "destinatario_tipo_pessoa": "juridica",
                "destinatario_documento": "11222333000181",
                "destinatario_cep": "59100000", "destinatario_logradouro": "Av. Livraria",
                "destinatario_numero": "500", "destinatario_bairro": "Centro",
                "destinatario_cidade": "Natal", "destinatario_uf": "RN",
                "frete_descricao": "Combinado no WhatsApp", "frete_preco": "15,00",
                "forma_pagamento": "Pix", "valor_pago": "65,00",
            },
            auth=("admin", "segredo123"),
        )
    assert resposta.status_code == 302

    pedido = pedidos.obter_pedido(lead["token"])
    assert pedido["endereco_destinatario_nome"] == "Livraria Shalom"
    assert pedido["endereco_destinatario_logradouro"] == "Av. Livraria"
    assert pedido["endereco_destinatario_cidade"] == "Natal"
    # endereco principal (quem fechou a compra) continua guardado, sem sobrescrever
    assert pedido["endereco_logradouro"] == "Rua Teste"


def test_confirmar_venda_com_telefone_do_destinatario_aparece_clicavel(client, monkeypatch):
    """Ver conversa: telefone de quem recebe (opcional) tambem vira
    link clicavel de WhatsApp no painel, igual o telefone do cliente."""
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)

    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 55, "id": 1}), \
         patch("app.enviar_confirmacao_pedido", return_value={"ok": True}), \
         patch("app.enviar_notificacao_venda", return_value={"ok": True}), \
         patch("app.enviar_notificacao_push", return_value={"ok": True}):
        client.post(
            f"/admin/pedidos/{lead['token']}/confirmar-venda",
            data={
                "cliente_nome": "Paróquia São José", "cliente_tipo_pessoa": "juridica",
                "cliente_documento": "11222333000181",
                "endereco_cep": "59000000", "endereco_logradouro": "Rua Teste", "endereco_numero": "100",
                "endereco_bairro": "Centro", "endereco_cidade": "Natal", "endereco_uf": "RN",
                "destinatario_nome": "Livraria Shalom", "destinatario_tipo_pessoa": "juridica",
                "destinatario_documento": "11222333000181",
                "destinatario_telefone": "84988887777",
                "destinatario_cep": "59100000", "destinatario_logradouro": "Av. Livraria",
                "destinatario_numero": "500", "destinatario_bairro": "Centro",
                "destinatario_cidade": "Natal", "destinatario_uf": "RN",
                "frete_descricao": "Combinado no WhatsApp", "frete_preco": "15,00",
                "forma_pagamento": "Pix", "valor_pago": "65,00",
            },
            auth=("admin", "segredo123"),
        )

    pedido = pedidos.obter_pedido(lead["token"])
    assert pedido["endereco_destinatario_telefone"] == "84988887777"

    pagina = client.get(f"/admin/pedidos/{lead['token']}", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "https://wa.me/5584988887777" in pagina


def test_confirmar_venda_com_cpf_invalido_400(client, monkeypatch):
    """Ver conversa: usuaria pediu pra checar CPF/CNPJ/celular tambem
    no formulario do WhatsApp, mesma validacao do checkout do site."""
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)
    resposta = client.post(
        f"/admin/pedidos/{lead['token']}/confirmar-venda",
        data={"cliente_nome": "Maria Teste", "cliente_documento": "11111111111"},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400
    assert "CPF" in resposta.get_data(as_text=True)


def test_confirmar_venda_com_cnpj_invalido_400(client, monkeypatch):
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)
    resposta = client.post(
        f"/admin/pedidos/{lead['token']}/confirmar-venda",
        data={
            "cliente_nome": "Loja Teste", "cliente_tipo_pessoa": "juridica",
            "cliente_documento": "11222333000199",
        },
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400
    assert "CNPJ" in resposta.get_data(as_text=True)


def test_confirmar_venda_com_telefone_invalido_400(client, monkeypatch):
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)
    resposta = client.post(
        f"/admin/pedidos/{lead['token']}/confirmar-venda",
        data={"cliente_nome": "Maria Teste", "cliente_telefone": "123"},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400
    assert "Telefone" in resposta.get_data(as_text=True)


def test_confirmar_venda_com_destinatario_cnpj_invalido_400(client, monkeypatch):
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)
    resposta = client.post(
        f"/admin/pedidos/{lead['token']}/confirmar-venda",
        data={
            "cliente_nome": "Maria Teste",
            "destinatario_nome": "Livraria Shalom", "destinatario_tipo_pessoa": "juridica",
            "destinatario_documento": "11222333000199",
        },
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400
    assert "CNPJ" in resposta.get_data(as_text=True)


def test_confirmar_venda_com_cnpj_valido_e_ie_isento(client, monkeypatch):
    """Ver conversa: mesma logica de Inscricao Estadual/isento/nao
    contribuinte do checkout do site, agora disponivel no formulario
    manual de venda combinada no WhatsApp."""
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)

    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 55, "id": 1}), \
         patch("app.enviar_confirmacao_pedido", return_value={"ok": True}), \
         patch("app.enviar_notificacao_venda", return_value={"ok": True}), \
         patch("app.enviar_notificacao_push", return_value={"ok": True}):
        client.post(
            f"/admin/pedidos/{lead['token']}/confirmar-venda",
            data={
                "cliente_nome": "Loja Teste", "cliente_tipo_pessoa": "juridica",
                "cliente_documento": "11222333000181",
                "cliente_ie_isento": "on", "cliente_inscricao_estadual": "123456",  # deve ser ignorado, isento
                "endereco_cep": "59000000", "endereco_logradouro": "Rua Teste", "endereco_numero": "100",
                "endereco_bairro": "Centro", "endereco_cidade": "Natal", "endereco_uf": "RN",
                "frete_descricao": "Combinado no WhatsApp", "frete_preco": "15,00",
                "forma_pagamento": "Pix", "valor_pago": "65,00",
            },
            auth=("admin", "segredo123"),
        )

    pedido = pedidos.obter_pedido(lead["token"])
    assert pedido["cliente_ie_isento"] == 1
    assert pedido["cliente_inscricao_estadual"] == ""


def test_confirmar_venda_com_cnpj_valido_e_inscricao_estadual(client, monkeypatch):
    _preparar_admin(monkeypatch)
    lead = _criar_lead_whatsapp(client)

    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 55, "id": 1}), \
         patch("app.enviar_confirmacao_pedido", return_value={"ok": True}), \
         patch("app.enviar_notificacao_venda", return_value={"ok": True}), \
         patch("app.enviar_notificacao_push", return_value={"ok": True}):
        client.post(
            f"/admin/pedidos/{lead['token']}/confirmar-venda",
            data={
                "cliente_nome": "Loja Teste", "cliente_tipo_pessoa": "juridica",
                "cliente_documento": "11222333000181",
                "cliente_inscricao_estadual": "123.456.789", "cliente_ie_nao_contribuinte": "on",
                "endereco_cep": "59000000", "endereco_logradouro": "Rua Teste", "endereco_numero": "100",
                "endereco_bairro": "Centro", "endereco_cidade": "Natal", "endereco_uf": "RN",
                "frete_descricao": "Combinado no WhatsApp", "frete_preco": "15,00",
                "forma_pagamento": "Pix", "valor_pago": "65,00",
            },
            auth=("admin", "segredo123"),
        )

    pedido = pedidos.obter_pedido(lead["token"])
    assert pedido["cliente_inscricao_estadual"] == "123.456.789"
    assert pedido["cliente_ie_isento"] == 0
    assert pedido["cliente_ie_nao_contribuinte"] == 1


def test_admin_tiny_buscar_contato_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.get("/admin/tiny/buscar-contato?q=livraria")
    assert resposta.status_code == 401


def test_admin_tiny_buscar_contato_devolve_lista(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.buscar_contatos_tiny", return_value={"ok": True, "contatos": [{"nome": "Livraria Shalom"}]}):
        resposta = client.get("/admin/tiny/buscar-contato?q=shalom", auth=("admin", "segredo123"))
    assert resposta.status_code == 200
    assert resposta.get_json()["contatos"][0]["nome"] == "Livraria Shalom"


def test_admin_tiny_buscar_contato_erro_devolve_502(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.buscar_contatos_tiny", return_value={"erro": "Tiny fora do ar"}):
        resposta = client.get("/admin/tiny/buscar-contato?q=shalom", auth=("admin", "segredo123"))
    assert resposta.status_code == 502


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


def test_excluir_pedido_exige_motivo(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    resposta = client.post(
        f"/admin/pedidos/{criado['token']}/excluir", data={}, auth=("admin", "segredo123")
    )
    assert resposta.status_code == 400
    assert pedidos.obter_pedido(criado["token"])["status"] == "pendente"


def test_excluir_pedido_marca_status_e_avisa_cliente_por_email(client, monkeypatch):
    """Ver conversa: exclusao NUNCA apaga a linha de verdade -- so marca
    status="excluido" com o motivo, e avisa o cliente por e-mail."""
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.enviar_pedido_excluido", return_value={"ok": True}) as mock_email:
        resposta = client.post(
            f"/admin/pedidos/{criado['token']}/excluir",
            data={"motivo": "Item fora de estoque"},
            auth=("admin", "segredo123"),
        )
    assert resposta.status_code == 302
    assert mock_email.call_count == 1
    assert mock_email.call_args.args[1] == "Item fora de estoque"

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "excluido"
    assert pedido["excluido_motivo"] == "Item fora de estoque"
    assert pedido["excluido_em"] is not None

    # a pagina de acompanhamento do cliente continua funcionando (nao
    # foi apagado de verdade), mostrando o motivo
    pagina = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "Item fora de estoque" in pagina


def test_excluir_pedido_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    resposta = client.post(f"/admin/pedidos/{criado['token']}/excluir", data={"motivo": "teste"})
    assert resposta.status_code == 401


def test_excluir_pedido_inexistente_404(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/nao-existe/excluir", data={"motivo": "teste"}, auth=("admin", "segredo123")
    )
    assert resposta.status_code == 404


def _pagar_pedido(client, token):
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": token, "paid_amount": 6000, "capture_method": "pix"},
    )


def test_acao_em_massa_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post("/admin/pedidos/acao-em-massa", data={"tokens": ["x"], "acao": "tiny"})
    assert resposta.status_code == 401


def test_acao_em_massa_sincroniza_varios_com_tiny(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}), \
         patch("app.criar_pedido_tiny", return_value={"erro": "não configurado"}), \
         patch("app.enviar_confirmacao_pedido", return_value={"erro": "não configurado"}):
        p1 = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
        p2 = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
        _pagar_pedido(client, p1["token"])
        _pagar_pedido(client, p2["token"])

    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 77, "id": 1}) as mock_tiny:
        resposta = client.post(
            "/admin/pedidos/acao-em-massa",
            data={"tokens": [p1["token"], p2["token"]], "acao": "tiny"},
            auth=("admin", "segredo123"),
        )
    assert resposta.status_code == 302
    assert mock_tiny.call_count == 2
    assert pedidos.obter_pedido(p1["token"])["tiny_numero_pedido"] == "77"
    assert pedidos.obter_pedido(p2["token"])["tiny_numero_pedido"] == "77"


def test_acao_em_massa_muda_status_de_varios(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        p1 = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
        p2 = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
        _pagar_pedido(client, p1["token"])
        _pagar_pedido(client, p2["token"])

    resposta = client.post(
        "/admin/pedidos/acao-em-massa",
        data={"tokens": [p1["token"], p2["token"]], "acao": "status", "novo_status": "faturado"},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302
    assert pedidos.obter_pedido(p1["token"])["status"] == "faturado"
    assert pedidos.obter_pedido(p2["token"])["status"] == "faturado"


def test_acao_em_massa_excluir_exige_motivo(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    client.post(
        "/admin/pedidos/acao-em-massa",
        data={"tokens": [criado["token"]], "acao": "excluir", "motivo": ""},
        auth=("admin", "segredo123"),
    )
    assert pedidos.obter_pedido(criado["token"])["status"] == "pendente"


def test_acao_em_massa_excluir_varios_avisa_cada_cliente(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        p1 = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
        p2 = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.enviar_pedido_excluido", return_value={"ok": True}) as mock_email:
        resposta = client.post(
            "/admin/pedidos/acao-em-massa",
            data={"tokens": [p1["token"], p2["token"]], "acao": "excluir", "motivo": "Estoque zerado"},
            auth=("admin", "segredo123"),
        )
    assert resposta.status_code == 302
    assert mock_email.call_count == 2
    assert pedidos.obter_pedido(p1["token"])["status"] == "excluido"
    assert pedidos.obter_pedido(p2["token"])["status"] == "excluido"


def test_acao_em_massa_preserva_filtro_de_status_no_redirect(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    resposta = client.post(
        "/admin/pedidos/acao-em-massa",
        data={"tokens": [criado["token"]], "acao": "tiny", "status_filtro": "pendente"},
        auth=("admin", "segredo123"),
    )
    assert resposta.headers["Location"].endswith("status=pendente")


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
