from __future__ import annotations

import pytest

import services.carrinhos_manuais as carrinhos_manuais
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    import app as app_module

    monkeypatch.setattr(carrinhos_manuais, "DB_PATH", str(tmp_path / "pedidos.db"))
    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    app.config["TESTING"] = True
    return app.test_client()


def _itens_exemplo():
    return [
        {
            "chave": "sao-jose-1-medalha-16mm",
            "tipo": "catalogo",
            "produtoId": "sao-jose",
            "produtoNome": "São José",
            "modeloId": 1,
            "modeloNome": "Modelo 1",
            "imagem": "/static/img/produtos/sao_jose_modelo_1_medalha.jpg",
            "imagensCor": None,
            "formato": "medalha",
            "chave_preco": "16mm",
            "tamanho": "16mm",
            "cor": None,
            "quantidade": 10,
        },
    ]


def test_admin_carrinho_manual_exige_autenticacao(client):
    resposta = client.post("/admin/carrinho-manual", json={"itens": _itens_exemplo()})
    assert resposta.status_code == 401


def test_admin_carrinho_manual_cria_e_devolve_link(client):
    resposta = client.post(
        "/admin/carrinho-manual", json={"itens": _itens_exemplo()}, auth=("admin", "segredo123")
    )
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["ok"] is True
    assert dados["token"]
    assert f"montar={dados['token']}" in dados["url"]


def test_admin_carrinho_manual_rejeita_itens_vazios(client):
    resposta = client.post("/admin/carrinho-manual", json={"itens": []}, auth=("admin", "segredo123"))
    assert resposta.status_code == 400


def test_api_carrinho_manual_obter_devolve_itens_salvos(client):
    criado = client.post(
        "/admin/carrinho-manual", json={"itens": _itens_exemplo()}, auth=("admin", "segredo123")
    ).get_json()

    resposta = client.get(f"/api/carrinho/manual/{criado['token']}")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["itens"][0]["produtoId"] == "sao-jose"
    assert dados["itens"][0]["quantidade"] == 10


def test_api_carrinho_manual_token_inexistente_404(client):
    resposta = client.get("/api/carrinho/manual/token-que-nao-existe")
    assert resposta.status_code == 404


def test_carrinho_com_montar_carrega_pagina_normal(client):
    # so confirma que a pagina carrega normal com ?montar= -- o
    # preenchimento de verdade acontece via JS/fetch no navegador, que
    # o teste de servidor (sem JS) nao executa.
    criado = client.post(
        "/admin/carrinho-manual", json={"itens": _itens_exemplo()}, auth=("admin", "segredo123")
    ).get_json()

    resposta = client.get(f"/carrinho?montar={criado['token']}")
    assert resposta.status_code == 200
