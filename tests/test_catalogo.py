from pathlib import Path

from services.catalogo import buscar_produto, carregar_produtos

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def test_carrega_produtos():
    produtos = carregar_produtos()
    assert len(produtos) > 100


def test_ids_unicos():
    produtos = carregar_produtos()
    ids = [p["id"] for p in produtos]
    assert len(ids) == len(set(ids))


def test_cada_produto_tem_ao_menos_um_modelo_com_tamanho_e_imagem():
    for produto in carregar_produtos():
        assert produto["modelos"], f"{produto['id']} sem modelos"
        for modelo in produto["modelos"]:
            assert modelo["tamanhos"]
            assert modelo["imagem"]


def test_imagens_referenciadas_existem_em_disco():
    for produto in carregar_produtos():
        for modelo in produto["modelos"]:
            caminho = STATIC_DIR / modelo["imagem"]
            assert caminho.is_file(), f"imagem faltando: {modelo['imagem']}"


def test_buscar_produto_por_id():
    produto = buscar_produto("sao-jose")
    assert produto is not None
    assert produto["nome"] == "São José"


def test_buscar_produto_inexistente():
    assert buscar_produto("nao-existe") is None
