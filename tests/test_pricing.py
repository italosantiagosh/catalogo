from services.pricing import calcular_carrinho, calcular_preco, preco_varejo, proxima_faixa


def test_calcular_preco_varejo_abaixo_de_20():
    assert calcular_preco("16mm", 10) == 5.00


def test_preco_varejo():
    assert preco_varejo() == 5.00
    assert preco_varejo("entremeio") == 5.00
    assert preco_varejo("chaveiro") == 15.00


def test_calcular_preco_faixas():
    assert calcular_preco("12mm", 20) == 4.50
    assert calcular_preco("12mm", 29) == 4.50
    assert calcular_preco("12mm", 30) == 4.00
    assert calcular_preco("16mm", 98) == 3.50
    assert calcular_preco("16mm", 100) == 3.00
    assert calcular_preco("16mm", 2000) == 1.75
    assert calcular_preco("16mm", 5000) == 1.75


def test_calcular_preco_igual_para_12mm_16mm_e_entremeio():
    for quantidade in (1, 20, 50, 131, 2000):
        preco_12 = calcular_preco("12mm", quantidade)
        assert calcular_preco("16mm", quantidade) == preco_12
        assert calcular_preco("entremeio", quantidade) == preco_12


def test_calcular_preco_chaveiro_tem_tabela_propria():
    assert calcular_preco("chaveiro", 1) == 15.00
    assert calcular_preco("chaveiro", 19) == 15.00
    assert calcular_preco("chaveiro", 20) == 12.00
    assert calcular_preco("chaveiro", 30) == 11.00
    assert calcular_preco("chaveiro", 50) == 10.00
    assert calcular_preco("chaveiro", 100) == 9.00
    assert calcular_preco("chaveiro", 200) == 8.00
    assert calcular_preco("chaveiro", 300) == 7.00
    assert calcular_preco("chaveiro", 1000) == 7.00


def test_proxima_faixa_perto_do_limite():
    assert proxima_faixa("16mm", 98) == {
        "quantidade": 100,
        "faltam": 2,
        "preco": 3.00,
        "economia": 50.00,  # (3.50 atual - 3.00 proximo) * 100 unidades
    }


def test_proxima_faixa_none_na_faixa_maxima():
    assert proxima_faixa("16mm", 2000) is None
    assert proxima_faixa("16mm", 5000) is None
    assert proxima_faixa("chaveiro", 300) is None
    assert proxima_faixa("chaveiro", 1000) is None


def test_calcular_carrinho_soma_medalha_e_entremeio_no_mesmo_grupo():
    # medalhas 12mm/16mm e entremeios se misturam pra faixa (grupo "padrao")
    itens = [
        {"chave_preco": "16mm", "quantidade": 40},
        {"chave_preco": "12mm", "quantidade": 30},
        {"chave_preco": "entremeio", "quantidade": 40},
    ]
    resultado = calcular_carrinho(itens)
    assert resultado["quantidade_total"] == 110
    assert resultado["grupos"]["padrao"]["quantidade_total"] == 110
    assert resultado["grupos"]["padrao"]["faixa_label"] == "100-130 unidades"
    for item in resultado["itens"]:
        assert item["preco_unitario"] == 3.00
    assert resultado["subtotal_total"] == round(110 * 3.00, 2)


def test_calcular_carrinho_chaveiro_nao_se_mistura_com_padrao():
    itens = [
        {"chave_preco": "16mm", "quantidade": 90},
        {"chave_preco": "chaveiro", "quantidade": 10},
    ]
    resultado = calcular_carrinho(itens)
    assert resultado["quantidade_total"] == 100
    assert resultado["grupos"]["padrao"]["quantidade_total"] == 90
    assert resultado["grupos"]["chaveiro"]["quantidade_total"] == 10
    # 90 medalhas -> faixa 50-99 (R$3,50), nao a faixa 100 mesmo somando com chaveiros
    medalha_item = next(i for i in resultado["itens"] if i["chave_preco"] == "16mm")
    assert medalha_item["preco_unitario"] == 3.50
    # 10 chaveiros -> continua no varejo (R$15), nao pega desconto por causa das medalhas
    chaveiro_item = next(i for i in resultado["itens"] if i["chave_preco"] == "chaveiro")
    assert chaveiro_item["preco_unitario"] == 15.00


