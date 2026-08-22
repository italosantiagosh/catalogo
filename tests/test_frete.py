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


def test_e_mini_envio():
    assert frete._e_mini_envio("Mini Envios")
    assert frete._e_mini_envio("PAC MINI")
    assert not frete._e_mini_envio("PAC")
    assert not frete._e_mini_envio("SEDEX")


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


def test_consultar_frenet_filtra_erro_e_mini_envio_e_ordena_por_preco(monkeypatch):
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

    opcoes = resultado["opcoes"]
    # Mini Envios e o servico com Error=True ficam de fora
    assert [o["servico"] for o in opcoes] == ["PAC", "SEDEX"]
    assert opcoes[0]["preco"] == 25.90
    assert opcoes[1]["preco"] == 45.00


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
