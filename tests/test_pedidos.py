from __future__ import annotations

import services.pedidos as pedidos


def _reapontar_db(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))


def _pedido_exemplo(**overrides):
    base = dict(
        itens=[{"chave_preco": "16mm", "quantidade": 30, "descricao": "São José — Modelo 1"}],
        subtotal=120.0,
        frete_descricao="Correios PAC — R$ 20,00",
        frete_preco=20.0,
        cliente={"nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "12345678900",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def test_criar_pedido_gera_token_longo_e_codigo_curto_diferentes(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    assert len(pedido["token"]) > 20  # token de URL -- longo, nao adivinhavel
    assert len(pedido["codigo"]) == 6  # codigo curto, so pra exibicao humana
    assert pedido["token"] != pedido["codigo"]
    assert pedido["status"] == "pendente"


def test_criar_pedido_soma_total_como_subtotal_mais_frete(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo(subtotal=120.0, frete_preco=20.0))
    assert pedido["total"] == 140.0


def test_obter_pedido_inexistente_devolve_none(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    assert pedidos.obter_pedido("token-que-nao-existe") is None


def test_obter_pedido_preserva_itens_como_lista(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    criado = pedidos.criar_pedido(**_pedido_exemplo())
    lido = pedidos.obter_pedido(criado["token"])
    assert lido["itens"] == [{"chave_preco": "16mm", "quantidade": 30, "descricao": "São José — Modelo 1"}]


def test_marcar_pago_atualiza_status_e_dados_do_pagamento(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    atualizado = pedidos.marcar_pago(
        pedido["token"], forma_pagamento="pix", parcelas=None, valor_pago=140.0, transaction_nsu="abc123"
    )
    assert atualizado["status"] == "pago"
    assert atualizado["forma_pagamento"] == "pix"
    assert atualizado["valor_pago"] == 140.0
    assert atualizado["transaction_nsu"] == "abc123"
    assert atualizado["pago_em"] is not None


def test_marcar_pago_e_idempotente_nao_reprocessa_webhook_repetido(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    primeiro = pedidos.marcar_pago(
        pedido["token"], forma_pagamento="pix", parcelas=None, valor_pago=140.0, transaction_nsu="abc123"
    )
    # segunda chamada com dados diferentes -- nao deve sobrescrever o
    # primeiro pagamento ja confirmado (webhook duplicado e comum)
    segundo = pedidos.marcar_pago(
        pedido["token"], forma_pagamento="credit_card", parcelas=3, valor_pago=999.0, transaction_nsu="outro"
    )
    assert segundo["forma_pagamento"] == "pix"
    assert segundo["transaction_nsu"] == "abc123"
    assert segundo["pago_em"] == primeiro["pago_em"]


def test_marcar_pago_pedido_inexistente_devolve_none(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    resultado = pedidos.marcar_pago(
        "token-que-nao-existe", forma_pagamento="pix", parcelas=None, valor_pago=10.0, transaction_nsu="x"
    )
    assert resultado is None
