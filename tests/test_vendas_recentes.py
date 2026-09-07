from __future__ import annotations

import pytest

import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _pedido_exemplo(**overrides):
    base = dict(
        itens=[{"chave_preco": "16mm", "quantidade": 30, "produtoId": "sao-jose"}],
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


def _vender(quantidade: int, produto_id: str = "sao-jose") -> None:
    criado = pedidos.criar_pedido(**_pedido_exemplo(
        itens=[{"chave_preco": "16mm", "quantidade": quantidade, "produtoId": produto_id}],
    ))
    pedidos.marcar_pago(criado["token"], forma_pagamento="pix", parcelas=None, valor_pago=100.0, transaction_nsu="tx")


def test_catalogo_sem_vendas_suficientes_nao_mostra_selo(client):
    """Ver conversa: numero baixo pareceria pouco procurado -- so vale
    mostrar quando bate o minimo (config.py:
    VENDAS_RECENTES_MINIMO_PARA_EXIBIR, 10 por padrao)."""
    _vender(5)
    pagina = client.get("/catalogo").get_data(as_text=True)
    assert "badge-vendas" not in pagina


def test_catalogo_mostra_selo_quando_bate_o_minimo(client):
    _vender(12)
    pagina = client.get("/catalogo").get_data(as_text=True)
    assert "badge-vendas" in pagina
    assert "12 vendidas nos últimos 30 dias" in pagina


def test_catalogo_soma_varias_vendas_do_mesmo_produto(client):
    _vender(6)
    _vender(7)
    pagina = client.get("/catalogo").get_data(as_text=True)
    assert "13 vendidas nos últimos 30 dias" in pagina


def test_venda_antiga_fora_da_janela_nao_conta(client):
    from datetime import datetime, timedelta, timezone

    criado = pedidos.criar_pedido(**_pedido_exemplo(
        itens=[{"chave_preco": "16mm", "quantidade": 50, "produtoId": "sao-jose"}],
    ))
    pedidos.marcar_pago(criado["token"], forma_pagamento="pix", parcelas=None, valor_pago=100.0, transaction_nsu="tx")
    with pedidos._conexao() as conexao:
        ha_40_dias = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        conexao.execute("UPDATE pedidos SET pago_em = ? WHERE token = ?", (ha_40_dias, criado["token"]))

    pagina = client.get("/catalogo").get_data(as_text=True)
    assert "badge-vendas" not in pagina


def test_venda_de_item_sem_produtoid_personalizada_nao_gera_selo(client):
    """Item de personalizada (sem produtoId proprio, ver conversa) nao
    tem como virar selo em nenhum card."""
    criado = pedidos.criar_pedido(**_pedido_exemplo(
        itens=[{"chave_preco": "medalha_2lados", "quantidade": 50}],
    ))
    pedidos.marcar_pago(criado["token"], forma_pagamento="pix", parcelas=None, valor_pago=100.0, transaction_nsu="tx")

    pagina = client.get("/catalogo").get_data(as_text=True)
    assert "badge-vendas" not in pagina
