from __future__ import annotations

import pytest

import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _preparar_admin(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")


def test_form_exige_autenticacao(client):
    resposta = client.get("/admin/pedidos/novo-manual")
    assert resposta.status_code == 401


def test_form_mostra_pagina_quando_autenticado(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.get("/admin/pedidos/novo-manual", auth=("admin", "segredo123"))
    assert resposta.status_code == 200
    assert "Registrar pedido manual".encode() in resposta.data


def test_criar_exige_autenticacao(client):
    resposta = client.post("/admin/pedidos/novo-manual", data={})
    assert resposta.status_code == 401


def test_cria_pedido_abaixo_do_minimo_sem_bloquear(client, monkeypatch):
    """ver conversa: pedido negociado de R$ 28,00, abaixo do mínimo de
    R$ 30 do checkout normal -- o admin precisa conseguir registrar
    mesmo assim."""
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Medalha São José 12mm"], "quantidade": ["4"], "valor_unitario": ["7,00"]},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302
    token = resposta.headers["Location"].rsplit("/", 1)[-1]
    pedido = pedidos.obter_pedido(token)
    assert pedido["status"] == "whatsapp"
    assert pedido["subtotal"] == 28.0
    assert pedido["total"] == 28.0
    assert pedido["itens"][0]["produtoNome"] == "Medalha São José 12mm"
    assert pedido["itens"][0]["quantidade"] == 4


def test_cria_pedido_com_varios_itens_soma_o_total(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={
            "descricao": ["Medalha São José 12mm", "Chaveiro Santa Rita"],
            "quantidade": ["2", "1"],
            "valor_unitario": ["5,00", "18,00"],
        },
        auth=("admin", "segredo123"),
    )
    token = resposta.headers["Location"].rsplit("/", 1)[-1]
    pedido = pedidos.obter_pedido(token)
    assert pedido["subtotal"] == 28.0
    assert len(pedido["itens"]) == 2


def test_ignora_linha_sem_descricao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={
            "descricao": ["Medalha São José 12mm", ""],
            "quantidade": ["4", "1"],
            "valor_unitario": ["7,00", "5,00"],
        },
        auth=("admin", "segredo123"),
    )
    token = resposta.headers["Location"].rsplit("/", 1)[-1]
    pedido = pedidos.obter_pedido(token)
    assert len(pedido["itens"]) == 1


def test_sem_nenhum_item_valido_400(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": [""], "quantidade": ["1"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400


def test_quantidade_invalida_400(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Item"], "quantidade": ["abc"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400


def test_quantidade_zero_400(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Item"], "quantidade": ["0"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400


def test_fluxo_completo_ate_confirmar_venda(client, monkeypatch):
    """Prova ponta a ponta que o pedido manual abaixo do minimo segue
    pro MESMO fluxo ja existente de confirmar venda de lead do
    WhatsApp, sem precisar de nenhuma mudanca la´."""
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Medalha São José 12mm"], "quantidade": ["4"], "valor_unitario": ["7,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]

    resposta = client.post(
        f"/admin/pedidos/{token}/confirmar-venda",
        data={
            "cliente_nome": "Maria Teste",
            "endereco_cep": "59000000",
            "endereco_logradouro": "Rua Teste",
            "endereco_numero": "100",
            "endereco_bairro": "Centro",
            "endereco_cidade": "Natal",
            "endereco_uf": "RN",
            "forma_pagamento": "Pix (combinado no WhatsApp)",
            "valor_pago": "28,00",
        },
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302
    pedido = pedidos.obter_pedido(token)
    assert pedido["status"] == "pago"
    assert pedido["total"] == 28.0


def test_item_manual_aparece_no_csv_de_producao(client, monkeypatch):
    """ver conversa: item manual nao tem produtoNome vindo do catalogo,
    precisa cair no CSV mesmo assim usando a descricao digitada."""
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Medalha São José 12mm"], "quantidade": ["4"], "valor_unitario": ["7,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]
    resposta = client.get(f"/admin/pedidos/{token}/csv", auth=("admin", "segredo123"))
    assert resposta.status_code == 200
    texto = resposta.data.decode("utf-8-sig")
    assert "Medalha São José 12mm" in texto
