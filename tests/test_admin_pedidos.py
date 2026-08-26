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
