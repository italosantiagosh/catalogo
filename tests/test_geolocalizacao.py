from __future__ import annotations

from unittest.mock import Mock, patch

import requests

import services.geolocalizacao as geolocalizacao


def _resposta_mock(json_dado):
    resposta = Mock()
    resposta.json.return_value = json_dado
    resposta.raise_for_status = Mock()
    return resposta


def test_localizar_por_ip_sem_ip_devolve_none():
    assert geolocalizacao.localizar_por_ip("") is None


def test_localizar_por_ip_com_sucesso_e_cep_valido():
    dados = {"success": True, "country_code": "BR", "region": "Rio Grande do Norte", "city": "Natal", "postal": "59000-000"}
    with patch("services.geolocalizacao.requests.get", return_value=_resposta_mock(dados)):
        resultado = geolocalizacao.localizar_por_ip("1.2.3.4")
    assert resultado == {"cidade": "Natal", "estado": "Rio Grande do Norte", "cep": "59000000"}


def test_localizar_por_ip_com_prefixo_de_cep_completa_com_000():
    # ver conversa "a barra sumiu": ipwho.is devolve so o prefixo de 5
    # digitos pra MAIORIA dos IPs brasileiros, nao o CEP completo -- sem
    # esse fallback, a barra ficava escondida (204) pra quase todo mundo.
    dados = {"success": True, "country_code": "BR", "region": "Rio Grande do Sul", "city": "Porto Alegre", "postal": "90020"}
    with patch("services.geolocalizacao.requests.get", return_value=_resposta_mock(dados)):
        resultado = geolocalizacao.localizar_por_ip("1.2.3.4")
    assert resultado == {"cidade": "Porto Alegre", "estado": "Rio Grande do Sul", "cep": "90020000"}


def test_localizar_por_ip_com_prefixo_sem_zero_a_esquerda_completa_certo():
    # "01002" (Sao Paulo) volta truncado como "1002" -- zfill devolve o
    # zero perdido antes de completar com "000".
    dados = {"success": True, "country_code": "BR", "region": "Sao Paulo", "city": "São Paulo", "postal": "1002"}
    with patch("services.geolocalizacao.requests.get", return_value=_resposta_mock(dados)):
        resultado = geolocalizacao.localizar_por_ip("1.2.3.4")
    assert resultado == {"cidade": "São Paulo", "estado": "Sao Paulo", "cep": "01002000"}


def test_localizar_por_ip_fora_do_brasil_devolve_none():
    dados = {"success": True, "country_code": "US", "region": "California", "city": "Los Angeles", "postal": "90001"}
    with patch("services.geolocalizacao.requests.get", return_value=_resposta_mock(dados)):
        assert geolocalizacao.localizar_por_ip("1.2.3.4") is None


def test_localizar_por_ip_com_sucesso_false_devolve_none():
    dados = {"success": False, "message": "invalid IP"}
    with patch("services.geolocalizacao.requests.get", return_value=_resposta_mock(dados)):
        assert geolocalizacao.localizar_por_ip("127.0.0.1") is None


def test_localizar_por_ip_sem_cep_conhecido_devolve_none():
    dados = {"success": True, "country_code": "BR", "region": "Bahia", "city": "Salvador", "postal": ""}
    with patch("services.geolocalizacao.requests.get", return_value=_resposta_mock(dados)):
        assert geolocalizacao.localizar_por_ip("1.2.3.4") is None


def test_localizar_por_ip_com_falha_de_rede_devolve_none():
    with patch("services.geolocalizacao.requests.get", side_effect=requests.Timeout("timeout")):
        assert geolocalizacao.localizar_por_ip("1.2.3.4") is None


def test_localizar_por_ip_tenta_de_novo_apos_falha_pontual_de_rede():
    # ver conversa: falha real em producao pra um IP que, testado
    # manualmente logo depois, respondia normal -- blip de rede pontual
    # de uma API gratis sem SLA. 1a chamada falha, 2a funciona -- ainda
    # devolve resultado em vez de desistir na primeira.
    dados = {"success": True, "country_code": "BR", "region": "Rio Grande do Norte", "city": "Natal", "postal": "59030-350"}
    with patch(
        "services.geolocalizacao.requests.get",
        side_effect=[requests.Timeout("timeout"), _resposta_mock(dados)],
    ):
        resultado = geolocalizacao.localizar_por_ip("186.236.197.50")
    assert resultado == {"cidade": "Natal", "estado": "Rio Grande do Norte", "cep": "59030350"}


def test_localizar_por_ip_desiste_apos_2_falhas_seguidas():
    with patch(
        "services.geolocalizacao.requests.get",
        side_effect=[requests.Timeout("timeout"), requests.Timeout("timeout")],
    ) as mock_get:
        assert geolocalizacao.localizar_por_ip("1.2.3.4") is None
    assert mock_get.call_count == 2  # nao fica tentando pra sempre
