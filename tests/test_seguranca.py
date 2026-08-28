from __future__ import annotations

from unittest.mock import patch

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


def test_resposta_tem_headers_de_seguranca(client):
    resposta = client.get("/")
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    assert resposta.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in resposta.headers
    assert "Strict-Transport-Security" in resposta.headers


def test_csp_permite_blob_em_img_src(client):
    """static/js/personalizada.js carrega a foto enviada via
    URL.createObjectURL(file) antes de desenhar no canvas do editor de
    recorte -- sem 'blob:' no img-src, a simulação da medalha
    personalizada trava logo no upload (já aconteceu de verdade, ver
    conversa)."""
    resposta = client.get("/personalizada")
    csp = resposta.headers["Content-Security-Policy"]
    diretiva_img = next(d for d in csp.split(";") if d.strip().startswith("img-src"))
    assert "blob:" in diretiva_img


def test_post_admin_de_outra_origem_e_bloqueado(client, monkeypatch):
    _preparar_admin(monkeypatch)
    pedido = pedidos.criar_pedido(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "descricao": "São José"}],
        subtotal=50.0,
        frete_descricao="Correios PAC",
        frete_preco=10.0,
        cliente={"nome": "Maria", "tipo_pessoa": "fisica", "documento": "11144477735", "telefone": "84999999999", "email": "m@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua", "numero": "1", "complemento": "", "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    resposta = client.post(
        f"/admin/pedidos/{pedido['token']}/status",
        data={"status": "faturado"},
        headers={"Origin": "https://site-malicioso.exemplo"},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 403
    assert pedidos.obter_pedido(pedido["token"])["status"] == "pendente"


def test_post_admin_de_mesma_origem_funciona(client, monkeypatch):
    _preparar_admin(monkeypatch)
    pedido = pedidos.criar_pedido(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "descricao": "São José"}],
        subtotal=50.0,
        frete_descricao="Correios PAC",
        frete_preco=10.0,
        cliente={"nome": "Maria", "tipo_pessoa": "fisica", "documento": "11144477735", "telefone": "84999999999", "email": "m@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua", "numero": "1", "complemento": "", "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    resposta = client.post(
        f"/admin/pedidos/{pedido['token']}/status",
        data={"status": "faturado"},
        headers={"Origin": "http://localhost"},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302  # redirect normal pos-acao (PRG), nao bloqueado
    assert pedidos.obter_pedido(pedido["token"])["status"] == "faturado"


def test_post_admin_sem_origin_nem_referer_ainda_funciona(client, monkeypatch):
    """Sem os dois headers (script/ferramenta de linha de comando, nao
    navegador) -- nao bloqueia, pra nao quebrar uso via API do proprio
    dono (ver _origem_admite_mesma_origem)."""
    _preparar_admin(monkeypatch)
    pedido = pedidos.criar_pedido(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "descricao": "São José"}],
        subtotal=50.0,
        frete_descricao="Correios PAC",
        frete_preco=10.0,
        cliente={"nome": "Maria", "tipo_pessoa": "fisica", "documento": "11144477735", "telefone": "84999999999", "email": "m@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua", "numero": "1", "complemento": "", "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    resposta = client.post(
        f"/admin/pedidos/{pedido['token']}/status", data={"status": "faturado"}, auth=("admin", "segredo123")
    )
    assert resposta.status_code == 302
    assert pedidos.obter_pedido(pedido["token"])["status"] == "faturado"


def test_rate_limit_bloqueia_apos_muitas_chamadas(client, monkeypatch):
    # desliga o filtro que pula rate limit durante os testes (ver
    # app._pular_rate_limit_em_teste) so PRA ESSE teste, pra confirmar
    # que o limite realmente existe e bloqueia -- os outros testes
    # continuam sem rate limit (senao a suite toda tomaria 429).
    monkeypatch.setattr(app, "testing", False)
    corpo = {"itens": [{"chave_preco": "16mm", "quantidade": 1}], "cep": "59000000"}
    respostas = [client.post("/api/frete/calcular", json=corpo) for _ in range(21)]
    codigos = [r.status_code for r in respostas]
    assert 429 in codigos


def test_webhook_infinitepay_exige_chave_quando_configurada(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "WEBHOOK_INFINITEPAY_SECRET", "segredo-webhook")
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post(
            "/api/pedido/criar",
            json={
                "itens": [{"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"}],
                "frete": {"texto": "Correios PAC", "preco": 10.0},
                "cliente": {"nome": "Maria", "tipo_pessoa": "fisica", "documento": "11144477735",
                            "telefone": "84999999999", "email": "m@example.com"},
                "endereco": {"cep": "59000000", "logradouro": "Rua", "numero": "1", "complemento": "",
                             "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
            },
        ).get_json()

    # sem a chave certa -- nao processa
    sem_chave = client.post(
        "/webhook/infinitepay", json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"}
    )
    assert sem_chave.status_code == 404
    assert pedidos.obter_pedido(criado["token"])["status"] == "pendente"

    # com a chave certa -- processa normalmente
    com_chave = client.post(
        "/webhook/infinitepay?chave=segredo-webhook",
        json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
    )
    assert com_chave.status_code == 200
    assert pedidos.obter_pedido(criado["token"])["status"] == "pago"
