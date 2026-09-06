from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import services.pedidos as pedidos
from app import app, _enviar_seguimento_avaliacao_entregues


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _corpo_valido(**overrides):
    base = dict(
        itens=[{
            "chave_preco": "16mm", "quantidade": 10, "produtoNome": "Anunciação", "produtoId": "anunciacao",
            "modeloNome": "Modelo 1",
        }],
        frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0},
        cliente={"nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "11144477735",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def _preparar_admin(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")


def _entregar_e_envelhecer(token: str, dias: int) -> None:
    pedidos.atualizar_status(token, "entregue")
    passado = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with pedidos._conexao() as conexao:
        conexao.execute("UPDATE pedidos SET entregue_em = ? WHERE token = ?", (passado, token))


# ---- 1o e-mail: na hora que o status vira "entregue" ----

def test_marcar_entregue_dispara_email_de_avaliacao_na_hora(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    pedidos.marcar_pago(criado["token"], forma_pagamento="pix", parcelas=None, valor_pago=1.0, transaction_nsu="tx")
    pedidos.atualizar_status(criado["token"], "faturado")
    pedidos.atualizar_status(criado["token"], "enviado")

    with patch("app.enviar_pedido_avaliacao", return_value={"ok": True}) as mock_email:
        resposta = client.post(
            f"/admin/pedidos/{criado['token']}/status", data={"status": "entregue"},
            auth=("admin", "segredo123"),
        )
    assert resposta.status_code == 302
    assert mock_email.call_count == 1
    url_avaliar = mock_email.call_args.args[1]
    assert "/avaliar" in url_avaliar

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_avaliacao_enviado"] == 1


def test_marcar_entregue_de_novo_nao_reenvia(client, monkeypatch):
    """Reenviar o mesmo formulario de status (sem mudar de "entregue"
    pra "entregue") nao deve mandar o e-mail de novo."""
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    pedidos.marcar_pago(criado["token"], forma_pagamento="pix", parcelas=None, valor_pago=1.0, transaction_nsu="tx")

    with patch("app.enviar_pedido_avaliacao", return_value={"ok": True}):
        client.post(
            f"/admin/pedidos/{criado['token']}/status", data={"status": "entregue"},
            auth=("admin", "segredo123"),
        )
    with patch("app.enviar_pedido_avaliacao") as mock_email2:
        client.post(
            f"/admin/pedidos/{criado['token']}/status", data={"status": "entregue"},
            auth=("admin", "segredo123"),
        )
    mock_email2.assert_not_called()


def test_pedido_sem_produto_no_catalogo_ainda_recebe_email_do_link_geral(client, monkeypatch):
    """O link de avaliacao agora e´ a pagina geral /avaliar (o cliente
    escolhe o produto na hora), entao mesmo um pedido so´ de peca
    personalizada (sem produtoId) recebe o e-mail normalmente."""
    _preparar_admin(monkeypatch)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post(
            "/api/pedido/criar",
            json=_corpo_valido(itens=[
                {"chave_preco": "16mm", "quantidade": 10, "produtoNome": "Personalizada"}
            ]),
        ).get_json()
    pedidos.marcar_pago(criado["token"], forma_pagamento="pix", parcelas=None, valor_pago=1.0, transaction_nsu="tx")

    with patch("app.enviar_pedido_avaliacao", return_value={"ok": True}) as mock_email:
        client.post(
            f"/admin/pedidos/{criado['token']}/status", data={"status": "entregue"},
            auth=("admin", "segredo123"),
        )
    assert mock_email.call_count == 1
    assert "/avaliar" in mock_email.call_args.args[1]

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_avaliacao_enviado"] == 1


# ---- 2o e-mail (seguimento): N dias depois da entrega ----

def test_sem_canonical_domain_nao_faz_nada(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "")
    with patch("app.enviar_pedido_avaliacao") as mock_email:
        _enviar_seguimento_avaliacao_entregues()
    mock_email.assert_not_called()


def test_manda_seguimento_e_marca_uma_vez(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _entregar_e_envelhecer(criado["token"], 8)

    with patch("app.enviar_pedido_avaliacao", return_value={"ok": True}) as mock_email:
        _enviar_seguimento_avaliacao_entregues()

    assert mock_email.call_count == 1
    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_avaliacao_seguimento_enviado"] == 1

    # rodar de novo nao deve mandar duas vezes
    with patch("app.enviar_pedido_avaliacao") as mock_email2:
        _enviar_seguimento_avaliacao_entregues()
    mock_email2.assert_not_called()


def test_entrega_recente_ainda_nao_recebe_seguimento(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _entregar_e_envelhecer(criado["token"], 2)

    with patch("app.enviar_pedido_avaliacao") as mock_email:
        _enviar_seguimento_avaliacao_entregues()
    mock_email.assert_not_called()
