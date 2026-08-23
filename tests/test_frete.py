from __future__ import annotations

from unittest.mock import Mock, patch

import services.frete as frete


def test_peso_total_kg():
    itens = [
        {"chave_preco": "16mm", "quantidade": 10},  # 10 x 0,002kg = 0,020kg
        {"chave_preco": "12mm", "quantidade": 4},  # 4 x 0,001kg = 0,004kg
        {"chave_preco": "entremeio", "quantidade": 5},  # 5 x 0,002kg = 0,010kg
        {"chave_preco": "chaveiro", "quantidade": 2},  # 2 x 0,015kg = 0,030kg
    ]
    assert frete.peso_total_kg(itens) == 0.064


def test_peso_padrao_kg_sobe_para_a_proxima_faixa():
    assert frete.peso_padrao_kg(0.02) == 0.3  # pedido pequeno -> 300g
    assert frete.peso_padrao_kg(0.3) == 0.3  # exatamente na faixa -> fica nela
    assert frete.peso_padrao_kg(0.31) == 0.5
    assert frete.peso_padrao_kg(0.5) == 0.5
    assert frete.peso_padrao_kg(0.51) == 1.0
    assert frete.peso_padrao_kg(1.0) == 1.0
    assert frete.peso_padrao_kg(1.01) == 2.0
    assert frete.peso_padrao_kg(2.0) == 2.0


def test_peso_padrao_kg_acima_de_2kg_usa_peso_real():
    assert frete.peso_padrao_kg(2.5) == 2.5
    assert frete.peso_padrao_kg(5.0) == 5.0


def test_preco_str_para_float_formato_frenet_ponto_decimal():
    assert frete._preco_str_para_float("25.90") == 25.90
    assert frete._preco_str_para_float("1234.56") == 1234.56
    assert frete._preco_str_para_float(17.09) == 17.09  # tambem aceita numero, nao so string


def test_preco_str_para_float_nao_confunde_ponto_com_separador_de_milhar():
    # Bug real corrigido: "17.09" (formato real da Frenet) virava 1709.0
    # quando o codigo tratava "." como separador de milhar do formato BR.
    assert frete._preco_str_para_float("17.09") == 17.09
    assert frete._preco_str_para_float("17.09") != 1709.0


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
    resultado = frete.consultar_frenet("20040020", 0.1, 50.0)
    assert "erro" in resultado


def test_consultar_frenet_cep_invalido(monkeypatch):
    monkeypatch.setattr(frete, "FRENET_TOKEN", "token-fake")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59000000")
    resultado = frete.consultar_frenet("123", 0.1, 50.0)
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
        {"Carrier": "Correios", "ServiceDescription": "SEDEX", "ShippingPrice": "45.00",
         "DeliveryTime": 3, "Error": False},
        {"Carrier": "Correios", "ServiceDescription": "PAC", "ShippingPrice": "25.90",
         "DeliveryTime": 8, "Error": False},
        {"Carrier": "Correios", "ServiceDescription": "Mini Envios", "ShippingPrice": "12.00",
         "DeliveryTime": 12, "Error": False},
        {"Carrier": "Jadlog", "ServiceDescription": ".Package", "ShippingPrice": "0.00",
         "DeliveryTime": None, "Error": True, "Msg": "CEP fora de area de cobertura"},
    ]

    with patch("services.frete.requests.post", return_value=_resposta_frenet_fake(*servicos)) as post_mock:
        resultado = frete.consultar_frenet("20040020", 0.05, 100.0)

    post_mock.assert_called_once()
    _, kwargs = post_mock.call_args
    assert kwargs["headers"]["token"] == "token-fake"
    assert kwargs["json"]["SellerCEP"] == "59000000"
    assert kwargs["json"]["RecipientCEP"] == "20040020"
    assert kwargs["json"]["ShipmentInvoiceValue"] == 0  # sem seguro
    item = kwargs["json"]["ShippingItemArray"][0]
    assert item["Category"]
    assert item["isFragile"] is False

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
        {"Carrier": "Correios", "ServiceDescription": "PAC", "ShippingPrice": "25.90",
         "DeliveryTime": 8, "Error": False},
        {"Carrier": "Jadlog", "ServiceDescription": "Jadlog Package", "ShippingPrice": "1709.00",
         "DeliveryTime": 11, "Error": False},
        {"Carrier": "Loggi", "ServiceDescription": "Loggi", "ShippingPrice": "1898.00",
         "DeliveryTime": 7, "Error": False},
    ]
    with patch("services.frete.requests.post", return_value=_resposta_frenet_fake(*servicos)):
        resultado = frete.consultar_frenet("20040020", 0.05, 50.0)

    assert [o["transportadora"] for o in resultado["opcoes"]] == ["Correios"]


