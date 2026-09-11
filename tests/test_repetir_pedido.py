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


def test_itens_repetiveis_ignora_personalizada_sem_imagem(client):
    """Sem imagem NENHUMA guardada (nem o placeholder "sem foto"), nao
    tem o que reconstruir -- unico caso de personalizada que continua
    de fora."""
    token = _criar(client, itens=[
        {"chave_preco": "16mm", "quantidade": 10},  # sem produtoId nem imagem -- personalizada incompleta
    ])
    pedido = pedidos.obter_pedido(token)
    assert app_module._itens_repetiveis_do_pedido(pedido) == []


def test_itens_repetiveis_inclui_personalizada_de_1_lado_com_imagem(client):
    """A foto/recorte de peca personalizada fica guardada de forma
    duravel (SQLite) desde a criacao do pedido -- entao da´ pra
    reconstruir o item de carrinho igualzinho, sem passar pelo
    simulador de novo (ver conversa: pedido que so tinha
    personalizados com foto ficava sem o botao de repetir)."""
    token = _criar(client, itens=[
        {"chave_preco": "entremeio", "quantidade": 10, "cor": "ouro_velho",
         "imagem": "/imagem-personalizada/abc123", "imagemRecorte": "/imagem-personalizada/def456"},
    ])
    pedido = pedidos.obter_pedido(token)
    itens = app_module._itens_repetiveis_do_pedido(pedido)
    assert len(itens) == 1
    item = itens[0]
    assert item["tipo"] == "personalizada"
    assert item["duasFaces"] is False
    assert item["formato"] == "entremeio"
    assert item["cor"] == "ouro_velho"
    assert item["imagem"] == "/imagem-personalizada/abc123"
    assert item["imagemRecorte"] == "/imagem-personalizada/def456"
    assert item["quantidade"] == 10


def test_itens_repetiveis_ignora_2lados_sem_imagem(client):
    """Combo antigo/incompleto sem imagem guardada nos lados (so
    produtoNome, que e´ so cosmetico) continua de fora -- nao tem foto
    real pra reconstruir."""
    token = _criar(client, itens=[
        {"chave_preco": "medalha_2lados", "quantidade": 5, "cor": "prata", "tamanho": "14mm", "duasFaces": True,
         "lado1": {"produtoNome": "São José"}, "lado2": {"produtoNome": "Santa Rita"}},
    ])
    pedido = pedidos.obter_pedido(token)
    assert app_module._itens_repetiveis_do_pedido(pedido) == []


def test_itens_repetiveis_inclui_2lados_com_imagens(client):
    """Mesma logica da personalizada de 1 lado, mas os 2 lados tem foto
    propria guardada -- pedido do usuario: cliente que sempre repete
    varios entremeios/medalhas de 2 lados consegue montar o proximo
    pedido com 1 clique."""
    token = _criar(client, itens=[
        {"chave_preco": "medalha_2lados", "quantidade": 5, "cor": "prata", "tamanho": "14mm", "duasFaces": True,
         "lado1": {"imagem": "/imagem-personalizada/lado1-preview", "imagemRecorte": "/imagem-personalizada/lado1-crop"},
         "lado2": {"imagem": "/imagem-personalizada/lado2-preview", "imagemRecorte": "/imagem-personalizada/lado2-crop"}},
    ])
    pedido = pedidos.obter_pedido(token)
    itens = app_module._itens_repetiveis_do_pedido(pedido)
    assert len(itens) == 1
    item = itens[0]
    assert item["tipo"] == "personalizada"
    assert item["duasFaces"] is True
    assert item["formato"] == "medalha_2lados"
    assert item["chave_preco"] == "medalha_2lados"
    assert item["cor"] == "prata"
    assert item["tamanho"] == "14mm"
    assert item["imagemLado1"] == "/imagem-personalizada/lado1-preview"
    assert item["imagemRecorteLado1"] == "/imagem-personalizada/lado1-crop"
    assert item["imagemLado2"] == "/imagem-personalizada/lado2-preview"
    assert item["imagemRecorteLado2"] == "/imagem-personalizada/lado2-crop"
    assert item["quantidade"] == 5


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


def test_pagina_do_pedido_sem_botao_repetir_quando_personalizada_sem_imagem(client):
    token = _criar(client, itens=[{"chave_preco": "16mm", "quantidade": 10}])
    pagina = client.get(f"/pedido/{token}").get_data(as_text=True)
    assert '"btn-repetir-pedido"' not in pagina  # o botao em si (o script referencia o id de qualquer jeito)


def test_pagina_do_pedido_mostra_botao_repetir_quando_so_tem_personalizada_com_foto(client):
    """Pedido do usuario: testou um pedido que so tinha personalizados
    com foto e o link de acompanhamento nao tinha o botao de repetir
    ainda -- confirma que isso ficou coberto."""
    token = _criar(client, itens=[
        {"chave_preco": "16mm", "quantidade": 10, "imagem": "/imagem-personalizada/abc123"},
    ])
    pagina = client.get(f"/pedido/{token}").get_data(as_text=True)
    assert "btn-repetir-pedido" in pagina
    assert "/imagem-personalizada/abc123" in pagina


def test_pagina_do_pedido_mostra_botao_repetir_com_item_de_2lados_com_foto(client):
    token = _criar(client, itens=[
        {"chave_preco": "entremeio_2lados", "quantidade": 10, "cor": "prata", "duasFaces": True,
         "lado1": {"imagem": "/imagem-personalizada/lado1"}, "lado2": {"imagem": "/imagem-personalizada/lado2"}},
    ])
    pagina = client.get(f"/pedido/{token}").get_data(as_text=True)
    assert "btn-repetir-pedido" in pagina
    assert "/imagem-personalizada/lado1" in pagina
    assert "/imagem-personalizada/lado2" in pagina


def test_pagina_do_pedido_avisa_quando_so_parte_do_pedido_repete(client):
    token = _criar(client, itens=[
        {"chave_preco": "16mm", "quantidade": 10, "produtoId": "sao-jose", "produtoNome": "São José"},
        {"chave_preco": "16mm", "quantidade": 10},  # personalizada sem imagem -- fica de fora
    ])
    pagina = client.get(f"/pedido/{token}").get_data(as_text=True)
    assert "btn-repetir-pedido" in pagina
    assert "não entraram" in pagina
