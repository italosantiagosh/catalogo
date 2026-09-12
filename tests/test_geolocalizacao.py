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
    dados = {"status": "success", "countryCode": "BR", "regionName": "Rio Grande do Norte", "city": "Natal", "zip": "59000-000"}
    with patch("services.geolocalizacao.requests.get", return_value=_resposta_mock(dados)):
        resultado = geolocalizacao.localizar_por_ip("1.2.3.4")
    assert resultado == {"cidade": "Natal", "estado": "Rio Grande do Norte", "cep": "59000000"}


def test_localizar_por_ip_fora_do_brasil_devolve_none():
    dados = {"status": "success", "countryCode": "US", "regionName": "California", "city": "Los Angeles", "zip": "90001"}
    with patch("services.geolocalizacao.requests.get", return_value=_resposta_mock(dados)):
        assert geolocalizacao.localizar_por_ip("1.2.3.4") is None


def test_localizar_por_ip_com_status_fail_devolve_none():
    dados = {"status": "fail", "message": "private range"}
    with patch("services.geolocalizacao.requests.get", return_value=_resposta_mock(dados)):
        assert geolocalizacao.localizar_por_ip("127.0.0.1") is None


def test_localizar_por_ip_sem_cep_conhecido_devolve_none():
    dados = {"status": "success", "countryCode": "BR", "regionName": "Bahia", "city": "Salvador", "zip": ""}
    with patch("services.geolocalizacao.requests.get", return_value=_resposta_mock(dados)):
        assert geolocalizacao.localizar_por_ip("1.2.3.4") is None


def test_localizar_por_ip_com_falha_de_rede_devolve_none():
    with patch("services.geolocalizacao.requests.get", side_effect=requests.Timeout("timeout")):
        assert geolocalizacao.localizar_por_ip("1.2.3.4") is None
