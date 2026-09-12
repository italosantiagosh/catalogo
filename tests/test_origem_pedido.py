from __future__ import annotations

from unittest.mock import patch

import pytest

import services.pedidos as pedidos
from app import _classificar_dispositivo, _classificar_origem_pedido, app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
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


def test_classificar_dispositivo():
    assert _classificar_dispositivo("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)") == "Celular"
    assert _classificar_dispositivo("Mozilla/5.0 (Linux; Android 14)") == "Celular"
    assert _classificar_dispositivo("Mozilla/5.0 (iPad; CPU OS 17_0)") == "Tablet"
    assert _classificar_dispositivo("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") == "Computador"
    assert _classificar_dispositivo("") == "Computador"


def test_classificar_origem_pedido_reconhece_fontes_conhecidas():
    assert _classificar_origem_pedido({"referrer": "https://chatgpt.com/c/abc"})[0] == "ChatGPT"
    assert _classificar_origem_pedido({"referrer": "https://l.instagram.com/xyz"})[0] == "Instagram"
    assert _classificar_origem_pedido({"referrer": "https://m.facebook.com/"})[0] == "Facebook"
    assert _classificar_origem_pedido({"referrer": "https://wa.me/5584999999999"})[0] == "WhatsApp"
    assert _classificar_origem_pedido({"referrer": "https://www.google.com/"})[0] == "Google (busca)"
    assert _classificar_origem_pedido(
        {"referrer": "", "utm_source": "google", "utm_medium": "cpc"}
    )[0] == "Google Ads"


def test_classificar_origem_pedido_sem_referrer_nem_utm_e_direto():
    assert _classificar_origem_pedido({"referrer": "", "utm_source": ""})[0] == "Direto"
    assert _classificar_origem_pedido(None)[0] == "Direto"
    assert _classificar_origem_pedido({})[0] == "Direto"


def test_classificar_origem_pedido_desconhecido_cai_em_outro():
    classificacao, bruto = _classificar_origem_pedido({"referrer": "https://umsitequalquer.com.br/pagina"})
    assert classificacao == "Outro"
    assert "umsitequalquer.com.br" in bruto


def test_criar_pedido_grava_origem_e_dispositivo(client):
    corpo = _corpo_valido(origem={"referrer": "https://www.instagram.com/nove.de.julho/", "utm_source": ""})
    with patch("app.calcular_frete", return_value={
        "frete_gratis": False,
        "opcoes": [{"transportadora": "Correios", "servico": "PAC", "preco": 10.0, "prazo_dias": 6}],
    }), patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        resposta = client.post(
            "/api/pedido/criar",
            json=corpo,
            headers={"User-Agent": "Mozilla/5.0 (Linux; Android 14) Mobile"},
        )
    assert resposta.status_code == 200
    # o pedido ja foi persistido antes do link de pagamento ser gerado --
    # confere direto no banco pelo mais recente.
    pedido = pedidos.listar_pedidos()[0]
    assert pedido["origem_classificada"] == "Instagram"
    assert pedido["origem_dispositivo"] == "Celular"
