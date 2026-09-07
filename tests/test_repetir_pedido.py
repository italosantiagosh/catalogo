from __future__ import annotations

from unittest.mock import patch

import pytest

import app as app_module
import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _corpo_valido(**overrides):
    base = dict(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "produtoId": "sao-jose",
                "produtoNome": "São José", "modeloId": "modelo-1", "modeloNome": "Modelo 1"}],
        frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0},
        cliente={"nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "11144477735",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def _criar(client, **overrides) -> str:
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido(**overrides)).get_json()
    return criado["token"]


def test_itens_repetiveis_inclui_item_de_catalogo_com_produtoid(client):
    token = _criar(client)
    pedido = pedidos.obter_pedido(token)
    itens = app_module._itens_repetiveis_do_pedido(pedido)
    assert len(itens) == 1
    assert itens[0]["produtoId"] == "sao-jose"
    assert itens[0]["formato"] == "medalha"
    assert itens[0]["tamanho"] == "16mm"
    assert itens[0]["quantidade"] == 10


def test_itens_repetiveis_ignora_item_personalizado_sem_produtoid(client):
    token = _criar(client, itens=[
        {"chave_preco": "16mm", "quantidade": 10},  # sem produtoId -- personalizada
    ])
    pedido = pedidos.obter_pedido(token)
    assert app_module._itens_repetiveis_do_pedido(pedido) == []


def test_itens_repetiveis_ignora_item_de_2_lados(client):
    token = _criar(client, itens=[
        {"chave_preco": "medalha_2lados", "quantidade": 5, "cor": "prata", "tamanho": "14mm", "duasFaces": True,
         "lado1": {"produtoNome": "São José"}, "lado2": {"produtoNome": "Santa Rita"}},
    ])
    pedido = pedidos.obter_pedido(token)
    assert app_module._itens_repetiveis_do_pedido(pedido) == []


def test_itens_repetiveis_deriva_formato_entremeio_e_chaveiro(client):
    token = _criar(client, itens=[
        {"chave_preco": "entremeio", "quantidade": 3, "produtoId": "sao-jose", "cor": "prata"},
        {"chave_preco": "chaveiro", "quantidade": 2, "produtoId": "sao-jose"},
    ])
    pedido = pedidos.obter_pedido(token)
    itens = app_module._itens_repetiveis_do_pedido(pedido)
    formatos = {i["chave_preco"]: i["formato"] for i in itens}
    assert formatos == {"entremeio": "entremeio", "chaveiro": "chaveiro"}


def test_pagina_do_pedido_mostra_botao_repetir_quando_tem_item_de_catalogo(client):
    token = _criar(client)
    pagina = client.get(f"/pedido/{token}").get_data(as_text=True)
    assert "btn-repetir-pedido" in pagina
    assert "sao-jose" in pagina


def test_pagina_do_pedido_sem_botao_repetir_quando_so_tem_personalizada(client):
    token = _criar(client, itens=[{"chave_preco": "16mm", "quantidade": 10}])
    pagina = client.get(f"/pedido/{token}").get_data(as_text=True)
    assert '"btn-repetir-pedido"' not in pagina  # o botao em si (o script referencia o id de qualquer jeito)


def test_pagina_do_pedido_avisa_quando_so_parte_do_pedido_repete(client):
    token = _criar(client, itens=[
        {"chave_preco": "16mm", "quantidade": 10, "produtoId": "sao-jose", "produtoNome": "São José"},
        {"chave_preco": "16mm", "quantidade": 10},  # personalizada, sem produtoId
    ])
    pagina = client.get(f"/pedido/{token}").get_data(as_text=True)
    assert "btn-repetir-pedido" in pagina
    assert "não entram" in pagina
