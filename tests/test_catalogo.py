from services.catalogo import buscar_produto, carregar_produtos


def test_carrega_cinco_santos():
    assert len(carregar_produtos()) == 5


def test_cada_santo_tem_dois_modelos_com_dois_tamanhos():
    for produto in carregar_produtos():
        assert len(produto["modelos"]) == 2
        for modelo in produto["modelos"]:
            assert modelo["tamanhos"] == ["12mm", "16mm"]


def test_buscar_produto_por_id():
    produto = buscar_produto("sao-jose")
    assert produto is not None
    assert produto["nome"] == "São José"


def test_buscar_produto_inexistente():
    assert buscar_produto("nao-existe") is None
