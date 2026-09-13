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
    # cada teste comeca com os caches de cotacao por CEP e de
    # geolocalizacao por IP vazios, senao um teste anterior com o mesmo
    # CEP/IP fake contaminaria o resultado.
    app_module._CACHE_ESTIMATIVA_FRETE_POR_CEP.clear()
    app_module._CACHE_LOCALIZACAO_POR_IP.clear()
    yield
    app_module._CACHE_ESTIMATIVA_FRETE_POR_CEP.clear()
    app_module._CACHE_LOCALIZACAO_POR_IP.clear()


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


def test_geolocalizacao_e_cacheada_por_ip(client, monkeypatch):
    # ver conversa: log em producao mostrou geolocalizacao falhando pra
    # um IP que respondia normal minutos depois testado na mao (blip de
    # rede pontual do ipwho.is) -- sem cache, o MESMO visitante vendo 2
    # produtos seguidos batia no servico 2 vezes, dobrando a chance de
    # pegar um blip desses.
    chamadas = []

    monkeypatch.setattr(
        app_module,
        "localizar_por_ip",
        lambda ip: chamadas.append(ip) or {"cidade": "Natal", "estado": "Rio Grande do Norte", "cep": "59000000"},
    )
    monkeypatch.setattr(
        app_module,
        "opcoes_frete_estimativa",
        lambda cep: [{"transportadora": "Correios", "servico": "PAC", "preco": 20.70, "prazo_dias": 8}],
    )

    headers = {"CF-Connecting-IP": "186.236.197.50"}
    client.get("/api/frete/estimativa-por-localizacao", headers=headers)
    client.get("/api/frete/estimativa-por-localizacao", headers=headers)

    assert len(chamadas) == 1  # a segunda chamada usou o cache, nao bateu o ipwho.is de novo


def test_geolocalizacao_falha_expira_do_cache_rapido(client, monkeypatch):
    chamadas = []
    relogio = [1000.0]

    monkeypatch.setattr(app_module, "localizar_por_ip", lambda ip: chamadas.append(ip) or None)
    monkeypatch.setattr(app_module.time, "monotonic", lambda: relogio[0])

    headers = {"CF-Connecting-IP": "186.236.197.50"}
    client.get("/api/frete/estimativa-por-localizacao", headers=headers)
    client.get("/api/frete/estimativa-por-localizacao", headers=headers)
    assert len(chamadas) == 1  # ainda dentro do TTL curto da falha, usa o cache

    relogio[0] += app_module._TTL_CACHE_LOCALIZACAO_FALHA_SEGUNDOS + 1
    client.get("/api/frete/estimativa-por-localizacao", headers=headers)
    assert len(chamadas) == 2  # TTL curto expirou -- tenta de novo em vez de esperar as 6h de uma localizacao valida


def test_cotacao_vazia_expira_do_cache_bem_mais_rapido(client, monkeypatch):
    # ver conversa: "ainda ficou sem aparecer" -- lista vazia (falha
    # transitoria da Frenet/Melhor Envio) nao pode prender esse CEP em
    # "sem estimativa" pelas mesmas 6h de uma cotacao de verdade, senao
    # 1 falha de rede esconde a barra pra regiao inteira por horas mesmo
    # com as APIs ja normais de novo.
    chamadas = []
    relogio = [1000.0]

    monkeypatch.setattr(
        app_module, "localizar_por_ip", lambda ip: {"cidade": "Natal", "estado": "Rio Grande do Norte", "cep": "59000000"}
    )
    monkeypatch.setattr(app_module, "opcoes_frete_estimativa", lambda cep: chamadas.append(cep) or [])
    monkeypatch.setattr(app_module.time, "monotonic", lambda: relogio[0])

    client.get("/api/frete/estimativa-por-localizacao")
    client.get("/api/frete/estimativa-por-localizacao")
    assert len(chamadas) == 1  # ainda dentro do TTL curto da lista vazia, usa o cache

    relogio[0] += app_module._TTL_CACHE_ESTIMATIVA_FRETE_VAZIA_SEGUNDOS + 1
    client.get("/api/frete/estimativa-por-localizacao")
    assert len(chamadas) == 2  # TTL curto ja expirou -- tenta de novo em vez de esperar as 6h de uma cotacao valida
