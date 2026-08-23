"""Carrega o catalogo de produtos a partir de data/produtos.json."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PRODUTOS_PATH = DATA_DIR / "produtos.json"


def carregar_produtos() -> list[dict]:
    with PRODUTOS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def buscar_produto(produto_id: str) -> dict | None:
    for produto in carregar_produtos():
        if produto["id"] == produto_id:
            return produto
    return None


def slugify(texto: str) -> str:
    """Slug de URL a partir de um nome de categoria (ex: "Nossa Senhora"
    -> "nossa-senhora") -- usado pra montar e resolver as paginas
    /categoria/<slug> em app.py (SEO: URL propria e indexavel por
    categoria, em vez de so filtro por clique na home)."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def categorias_com_slug(produtos: list[dict]) -> list[dict]:
    nomes = sorted({p["categoria"] for p in produtos})
    return [{"nome": nome, "slug": slugify(nome)} for nome in nomes]


def categoria_por_slug(produtos: list[dict], slug: str) -> str | None:
    for nome in {p["categoria"] for p in produtos}:
        if slugify(nome) == slug:
            return nome
    return None
