from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import services.pedidos as pedidos
from app import app, _enviar_upsell_pedidos_pagos


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


def _pagar_e_envelhecer(token: str, horas: int) -> None:
    """Marca pago direto via services.pedidos (nao passa pelo webhook,
    que rejeitaria paid_amount que nao bate com o total real do
    pedido) e joga pago_em pro passado, simulando um pedido pago ha´
    `horas` horas."""
    pedidos.marcar_pago(token, forma_pagamento="pix", parcelas=None, valor_pago=1.0, transaction_nsu="tx-abc")
    passado = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()
    with pedidos._conexao() as conexao:
        conexao.execute("UPDATE pedidos SET pago_em = ? WHERE token = ?", (passado, token))


def test_sem_canonical_domain_nao_faz_nada(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "")
    with patch("app.enviar_oportunidade_upsell") as mock_email:
        _enviar_upsell_pedidos_pagos()
    mock_email.assert_not_called()


def test_manda_oportunidade_pro_pedido_antigo_e_marca_uma_vez(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _pagar_e_envelhecer(criado["token"], 30)

    with patch("app.enviar_oportunidade_upsell", return_value={"ok": True}) as mock_email:
        _enviar_upsell_pedidos_pagos()

    assert mock_email.call_count == 1
    oportunidades = mock_email.call_args.args[1]
    assert oportunidades[0]["label"] == "medalhas/entremeios"
    assert oportunidades[0]["faltam"] == 10
    assert oportunidades[0]["preco"] == 4.5

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_upsell_enviado"] == 1

    # rodar de novo nao deve mandar duas vezes
    with patch("app.enviar_oportunidade_upsell") as mock_email2:
        _enviar_upsell_pedidos_pagos()
    mock_email2.assert_not_called()


def test_pedido_ja_na_melhor_faixa_nao_manda_email_mas_marca_processado(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post(
            "/api/pedido/criar",
            json=_corpo_valido(itens=[
                {"chave_preco": "16mm", "quantidade": 2000, "produtoNome": "São José", "modeloNome": "Modelo 1"}
            ]),
        ).get_json()
    _pagar_e_envelhecer(criado["token"], 30)

    with patch("app.enviar_oportunidade_upsell") as mock_email:
        _enviar_upsell_pedidos_pagos()
    mock_email.assert_not_called()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_upsell_enviado"] == 1


def test_pedido_recente_nao_recebe_oportunidade_ainda(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix", "transaction_nsu": "tx-abc"},
    )

    with patch("app.enviar_oportunidade_upsell") as mock_email:
        _enviar_upsell_pedidos_pagos()
    mock_email.assert_not_called()


def test_pagina_de_obrigado_mostra_oportunidade(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix", "transaction_nsu": "tx-abc"},
    )

    corpo = client.get(f"/pedido/{criado['token']}?obrigado=1").get_data(as_text=True)
    assert "Uma dica pro seu próximo pedido" in corpo
    assert "medalhas/entremeios" in corpo