def test_calcular_carrinho_chaveiro_em_quantidade_isoladamente_bate_faixa_propria():
    resultado = calcular_carrinho([{"chave_preco": "chaveiro", "quantidade": 200}])
    assert resultado["grupos"]["chaveiro"]["quantidade_total"] == 200
    assert resultado["grupos"]["chaveiro"]["faixa_label"] == "200-299 unidades"
    assert resultado["itens"][0]["preco_unitario"] == 8.00
    assert resultado["subtotal_total"] == round(200 * 8.00, 2)


def test_calcular_preco_igual_para_medalha_2lados_e_entremeio_2lados():
    for chave in ("medalha_2lados", "entremeio_2lados"):
        assert calcular_preco(chave, 1) == 7.00
        assert calcular_preco(chave, 20) == 6.00
        assert calcular_preco(chave, 30) == 5.00
        assert calcular_preco(chave, 50) == 4.50
        assert calcular_preco(chave, 100) == 4.00
        assert calcular_preco(chave, 130) == 3.75
        assert calcular_preco(chave, 160) == 3.50
        assert calcular_preco(chave, 300) == 3.25
        assert calcular_preco(chave, 500) == 3.00
        assert calcular_preco(chave, 1000) == 2.75
        assert calcular_preco(chave, 2000) == 2.25


def test_calcular_carrinho_medalha_2lados_e_entremeio_2lados_somam_no_mesmo_grupo():
    itens = [
        {"chave_preco": "medalha_2lados", "quantidade": 15},
        {"chave_preco": "entremeio_2lados", "quantidade": 15},
    ]
    resultado = calcular_carrinho(itens)
    assert resultado["grupos"]["duas_faces"]["quantidade_total"] == 30
    # 30 juntos -> faixa dos 30 (R$5,00), mesmo cada um tendo so 15 isolado
    for item in resultado["itens"]:
        assert item["preco_unitario"] == 5.00


def test_calcular_carrinho_duas_faces_nao_se_mistura_com_padrao_nem_chaveiro():
    itens = [
        {"chave_preco": "16mm", "quantidade": 90},
        {"chave_preco": "chaveiro", "quantidade": 10},
        {"chave_preco": "medalha_2lados", "quantidade": 20},
    ]
    resultado = calcular_carrinho(itens)
    assert resultado["quantidade_total"] == 120
    assert resultado["grupos"]["padrao"]["quantidade_total"] == 90
    assert resultado["grupos"]["chaveiro"]["quantidade_total"] == 10
    assert resultado["grupos"]["duas_faces"]["quantidade_total"] == 20
    duas_faces_item = next(i for i in resultado["itens"] if i["chave_preco"] == "medalha_2lados")
    assert duas_faces_item["preco_unitario"] == 6.00  # faixa 20, isolada das outras


def test_calcular_carrinho_mudanca_de_faixa_ao_cruzar_o_limite():
    quase = calcular_carrinho([{"chave_preco": "16mm", "quantidade": 98}])
    assert quase["grupos"]["padrao"]["proxima_faixa"] == {
        "quantidade": 100,
        "faltam": 2,
        "preco": 3.00,
        "economia": 50.00,
    }
    assert quase["itens"][0]["preco_unitario"] == 3.50

    completo = calcular_carrinho([{"chave_preco": "16mm", "quantidade": 100}])
    assert completo["itens"][0]["preco_unitario"] == 3.00


def test_calcular_carrinho_abaixo_do_minimo():
    resultado = calcular_carrinho([{"chave_preco": "16mm", "quantidade": 5}])
    assert resultado["subtotal_total"] == 25.00
    assert resultado["atinge_minimo"] is False


def test_calcular_carrinho_atinge_minimo():
    resultado = calcular_carrinho([{"chave_preco": "16mm", "quantidade": 20}])
    assert resultado["subtotal_total"] == 90.00
    assert resultado["atinge_minimo"] is True


def test_calcular_carrinho_vazio():
    resultado = calcular_carrinho([])
    assert resultado["quantidade_total"] == 0
    assert resultado["subtotal_total"] == 0.0
    assert resultado["grupos"]["padrao"]["proxima_faixa"] is None
    assert resultado["grupos"]["padrao"]["faixa_atual_inicio"] == 0
    assert resultado["grupos"]["chaveiro"]["proxima_faixa"] is None
    assert resultado["grupos"]["chaveiro"]["faixa_atual_inicio"] == 0
    assert resultado["frete_gratis_atingido"] is False
    assert resultado["falta_para_frete_gratis"] == 300.00


