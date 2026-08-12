"""
Acesso a data/precos.json.

Por enquanto so expoe o preco minimo (usado no "A partir de R$X" dos
cards do catalogo). O motor completo de calculo por faixa de atacado
(calcular_preco, proxima_faixa) entra na ETAPA 5, quando o carrinho
precisar recalcular o pedido inteiro a cada mudanca de quantidade.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PRECOS_PATH = DATA_DIR / "precos.json"

TAMANHOS = ("12mm", "16mm")


def carregar_precos() -> dict:
    with PRECOS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def preco_minimo() -> float:
    precos = carregar_precos()
    valores = [v for tamanho in TAMANHOS for v in precos[tamanho].values()]
    return min(valores)
