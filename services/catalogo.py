"""Carrega o catalogo de produtos a partir de data/produtos.json."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PRODUTOS_PATH = DATA_DIR / "produtos.json"

# Cache em memoria (por processo) -- produtos.json e´ estatico, so muda
# com um novo deploy (ninguem edita pelo admin em runtime), entao nao
# ha risco de servir dado velho. Antes disso, TODA pagina relia e
# reparseava o JSON inteiro do zero, varias vezes por requisicao
# (buscar_produto chama carregar_produtos, que por sua vez e´ chamado
# de novo logo em seguida por quem so precisava da lista inteira) --
# desperdicio de CPU/IO que so cresce com o catalogo. Nada aqui muta o
# dict devolvido (conferido: todo consumidor so le), entao devolver a
# MESMA lista cacheada, sem copiar, e´ seguro.
_produtos_cache: list[dict] | None = None


def carregar_produtos() -> list[dict]:
    global _produtos_cache
    if _produtos_cache is None:
        with PRODUTOS_PATH.open(encoding="utf-8") as f:
            _produtos_cache = json.load(f)
    return _produtos_cache


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


def normalizar_busca(texto: str) -> str:
    """minusculo sem acento nem apostrofo, pra comparar nomes de forma
    tolerante a acentuacao -- usado tanto no filtro client-side de
    /catalogo (via equivalente em JS) quanto na busca ao vivo da home
    (/api/busca). Sem apostrofo pra "Santa Teresa d'Avila" ser encontrada
    digitando "davila", sem precisar do "'" (ver conversa)."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"['’`´]", "", sem_acento)


def categorias_com_slug(produtos: list[dict]) -> list[dict]:
    nomes = sorted({p["categoria"] for p in produtos})
    return [{"nome": nome, "slug": slugify(nome)} for nome in nomes]


def categoria_por_slug(produtos: list[dict], slug: str) -> str | None:
    for nome in {p["categoria"] for p in produtos}:
        if slugify(nome) == slug:
            return nome
    return None
