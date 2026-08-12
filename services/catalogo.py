"""Carrega o catalogo de produtos a partir de data/produtos.json."""

from __future__ import annotations

import json
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
