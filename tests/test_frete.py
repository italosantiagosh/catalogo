from __future__ import annotations

from unittest.mock import Mock, patch

import services.frete as frete


def test_peso_total_gramas():
    itens = [
        {"chave_preco": "16mm", "quantidade": 10},  # 10 x 2g = 20g
        {"chave_preco": "12mm", "quantidade": 4},  # 4 x 1.5g = 6g
        {"chave_preco": "entremeio", "quantidade": 5},  # 5 x 2g = 10g
        {"chave_preco": "chaveiro", "quantidade": 2},  # 2 x 15g = 30g
    ]
    assert frete.peso_total_gramas(itens) == 66.0


def test_preco_str_para_float_formato_br():
    assert frete._preco_str_para_float("25,90") == 25.90
    assert frete._preco_str_para_float("1.234,56") == 1234.56


def test_calcular_frete_com_frete_gratis_nao_consulta_api():
    with patch("services.frete.requests.post") as post_mock:
        resultado = frete.calcular_frete(
            itens=[{"chave_preco": "16mm", "quantidade": 200}],
            cep_destino="59000000",
            subtotal=350.0,
            frete_gratis_atingido=True,
        )
    post_mock.assert_not_called()
    assert resultado["frete_gratis"] is True
    assert resultado["opcoes"] == []
    assert "WhatsApp" in resultado["aviso"]


def test_consultar_frenet_sem_token_retorna_erro(monkeypatch):
    monkeypatch.setattr(frete, "FRENET_TOKEN", "")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59000000")
    resultado = frete.consultar_frenet("20040020", 100, 50.0)
    assert "erro" in resultado


def test_consultar_frenet_cep_invalido(monkeypatch):
    monkeypatch.setattr(frete, "FRENET_TOKEN", "token-fake")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59000000")
    resultado = frete.consultar_frenet("123", 100, 50.0)
    assert "erro" in resultado


def _resposta_frenet_fake(*servicos):
    resp = Mock()
    resp.raise_for_status = Mock()
    resp.json = Mock(return_value={"ShippingSevicesArray": list(servicos)})
    return resp


def test_consultar_frenet_filtra_so_erro_mini_envio_fica_e_ordena_por_preco(monkeypatch):
    monkeypatch.setattr(frete, "FRENET_TOKEN", "token-fake")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59000000")

    servicos = [
        {"Carrier": "Correios", "ServiceDescription": "SEDEX", "ShippingPrice": "45,00",
         "DeliveryTime": 3, "Error": False},
        {"Carrier": "Correios", "ServiceDescription": "PAC", "ShippingPrice": "25,90",
         "DeliveryTime": 8, "Error": False},
        {"Carrier": "Correios", "ServiceDescription": "Mini Envios", "ShippingPrice": "12,00",
         "DeliveryTime": 12, "Error": False},
        {"Carrier": "Jadlog", "ServiceDescription": ".Package", "ShippingPrice": "0,00",
         "DeliveryTime": None, "Error": True, "Msg": "CEP fora de area de cobertura"},
    ]

    with patch("services.frete.requests.post", return_value=_resposta_frenet_fake(*servicos)) as post_mock:
        resultado = frete.consultar_frenet("20040020", 50, 100.0)

    post_mock.assert_called_once()
    _, kwargs = post_mock.call_args
    assert kwargs["headers"]["token"] == "token-fake"
    assert kwargs["json"]["SellerCEP"] == "59000000"
    assert kwargs["json"]["RecipientCEP"] == "20040020"
    assert kwargs["json"]["ShipmentInvoiceValue"] == 0  # sem seguro

    opcoes = resultado["opcoes"]
    # so o servico com Error=True fica de fora -- Mini Envios aparece
    # normalmente quando o frete nao e gratis (pedido do usuario)
    assert [o["servico"] for o in opcoes] == ["Mini Envios", "PAC", "SEDEX"]
    assert opcoes[0]["preco"] == 12.00
    assert opcoes[1]["preco"] == 25.90
    assert opcoes[2]["preco"] == 45.00


def test_consultar_frenet_descarta_cotacao_absurda_de_transportadora_de_carga(monkeypatch):
    # Caso real observado: Jadlog/Loggi/Total Express devolvendo R$1700+
    # pra um pedido de R$50 em medalhas -- claramente errado, nunca deve
    # aparecer pro cliente.
    monkeypatch.setattr(frete, "FRENET_TOKEN", "token-fake")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59000000")

    servicos = [
        {"Carrier": "Correios", "ServiceDescription": "PAC", "ShippingPrice": "25,90",
         "DeliveryTime": 8, "Error": False},
        {"Carrier": "Jadlog", "ServiceDescription": "Jadlog Package", "ShippingPrice": "1709,00",
         "DeliveryTime": 11, "Error": False},
        {"Carrier": "Loggi", "ServiceDescription": "Loggi", "ShippingPrice": "1898,00",
         "DeliveryTime": 7, "Error": False},
    ]
    with patch("services.frete.requests.post", return_value=_resposta_frenet_fake(*servicos)):
        resultado = frete.consultar_frenet("20040020", 50, 50.0)

    assert [o["transportadora"] for o in resultado["opcoes"]] == ["Correios"]


def test_consultar_frenet_sem_nenhuma_cotacao_confiavel_retorna_erro(monkeypatch):
    monkeypatch.setattr(frete, "FRENET_TOKEN", "token-fake")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59000000")

    servicos = [
        {"Carrier": "Jadlog", "ServiceDescription": "Jadlog Package", "ShippingPrice": "1709,00",
         "DeliveryTime": 11, "Error": False},
    ]
    with patch("services.frete.requests.post", return_value=_resposta_frenet_fake(*servicos)):
        resultado = frete.consultar_frenet("20040020", 50, 50.0)

    assert resultado["opcoes"] == []
    assert "erro" in resultado


def test_calcular_frete_sem_frete_gratis_consulta_api(monkeypatch):
    monkeypatch.setattr(frete, "FRENET_TOKEN", "token-fake")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59000000")

    servicos = [
        {"Carrier": "Correios", "ServiceDescription": "PAC", "ShippingPrice": "25,90",
         "DeliveryTime": 8, "Error": False},
    ]
    with patch("services.frete.requests.post", return_value=_resposta_frenet_fake(*servicos)):
        resultado = frete.calcular_frete(
            itens=[{"chave_preco": "16mm", "quantidade": 10}],
            cep_destino="20040020",
            subtotal=50.0,
            frete_gratis_atingido=False,
        )

    assert resultado["frete_gratis"] is False
    assert resultado["opcoes"][0]["servico"] == "PAC"