def test_consultar_frenet_sem_nenhuma_cotacao_confiavel_retorna_erro(monkeypatch):
    monkeypatch.setattr(frete, "FRENET_TOKEN", "token-fake")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59000000")

    servicos = [
        {"Carrier": "Jadlog", "ServiceDescription": "Jadlog Package", "ShippingPrice": "1709.00",
         "DeliveryTime": 11, "Error": False},
    ]
    with patch("services.frete.requests.post", return_value=_resposta_frenet_fake(*servicos)):
        resultado = frete.consultar_frenet("20040020", 0.05, 50.0)

    assert resultado["opcoes"] == []
    assert "erro" in resultado


def test_calcular_frete_sem_frete_gratis_consulta_api(monkeypatch):
    monkeypatch.setattr(frete, "FRENET_TOKEN", "token-fake")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59000000")

    servicos = [
        {"Carrier": "Correios", "ServiceDescription": "PAC", "ShippingPrice": "25.90",
         "DeliveryTime": 8, "Error": False},
    ]
    with patch("services.frete.requests.post", return_value=_resposta_frenet_fake(*servicos)) as post_mock:
        resultado = frete.calcular_frete(
            # 10 x 16mm = 0,020kg de peso real -- bem abaixo da faixa
            # padrao de 300g, entao 300g e o que deve ser mandado.
            itens=[{"chave_preco": "16mm", "quantidade": 10}],
            cep_destino="20040020",
            subtotal=50.0,
            frete_gratis_atingido=False,
        )

    _, kwargs = post_mock.call_args
    assert kwargs["json"]["ShippingItemArray"][0]["Weight"] == 0.3

    assert resultado["frete_gratis"] is False
    assert resultado["opcoes"][0]["servico"] == "PAC"


def test_consultar_melhor_envio_sem_token_retorna_lista_vazia(monkeypatch):
    monkeypatch.setattr(frete, "MELHOR_ENVIO_TOKEN", "")
    assert frete.consultar_melhor_envio("20040020", 0.3, 50.0) == []


def _resposta_melhor_envio_fake(lista):
    resp = Mock()
    resp.raise_for_status = Mock()
    resp.json = Mock(return_value=lista)
    return resp


def test_consultar_melhor_envio_filtra_transportadoras_conhecidas_e_erros(monkeypatch):
    monkeypatch.setattr(frete, "MELHOR_ENVIO_TOKEN", "token-me-fake")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59088040")

    servicos = [
        {"name": "Azul Express e-commerce", "price": "29.86", "delivery_time": 6,
         "company": {"name": "Azul Cargo Express"}, "error": None},
        {"name": "PAC", "price": "20.70", "delivery_time": 6,
         "company": {"name": "Correios"}, "error": None},
        {"name": "Jadlog Package", "price": "17.09", "delivery_time": 11,
         "company": {"name": "Jadlog"}, "error": None},
        {"name": "Azul Cargo Expresso", "price": "0", "delivery_time": None,
         "company": {"name": "Azul Cargo Express"}, "error": "Servico indisponivel"},
    ]
    with patch("services.frete.requests.post", return_value=_resposta_melhor_envio_fake(servicos)) as post_mock:
        opcoes = frete.consultar_melhor_envio("20040020", 0.3, 50.0)

    _, kwargs = post_mock.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer token-me-fake"
    assert "User-Agent" in kwargs["headers"]
    assert kwargs["json"]["from"]["postal_code"] == "59088040"
    assert kwargs["json"]["to"]["postal_code"] == "20040020"

    # Azul e Correios (sem sobretaxa) ficam -- Jadlog (fora da lista de
    # transportadoras do Melhor Envio) e a Azul com erro ficam de fora
    assert {o["transportadora"] for o in opcoes} == {"Azul Cargo Express", "Correios"}
    preco_por_transportadora = {o["transportadora"]: o["preco"] for o in opcoes}
    assert preco_por_transportadora["Azul Cargo Express"] == 29.86
    assert preco_por_transportadora["Correios"] == 20.70


