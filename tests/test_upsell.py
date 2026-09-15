from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import services.carrinhos_abandonados as carrinhos_abandonados
import services.pedidos as pedidos
from app import app, _enviar_upsell_pedidos_pagos


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(pedidos, "DB_PATH", db_path)
    monkeypatch.setattr(carrinhos_abandonados, "DB_PATH", db_path)
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


def test_pedido_com_12_entremeios_sem_cruz_recebe_oportunidade_e_marca_uma_vez(client, monkeypatch):
    """Ver conversa "upsell de cruz durante producao": cruz e´ peca
    pronta, da´ pra somar ao pedido ainda em producao -- so oferece pra
    quem comprou bastante entremeio (>= UPSELL_ENTREMEIOS_MINIMO) e
    ainda nao tem cruz nenhuma no pedido."""
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "UPSELL_ENTREMEIOS_MINIMO", 12)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post(
            "/api/pedido/criar",
            json=_corpo_valido(itens=[
                {"chave_preco": "entremeio", "quantidade": 12, "produtoNome": "São José", "modeloNome": "Modelo 1"},
            ]),
        ).get_json()
    _pagar_e_envelhecer(criado["token"], 30)

    with patch("app.enviar_oportunidade_upsell", return_value={"ok": True}) as mock_email:
        _enviar_upsell_pedidos_pagos()

    assert mock_email.call_count == 1
    assert mock_email.call_args.args[1] == 12  # quantidade_entremeios

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_upsell_enviado"] == 1

    # rodar de novo nao deve mandar duas vezes
    with patch("app.enviar_oportunidade_upsell") as mock_email2:
        _enviar_upsell_pedidos_pagos()
    mock_email2.assert_not_called()


def test_pedido_com_menos_de_12_entremeios_nao_recebe_mas_marca_processado(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "UPSELL_ENTREMEIOS_MINIMO", 12)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post(
            "/api/pedido/criar",
            json=_corpo_valido(itens=[
                {"chave_preco": "entremeio", "quantidade": 11, "produtoNome": "São José", "modeloNome": "Modelo 1"},
            ]),
        ).get_json()
    _pagar_e_envelhecer(criado["token"], 30)

    with patch("app.enviar_oportunidade_upsell") as mock_email:
        _enviar_upsell_pedidos_pagos()
    mock_email.assert_not_called()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_upsell_enviado"] == 1


def test_pedido_com_cruz_nao_recebe_mesmo_com_bastante_entremeio(client, monkeypatch):
    """Ja tem cruz -- nao ha´ nada pra "completar", nao faz sentido
    oferecer de novo."""
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "UPSELL_ENTREMEIOS_MINIMO", 12)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post(
            "/api/pedido/criar",
            json=_corpo_valido(itens=[
                {"chave_preco": "entremeio", "quantidade": 12, "produtoNome": "São José", "modeloNome": "Modelo 1"},
                {"chave_preco": "cruz_terco_prata", "quantidade": 1, "produtoNome": "Cruz"},
            ]),
        ).get_json()
    _pagar_e_envelhecer(criado["token"], 30)

    with patch("app.enviar_oportunidade_upsell") as mock_email:
        _enviar_upsell_pedidos_pagos()
    mock_email.assert_not_called()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_upsell_enviado"] == 1


def test_medalha_sozinha_nao_recebe_upsell_de_cruz(client, monkeypatch):
    """Pedido sem nenhum entremeio (so medalha) nunca se qualifica --
    nao tem o que "completar" com cruz."""
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _pagar_e_envelhecer(criado["token"], 30)

    with patch("app.enviar_oportunidade_upsell") as mock_email:
        _enviar_upsell_pedidos_pagos()
    mock_email.assert_not_called()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_upsell_enviado"] == 1


def test_entremeio_2lados_soma_junto_pro_minimo(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "UPSELL_ENTREMEIOS_MINIMO", 12)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post(
            "/api/pedido/criar",
            json=_corpo_valido(itens=[
                {"chave_preco": "entremeio", "quantidade": 8, "produtoNome": "São José", "modeloNome": "Modelo 1"},
                {"chave_preco": "entremeio_2lados", "quantidade": 4, "produtoNome": "Personalizada"},
            ]),
        ).get_json()
    _pagar_e_envelhecer(criado["token"], 30)

    with patch("app.enviar_oportunidade_upsell", return_value={"ok": True}) as mock_email:
        _enviar_upsell_pedidos_pagos()

    assert mock_email.call_count == 1
    assert mock_email.call_args.args[1] == 12


def test_pedido_recente_nao_recebe_oportunidade_ainda(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "UPSELL_ENTREMEIOS_MINIMO", 12)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post(
            "/api/pedido/criar",
            json=_corpo_valido(itens=[
                {"chave_preco": "entremeio", "quantidade": 12, "produtoNome": "São José", "modeloNome": "Modelo 1"},
            ]),
        ).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix", "transaction_nsu": "tx-abc"},
    )

    with patch("app.enviar_oportunidade_upsell") as mock_email:
        _enviar_upsell_pedidos_pagos()
    mock_email.assert_not_called()


def test_pagina_de_obrigado_mostra_oportunidade(client):
    """Nudge de faixa de atacado na pagina de obrigado -- NAO mudou,
    continua usando _oportunidades_upsell_do_pedido direto (so o
    e-mail agendado mudou de logica, ver testes acima)."""
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix", "transaction_nsu": "tx-abc"},
    )

    corpo = client.get(f"/pedido/{criado['token']}?obrigado=1").get_data(as_text=True)
    assert "Uma dica pro seu próximo pedido" in corpo
    assert "medalhas/entremeios" in corpo
