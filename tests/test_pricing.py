from services.pricing import calcular_carrinho, calcular_preco, proxima_faixa


def test_calcular_preco_varejo_abaixo_de_20():
    assert calcular_preco("16mm", 10) == 5.00


def test_calcular_preco_faixas():
    assert calcular_preco("12mm", 20) == 4.50
    assert calcular_preco("12mm", 29) == 4.50
    assert calcular_preco("12mm", 30) == 4.00
    assert calcular_preco("16mm", 98) == 3.50
    assert calcular_preco("16mm", 100) == 3.00
    assert calcular_preco("16mm", 2000) == 1.75
    assert calcular_preco("16mm", 5000) == 1.75


def test_calcular_preco_igual_para_12_e_16mm():
    for quantidade in (1, 20, 50, 131, 2000):
        assert calcular_preco("12mm", quantidade) == calcular_preco("16mm", quantidade)


def test_proxima_faixa_perto_do_limite():
    assert proxima_faixa("16mm", 98) == {"quantidade": 100, "faltam": 2, "preco": 3.00}


def test_proxima_faixa_none_na_faixa_maxima():
    assert proxima_faixa("16mm", 2000) is None
    assert proxima_faixa("16mm", 5000) is None


def test_calcular_carrinho_soma_todos_produtos_para_a_mesma_faixa():
    itens = [
        {"tamanho": "16mm", "quantidade": 40},
        {"tamanho": "12mm", "quantidade": 30},
        {"tamanho": "16mm", "quantidade": 40},
    ]
    resultado = calcular_carrinho(itens)
    assert resultado["quantidade_total"] == 110
    assert resultado["faixa_label"] == "100-130 unidades"
    for item in resultado["itens"]:
        assert item["preco_unitario"] == 3.00
    assert resultado["subtotal_total"] == round(110 * 3.00, 2)


def test_calcular_carrinho_mudanca_de_faixa_ao_cruzar_o_limite():
    quase = calcular_carrinho([{"tamanho": "16mm", "quantidade": 98}])
    assert quase["proxima_faixa"] == {"quantidade": 100, "faltam": 2, "preco": 3.00}
    assert quase["itens"][0]["preco_unitario"] == 3.50

    completo = calcular_carrinho([{"tamanho": "16mm", "quantidade": 100}])
    assert completo["itens"][0]["preco_unitario"] == 3.00


def test_calcular_carrinho_abaixo_do_minimo():
    resultado = calcular_carrinho([{"tamanho": "16mm", "quantidade": 5}])
    assert resultado["subtotal_total"] == 25.00
    assert resultado["atinge_minimo"] is False


def test_calcular_carrinho_atinge_minimo():
    resultado = calcular_carrinho([{"tamanho": "16mm", "quantidade": 20}])
    assert resultado["subtotal_total"] == 90.00
    assert resultado["atinge_minimo"] is True


def test_calcular_carrinho_vazio():
    resultado = calcular_carrinho([])
    assert resultado["quantidade_total"] == 0
    assert resultado["subtotal_total"] == 0.0
    assert resultado["proxima_faixa"] is None
    assert resultado["faixa_atual_inicio"] == 0
    assert resultado["frete_gratis_atingido"] is False
    assert resultado["falta_para_frete_gratis"] == 300.00


def test_faixa_atual_inicio():
    assert calcular_carrinho([{"tamanho": "16mm", "quantidade": 98}])["faixa_atual_inicio"] == 50
    assert calcular_carrinho([{"tamanho": "16mm", "quantidade": 100}])["faixa_atual_inicio"] == 100


def test_frete_gratis_nao_atingido():
    resultado = calcular_carrinho([{"tamanho": "16mm", "quantidade": 20}])
    assert resultado["subtotal_total"] == 90.00
    assert resultado["frete_gratis_atingido"] is False
    assert resultado["falta_para_frete_gratis"] == 210.00


def test_frete_gratis_atingido():
    # 110 unidades na faixa 100-130 (R$3,00/un) = R$330, acima dos R$300
    resultado = calcular_carrinho([{"tamanho": "16mm", "quantidade": 110}])
    assert resultado["subtotal_total"] == 330.00
    assert resultado["frete_gratis_atingido"] is True
    assert resultado["falta_para_frete_gratis"] == 0.0
