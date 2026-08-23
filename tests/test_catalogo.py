from pathlib import Path

from config import DESCRICOES_CATEGORIA
from services.catalogo import (
    buscar_produto,
    carregar_produtos,
    categoria_por_slug,
    categorias_com_slug,
    slugify,
)

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


def test_slugify():
    assert slugify("Nossa Senhora") == "nossa-senhora"
    assert slugify("Espírito Santo") == "espirito-santo"
    assert slugify("Famílias") == "familias"


def test_categorias_com_slug_cobre_todas_as_categorias_reais():
    produtos = carregar_produtos()
    categorias_reais = {p["categoria"] for p in produtos}
    categorias = categorias_com_slug(produtos)
    assert {c["nome"] for c in categorias} == categorias_reais
    # slugs unicos -- duas categorias diferentes nao podem colidir na
    # mesma URL /categoria/<slug>
    slugs = [c["slug"] for c in categorias]
    assert len(slugs) == len(set(slugs))


def test_categoria_por_slug_resolve_e_ignora_slug_invalido():
    produtos = carregar_produtos()
    assert categoria_por_slug(produtos, "nossa-senhora") == "Nossa Senhora"
    assert categoria_por_slug(produtos, "nao-existe") is None


def test_descricoes_categoria_cobre_todas_as_categorias_reais():
    # toda categoria que existe de verdade no catalogo precisa ter uma
    # descricao (senao a pagina /categoria/<slug> fica sem meta
    # description/intro) -- pega categoria nova sem descricao cadastrada.
    produtos = carregar_produtos()
    categorias_reais = {p["categoria"] for p in produtos}
    assert categorias_reais <= set(DESCRICOES_CATEGORIA)
