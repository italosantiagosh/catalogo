from __future__ import annotations

from unittest.mock import Mock, patch

import services.inter as inter


def _preparar_credenciais(monkeypatch):
    monkeypatch.setattr(inter, "INTER_CLIENT_ID", "id-teste")
    monkeypatch.setattr(inter, "INTER_CLIENT_SECRET", "segredo-teste")
    monkeypatch.setattr(inter, "INTER_CERTIFICADO_PEM", "-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----")
    monkeypatch.setattr(inter, "INTER_CHAVE_PRIVADA_PEM", "-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----")
    monkeypatch.setattr(inter, "_token_cache", None)
    monkeypatch.setattr(inter, "_arquivos_certificado", None)


def _cliente_exemplo(**overrides):
    base = dict(
        nome="Maria Teste", tipo_pessoa="fisica", documento="11144477735",
        telefone="84999999999", email="maria@example.com",
    )
    base.update(overrides)
    return base


def _endereco_exemplo(**overrides):
    base = dict(
        cep="59000000", logradouro="Rua Teste", numero="100", complemento="",
        bairro="Centro", cidade="Natal", uf="RN",
    )
    base.update(overrides)
    return base


def test_emitir_boleto_sem_credenciais_devolve_erro(monkeypatch):
    monkeypatch.setattr(inter, "INTER_CLIENT_ID", "")
    resultado = inter.emitir_boleto(
        seu_numero="ABC123", valor=50.0, cliente=_cliente_exemplo(), endereco=_endereco_exemplo()
    )
    assert "erro" in resultado


def test_obter_token_usa_certificado_e_client_credentials(monkeypatch, tmp_path):
    _preparar_credenciais(monkeypatch)
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    resposta_mock.json.return_value = {"access_token": "tok123", "expires_in": 3600}
    with patch("services.inter.requests.post", return_value=resposta_mock) as post_mock:
        token = inter._obter_token()
    assert token == "tok123"
    corpo = post_mock.call_args.kwargs["data"]
    assert corpo["client_id"] == "id-teste"
    assert corpo["client_secret"] == "segredo-teste"
    assert corpo["grant_type"] == "client_credentials"
    assert "cert" in post_mock.call_args.kwargs


def test_obter_token_reaproveita_cache_valido(monkeypatch):
    _preparar_credenciais(monkeypatch)
    import time

    monkeypatch.setattr(inter, "_token_cache", {"access_token": "tok-cache", "expira_em": time.time() + 3000})
    with patch("services.inter.requests.post") as post_mock:
        token = inter._obter_token()
    assert token == "tok-cache"
    post_mock.assert_not_called()


def test_emitir_boleto_com_sucesso(monkeypatch):
    _preparar_credenciais(monkeypatch)
    monkeypatch.setattr(inter, "_obter_token", lambda: "tok123")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    resposta_mock.json.return_value = {"codigoSolicitacao": "abc-uuid"}
    with patch("services.inter.requests.post", return_value=resposta_mock) as post_mock:
        resultado = inter.emitir_boleto(
            seu_numero="ABC123", valor=50.0, cliente=_cliente_exemplo(), endereco=_endereco_exemplo()
        )
    assert resultado == {"codigo_solicitacao": "abc-uuid"}
    payload = post_mock.call_args.kwargs["json"]
    assert payload["seuNumero"] == "ABC123"
    assert payload["valorNominal"] == 50.0
    assert payload["pagador"]["nome"] == "Maria Teste"
    assert payload["pagador"]["cpfCnpj"] == "11144477735"
    assert payload["pagador"]["tipoPessoa"] == "FISICA"
    assert payload["pagador"]["ddd"] == "84"
    assert payload["pagador"]["telefone"] == "999999999"
    assert payload["formasRecebimento"] == ["BOLETO", "PIX"]


def test_emitir_boleto_juridica_manda_tipo_pessoa_correto(monkeypatch):
    _preparar_credenciais(monkeypatch)
    monkeypatch.setattr(inter, "_obter_token", lambda: "tok123")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    resposta_mock.json.return_value = {"codigoSolicitacao": "abc-uuid"}
    with patch("services.inter.requests.post", return_value=resposta_mock) as post_mock:
        inter.emitir_boleto(
            seu_numero="ABC123", valor=50.0,
            cliente=_cliente_exemplo(tipo_pessoa="juridica", documento="11222333000181"),
            endereco=_endereco_exemplo(),
        )
    payload = post_mock.call_args.kwargs["json"]
    assert payload["pagador"]["tipoPessoa"] == "JURIDICA"


def test_emitir_boleto_erro_de_rede(monkeypatch):
    import requests

    _preparar_credenciais(monkeypatch)
    monkeypatch.setattr(inter, "_obter_token", lambda: "tok123")
    with patch("services.inter.requests.post", side_effect=requests.RequestException("timeout")):
        resultado = inter.emitir_boleto(
            seu_numero="ABC123", valor=50.0, cliente=_cliente_exemplo(), endereco=_endereco_exemplo()
        )
    assert "erro" in resultado


def test_consultar_cobranca_com_sucesso(monkeypatch):
    _preparar_credenciais(monkeypatch)
    monkeypatch.setattr(inter, "_obter_token", lambda: "tok123")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    resposta_mock.json.return_value = {"cobranca": {"situacao": "RECEBIDO"}, "boleto": {}, "pix": {}}
    with patch("services.inter.requests.get", return_value=resposta_mock):
        resultado = inter.consultar_cobranca("abc-uuid")
    assert resultado["cobranca"]["situacao"] == "RECEBIDO"


def test_consultar_cobranca_sem_token_devolve_erro(monkeypatch):
    _preparar_credenciais(monkeypatch)
    monkeypatch.setattr(inter, "_obter_token", lambda: None)
    resultado = inter.consultar_cobranca("abc-uuid")
    assert "erro" in resultado


def test_baixar_pdf_com_sucesso(monkeypatch):
    _preparar_credenciais(monkeypatch)
    monkeypatch.setattr(inter, "_obter_token", lambda: "tok123")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    resposta_mock.json.return_value = {"pdf": "base64conteudo"}
    with patch("services.inter.requests.get", return_value=resposta_mock):
        resultado = inter.baixar_pdf("abc-uuid")
    assert resultado == {"pdf_base64": "base64conteudo"}


def test_telefone_ddd_numero_separa_corretamente():
    ddd, numero = inter._telefone_ddd_numero("84999999999")
    assert ddd == "84"
    assert numero == "999999999"
