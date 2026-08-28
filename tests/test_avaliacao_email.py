from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import services.pedidos as pedidos
from app import app, _enviar_pedidos_para_avaliacao


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


def _pagar_e_envelhecer(token: str, dias: int) -> None:
    pedidos.marcar_pago(token, forma_pagamento="pix", parcelas=None, valor_pago=1.0, transaction_nsu="tx-abc")
    passado = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with pedidos._conexao() as conexao:
        conexao.execute("UPDATE pedidos SET pago_em = ? WHERE token = ?", (passado, token))


def test_sem_canonical_domain_nao_faz_nada(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "")
    with patch("app.enviar_pedido_avaliacao") as mock_email:
        _enviar_pedidos_para_avaliacao()
    mock_email.assert_not_called()


def test_manda_pedido_de_avaliacao_e_marca_uma_vez(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _pagar_e_envelhecer(criado["token"], 31)

    with patch("app.enviar_pedido_avaliacao", return_value={"ok": True}) as mock_email:
        _enviar_pedidos_para_avaliacao()

    assert mock_email.call_count == 1
    produto_nome = mock_email.call_args.args[1]
    url_produto = mock_email.call_args.args[2]
    assert produto_nome == "Anunciação"
    assert "/produto/anunciacao" in url_produto
    assert url_produto.endswith("#avaliacoes")

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_avaliacao_enviado"] == 1

    # rodar de novo nao deve mandar duas vezes
    with patch("app.enviar_pedido_avaliacao") as mock_email2:
        _enviar_pedidos_para_avaliacao()
    mock_email2.assert_not_called()


def test_pedido_recente_ainda_nao_recebe_pedido_de_avaliacao(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _pagar_e_envelhecer(criado["token"], 2)

    with patch("app.enviar_pedido_avaliacao") as mock_email:
        _enviar_pedidos_para_avaliacao()
    mock_email.assert_not_called()


def test_pedido_sem_produto_valido_marca_processado_sem_email(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post(
            "/api/pedido/criar",
            json=_corpo_valido(itens=[
                {"chave_preco": "16mm", "quantidade": 10, "produtoNome": "Personalizada"}
            ]),
        ).get_json()
    _pagar_e_envelhecer(criado["token"], 31)

    with patch("app.enviar_pedido_avaliacao") as mock_email:
        _enviar_pedidos_para_avaliacao()
    mock_email.assert_not_called()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_avaliacao_enviado"] == 1


def test_pedido_enviado_tambem_recebe_pedido_de_avaliacao(client, monkeypatch):
    """Nao precisa continuar 'pago' -- se ja avancou pro fluxo (faturado/
    enviado/entregue) antes dos dias passarem, ainda conta."""
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _pagar_e_envelhecer(criado["token"], 31)
    pedidos.atualizar_status(criado["token"], "faturado")

    with patch("app.enviar_pedido_avaliacao", return_value={"ok": True}) as mock_email:
        _enviar_pedidos_para_avaliacao()
    assert mock_email.call_count == 1