def test_faixa_atual_inicio():
    assert calcular_carrinho([{"chave_preco": "16mm", "quantidade": 98}])["grupos"]["padrao"]["faixa_atual_inicio"] == 50
    assert calcular_carrinho([{"chave_preco": "16mm", "quantidade": 100}])["grupos"]["padrao"]["faixa_atual_inicio"] == 100


def test_frete_gratis_nao_atingido():
    resultado = calcular_carrinho([{"chave_preco": "16mm", "quantidade": 20}])
    assert resultado["subtotal_total"] == 90.00
    assert resultado["frete_gratis_atingido"] is False
    assert resultado["falta_para_frete_gratis"] == 210.00


def test_frete_gratis_atingido():
    # 110 unidades na faixa 100-130 (R$3,00/un) = R$330, acima dos R$300
    resultado = calcular_carrinho([{"chave_preco": "16mm", "quantidade": 110}])
    assert resultado["subtotal_total"] == 330.00
    assert resultado["frete_gratis_atingido"] is True
    assert resultado["falta_para_frete_gratis"] == 0.0


def test_desconto_frete_atacado_zero_antes_da_primeira_faixa():
    resultado = calcular_carrinho([{"chave_preco": "16mm", "quantidade": 19}])
    assert resultado["desconto_frete_atacado"] == 0


def test_desconto_frete_atacado_carrinho_vazio():
    assert calcular_carrinho([])["desconto_frete_atacado"] == 0


def test_desconto_frete_atacado_exemplo_do_usuario():
    """Ver conversa: 20 medalhas 16mm ja e´ atacado (R$4,50/un = R$90) ->
    8% de 90 = R$7,20 de desconto no frete."""
    resultado = calcular_carrinho([{"chave_preco": "16mm", "quantidade": 20}])
    assert resultado["subtotal_total"] == 90.00
    assert resultado["desconto_frete_atacado"] == 7.20


def test_desconto_frete_atacado_escala_com_a_quantidade():
    # 25 unidades ainda na faixa 20-29 (R$4,50/un) = R$112,50 -> 8% = R$9,00
    resultado = calcular_carrinho([{"chave_preco": "16mm", "quantidade": 25}])
    assert resultado["subtotal_total"] == 112.50
    assert resultado["desconto_frete_atacado"] == 9.00


def test_desconto_frete_atacado_por_grupo_independente():
    # so o chaveiro atinge atacado (20 un) -- medalha continua no varejo,
    # nao entra no calculo do desconto
    resultado = calcular_carrinho([
        {"chave_preco": "16mm", "quantidade": 5},
        {"chave_preco": "chaveiro", "quantidade": 20},
    ])
    assert resultado["grupos"]["padrao"]["quantidade_total"] == 5
    assert resultado["grupos"]["chaveiro"]["quantidade_total"] == 20
    # 20 chaveiros x R$12,00 = R$240,00 -> 8% = R$19,20
    assert resultado["desconto_frete_atacado"] == 19.20


def test_desconto_frete_atacado_duas_faces_grupo_independente():
    # 20 medalhas_2lados x R$6,00 = R$120,00 -> 8% = R$9,60; nao mistura
    # com a faixa varejo das 16mm que continuam abaixo do atacado
    resultado = calcular_carrinho([
        {"chave_preco": "16mm", "quantidade": 5},
        {"chave_preco": "medalha_2lados", "quantidade": 20},
    ])
    assert resultado["grupos"]["padrao"]["quantidade_total"] == 5
    assert resultado["grupos"]["duas_faces"]["quantidade_total"] == 20
    assert resultado["desconto_frete_atacado"] == 9.60


def test_desconto_frete_atacado_soma_os_dois_grupos_quando_ambos_atingem():
    resultado = calcular_carrinho([
        {"chave_preco": "16mm", "quantidade": 20},   # 20 x 4,50 = 90,00 -> 7,20
        {"chave_preco": "chaveiro", "quantidade": 20},  # 20 x 12,00 = 240,00 -> 19,20
    ])
    assert resultado["desconto_frete_atacado"] == 26.40


def test_frete_gratis_considera_subtotal_combinado_de_ambos_grupos():
    # medalhas + chaveiros somam pro frete gratis, mesmo sem se misturar na faixa
    resultado = calcular_carrinho([
        {"chave_preco": "16mm", "quantidade": 5},   # 5 x 5,00 = 25,00
        {"chave_preco": "chaveiro", "quantidade": 20},  # 20 x 12,00 = 240,00
    ])
    assert resultado["subtotal_total"] == 265.00
    assert resultado["frete_gratis_atingido"] is False
    assert resultado["falta_para_frete_gratis"] == 35.00
