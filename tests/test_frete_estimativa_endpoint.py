from __future__ import annotations

import re

import pytest

import app as app_module

app = app_module.app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture(autouse=True)
def limpar_cache_estimativa():
    # cada teste comeca com o cache de cotacao por CEP vazio, senao um
    # teste anterior com o mesmo CEP fake contaminaria o resultado.
    app_module._CACHE_ESTIMATIVA_FRETE_POR_CEP.clear()
    yield
    app_module._CACHE_ESTIMATIVA_FRETE_POR_CEP.clear()


def test_sem_localizacao_devolve_204(client, monkeypatch):
    monkeypatch.setattr(app_module, "localizar_por_ip", lambda ip: None)
    resposta = client.get("/api/frete/estimativa-por-localizacao")
    assert resposta.status_code == 204


def test_usa_cf_connecting_ip_quando_presente(client, monkeypatch):
    # ver conversa: o site roda atras do Cloudflare -- CF-Connecting-IP
    # tem que ter prioridade sobre remote_addr (que pode ser so o IP do
    # proprio Render/Cloudflare fazendo o proxy, nao o do visitante).
    ip_recebido = []
    monkeypatch.setattr(app_module, "localizar_por_ip", lambda ip: ip_recebido.append(ip) or None)
    client.get("/api/frete/estimativa-por-localizacao", headers={"CF-Connecting-IP": "189.6.10.10"})
    assert ip_recebido == ["189.6.10.10"]


def test_sem_cotacao_disponivel_devolve_204(client, monkeypatch):
    monkeypatch.setattr(
        app_module, "localizar_por_ip", lambda ip: {"cidade": "Natal", "estado": "Rio Grande do Norte", "cep": "59000000"}
    )
    monkeypatch.setattr(app_module, "opcoes_frete_estimativa", lambda cep: [])
    resposta = client.get("/api/frete/estimativa-por-localizacao")
    assert resposta.status_code == 204


def test_com_localizacao_e_cotacao_devolve_economico_e_expresso(client, monkeypatch):
    monkeypatch.setattr(
        app_module, "localizar_por_ip", lambda ip: {"cidade": "Natal", "estado": "Rio Grande do Norte", "cep": "59000000"}
    )
    monkeypatch.setattr(
        app_module,
        "opcoes_frete_estimativa",
        lambda cep: [
            {"transportadora": "Correios", "servico": "PAC", "preco": 20.70, "prazo_dias": 8},
            {"transportadora": "Correios", "servico": "SEDEX", "preco": 45.00, "prazo_dias": 3},
        ],
    )
    resposta = client.get("/api/frete/estimativa-por-localizacao")
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["cidade"] == "Natal"
    assert dados["estado"] == "Rio Grande do Norte"
    assert dados["economico"]["transportadora"] == "Correios"  # a mais barata (PAC)
    assert dados["expresso"]["transportadora"] == "Correios"  # a mais rapida (SEDEX)
    assert dados["economico"]["servico"] == "PAC"
    assert dados["expresso"]["servico"] == "SEDEX"
    assert "correios.svg" in dados["economico"]["logo"]  # ver services/frete.py:LOGO_POR_TRANSPORTADORA
    assert re.fullmatch(r"\d{2}/\d{2}", dados["economico"]["data"])
    assert re.fullmatch(r"\d{2}/\d{2}", dados["expresso"]["data"])


def test_cotacao_e_cacheada_por_cep(client, monkeypatch):
    chamadas = []

    def opcoes_fake(cep):
        chamadas.append(cep)
        return [{"transportadora": "Correios", "servico": "PAC", "preco": 20.70, "prazo_dias": 8}]

    monkeypatch.setattr(
        app_module, "localizar_por_ip", lambda ip: {"cidade": "Natal", "estado": "Rio Grande do Norte", "cep": "59000000"}
    )
    monkeypatch.setattr(app_module, "opcoes_frete_estimativa", opcoes_fake)

    client.get("/api/frete/estimativa-por-localizacao")
    client.get("/api/frete/estimativa-por-localizacao")

    assert len(chamadas) == 1  # a segunda chamada usou o cache, nao bateu a Frenet/Melhor Envio de novo
