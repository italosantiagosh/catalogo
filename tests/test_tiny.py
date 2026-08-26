from __future__ import annotations

import json
from unittest.mock import Mock, patch

import services.tiny as tiny


def _pedido_exemplo(**overrides):
    base = dict(
        codigo="ABC123",
        itens=[{"chave_preco": "16mm", "quantidade": 10, "descricao": "São José — Modelo 1", "valor_unitario": 5.0}],
        subtotal=50.0,
        frete_descricao="Correios PAC — R$ 10,00",
        frete_preco=10.0,
        total=60.0,
        cliente_nome="Maria Teste",
        cliente_tipo_pessoa="fisica",
        cliente_documento="12345678900",
        cliente_telefone="84999999999",
        cliente_email="maria@example.com",
        endereco_cep="59000000",
        endereco_destinatario_nome="",
        endereco_destinatario_tipo_pessoa="",
        endereco_destinatario_documento="",
        endereco_logradouro="Rua Teste",
        endereco_numero="100",
        endereco_complemento="",
        endereco_bairro="Centro",
        endereco_cidade="Natal",
        endereco_uf="RN",
        forma_pagamento="pix",
        transaction_nsu="tx-abc",
    )
    base.update(overrides)
    return base


def _resposta_ok(numero=1001, id_=555):
    resposta = Mock()
    resposta.raise_for_status = Mock()
    resposta.json.return_value = {
        "retorno": {
            "status_processamento": 3,
            "status": "OK",
            "registros": [{"registro": {"status": "OK", "id": id_, "numero": numero}}],
        }
    }
    return resposta


def test_sem_token_devolve_erro(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "")
    resultado = tiny.criar_pedido_tiny(_pedido_exemplo())
    assert "erro" in resultado


def test_monta_payload_com_cliente_itens_e_numero_pedido_ecommerce(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        resultado = tiny.criar_pedido_tiny(_pedido_exemplo())

    assert resultado == {"ok": True, "numero": 1001, "id": 555}

    corpo_enviado = post_mock.call_args.kwargs["data"]
    assert corpo_enviado["token"] == "segredo123"
    assert corpo_enviado["formato"] == "json"
    pedido_json = json.loads(corpo_enviado["pedido"])["pedido"]

    assert pedido_json["cliente"]["nome"] == "Maria Teste"
    assert pedido_json["cliente"]["tipo_pessoa"] == "F"
    assert pedido_json["cliente"]["cpf_cnpj"] == "12345678900"
    assert pedido_json["cliente"]["cep"] == "59000000"
    assert pedido_json["itens"][0]["item"]["descricao"] == "São José — Modelo 1"
    assert pedido_json["itens"][0]["item"]["quantidade"] == "10"
    assert pedido_json["itens"][0]["item"]["valor_unitario"] == "5.00"
    assert pedido_json["numero_pedido_ecommerce"] == "ABC123"
    assert pedido_json["forma_pagamento"] == "pix"
    assert "Pedido site #ABC123" in pedido_json["obs"]
    assert "tx-abc" in pedido_json["obs"]


def test_destinatario_diferente_entra_nas_observacoes(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(
            endereco_destinatario_nome="João Receptor", endereco_destinatario_documento="98765432100"
        ))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert "João Receptor" in pedido_json["obs"]
    assert "98765432100" in pedido_json["obs"]


def test_tipo_pessoa_juridica_mapeia_para_j(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(cliente_tipo_pessoa="juridica"))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["cliente"]["tipo_pessoa"] == "J"


def test_forma_pagamento_desconhecida_nao_e_enviada(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(forma_pagamento="boleto_bancario_desconhecido"))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert "forma_pagamento" not in pedido_json


def test_resposta_com_erro_da_tiny(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    resposta = Mock()
    resposta.raise_for_status = Mock()
    resposta.json.return_value = {
        "retorno": {
            "status_processamento": 3,
            "status": "Erro",
            "codigo_erro": 20,
            "erros": [{"erro": "CPF inválido"}],
        }
    }
    with patch("services.tiny.requests.post", return_value=resposta):
        resultado = tiny.criar_pedido_tiny(_pedido_exemplo())
    assert resultado == {"erro": "CPF inválido"}


def test_erro_de_rede(monkeypatch):
    import requests

    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", side_effect=requests.RequestException("timeout")):
        resultado = tiny.criar_pedido_tiny(_pedido_exemplo())
    assert "erro" in resultado