def test_consultar_melhor_envio_aplica_sobretaxa_latam_e_jt(monkeypatch):
    monkeypatch.setattr(frete, "MELHOR_ENVIO_TOKEN", "token-me-fake")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59088040")

    servicos = [
        {"name": "LATAM Cargo", "price": "40.00", "delivery_time": 4,
         "company": {"name": "LATAM Cargo"}, "error": None},
        {"name": "J&T Express", "price": "15.00", "delivery_time": 5,
         "company": {"name": "J&T Express"}, "error": None},
    ]
    with patch("services.frete.requests.post", return_value=_resposta_melhor_envio_fake(servicos)):
        opcoes = frete.consultar_melhor_envio("20040020", 0.3, 200.0)

    preco_por_transportadora = {o["transportadora"]: o["preco"] for o in opcoes}
    assert preco_por_transportadora["LATAM Cargo"] == 90.00  # 40 + 50 de sobretaxa
    assert preco_por_transportadora["J&T Express"] == 35.00  # 15 + 20 de sobretaxa


def test_calcular_frete_combina_frenet_e_melhor_envio_ordenado_por_preco(monkeypatch):
    monkeypatch.setattr(frete, "FRENET_TOKEN", "token-fake")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59000000")
    monkeypatch.setattr(frete, "MELHOR_ENVIO_TOKEN", "token-me-fake")

    def post_fake(url, **kwargs):
        if url == frete.FRENET_URL:
            return _resposta_frenet_fake(
                {"Carrier": "Correios", "ServiceDescription": "PAC", "ShippingPrice": "25.90",
                 "DeliveryTime": 8, "Error": False},
            )
        if url == frete.MELHOR_ENVIO_URL:
            return _resposta_melhor_envio_fake([
                {"name": "Azul Express e-commerce", "price": "19.90", "delivery_time": 6,
                 "company": {"name": "Azul Cargo Express"}, "error": None},
            ])
        raise AssertionError(f"URL inesperada: {url}")

    with patch("services.frete.requests.post", side_effect=post_fake):
        resultado = frete.calcular_frete(
            itens=[{"chave_preco": "16mm", "quantidade": 10}],
            cep_destino="20040020",
            subtotal=50.0,
            frete_gratis_atingido=False,
        )

    # a Azul (mais barata) vem primeiro, PAC depois -- fontes diferentes,
    # uma lista so, ordenada por preco
    assert [o["transportadora"] for o in resultado["opcoes"]] == ["Azul Cargo Express", "Correios"]
    assert resultado["opcoes"][0]["preco"] == 19.90
    assert resultado["opcoes"][1]["preco"] == 25.90


def test_calcular_frete_correios_pode_aparecer_das_duas_fontes(monkeypatch):
    # Pedido do usuario: Correios tambem entra pelo Melhor Envio, alem da
    # Frenet (que ja usa o preco do contrato proprio) -- podem aparecer 2
    # opcoes de "Correios" com precos diferentes, isso e esperado.
    monkeypatch.setattr(frete, "FRENET_TOKEN", "token-fake")
    monkeypatch.setattr(frete, "CEP_ORIGEM", "59000000")
    monkeypatch.setattr(frete, "MELHOR_ENVIO_TOKEN", "token-me-fake")

    def post_fake(url, **kwargs):
        if url == frete.FRENET_URL:
            return _resposta_frenet_fake(
                {"Carrier": "Correios", "ServiceDescription": "PAC", "ShippingPrice": "25.90",
                 "DeliveryTime": 8, "Error": False},
            )
        if url == frete.MELHOR_ENVIO_URL:
            return _resposta_melhor_envio_fake([
                {"name": "PAC", "price": "20.70", "delivery_time": 6,
                 "company": {"name": "Correios"}, "error": None},
            ])
        raise AssertionError(f"URL inesperada: {url}")

    with patch("services.frete.requests.post", side_effect=post_fake):
        resultado = frete.calcular_frete(
            itens=[{"chave_preco": "16mm", "quantidade": 10}],
            cep_destino="20040020",
            subtotal=50.0,
            frete_gratis_atingido=False,
        )

    assert [o["transportadora"] for o in resultado["opcoes"]] == ["Correios", "Correios"]
    assert {o["preco"] for o in resultado["opcoes"]} == {20.70, 25.90}
