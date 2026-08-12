"""
Motor de preco por atacado.

A regra central (secao 25 do briefing): a faixa de atacado depende da
quantidade TOTAL de medalhas no carrinho -- somando todos os produtos e
tamanhos -- nao da quantidade de cada produto isoladamente. calcular_preco
e proxima_faixa recebem esse total ja somado por quem chama (o endpoint
/api/carrinho/calcular, em app.py); nao ha nenhuma soma "por produto"
aqui dentro.

Frete gratis (frete_gratis_reais em data/precos.json) e so um indicador
visual por enquanto -- baseado no SUBTOTAL do carrinho, nao na
quantidade. O calculo de frete em si continua "a combinar no
atendimento" (secao 18 do briefing).
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


def pedido_minimo_reais() -> float:
    return carregar_precos()["pedido_minimo_reais"]


def preco_varejo() -> float:
    """Preco unitario da faixa "1" (antes de qualquer desconto de atacado)
    -- usado nas paginas de produto/personalizada para mostrar um preco de
    referencia antes do cliente adicionar ao carrinho, ja que o preco real
    so e conhecido depois (depende da quantidade TOTAL do carrinho)."""
    return calcular_preco("16mm", 1)


def frete_gratis_reais() -> float:
    return carregar_precos()["frete_gratis_reais"]


def _faixas_ordenadas(tamanho: str) -> list[tuple[int, float]]:
    tabela = carregar_precos()[tamanho]
    return sorted((int(inicio), preco) for inicio, preco in tabela.items())


def _faixa_atual(tamanho: str, quantidade_total_carrinho: int) -> tuple[int, float]:
    """(inicio, preco) da faixa em que a quantidade dada se encontra."""
    faixas = _faixas_ordenadas(tamanho)
    atual = faixas[0]
    for inicio, valor in faixas:
        if quantidade_total_carrinho >= inicio:
            atual = (inicio, valor)
        else:
            break
    return atual


def calcular_preco(tamanho: str, quantidade_total_carrinho: int) -> float:
    """Preco unitario da faixa atual, para a quantidade TOTAL do carrinho."""
    return _faixa_atual(tamanho, quantidade_total_carrinho)[1]


def proxima_faixa(tamanho: str, quantidade_total_carrinho: int) -> dict | None:
    """Proxima faixa a desbloquear (quantidade/faltam/preco), ou None se o
    carrinho ja esta na maior faixa cadastrada."""
    for inicio, valor in _faixas_ordenadas(tamanho):
        if quantidade_total_carrinho < inicio:
            return {
                "quantidade": inicio,
                "faltam": inicio - quantidade_total_carrinho,
                "preco": valor,
            }
    return None


def faixa_label(tamanho: str, quantidade_total_carrinho: int) -> str:
    """Rotulo de exibicao tipo '50-99 unidades' para a faixa atual."""
    faixas = _faixas_ordenadas(tamanho)
    for i, (inicio, _) in enumerate(faixas):
        fim = faixas[i + 1][0] - 1 if i + 1 < len(faixas) else None
        if quantidade_total_carrinho >= inicio and (fim is None or quantidade_total_carrinho <= fim):
            return f"{inicio}+ unidades" if fim is None else f"{inicio}-{fim} unidades"
    return ""


def calcular_carrinho(itens: list[dict]) -> dict:
    """
    Recalcula o carrinho inteiro de uma vez: soma a quantidade total (todos
    os produtos e tamanhos juntos), acha a faixa de atacado atingida, e
    aplica o preco dessa faixa em CADA item (o preco em si pode variar por
    tamanho, mas a faixa que da o desconto e sempre a mesma para o
    carrinho inteiro).

    `itens` e uma lista de {"tamanho": "12mm"|"16mm", "quantidade": int}.
    A ordem da lista de retorno espelha a ordem recebida.
    """
    quantidade_total = sum(item["quantidade"] for item in itens)

    itens_calculados = []
    subtotal_total = 0.0
    for item in itens:
        preco_unitario = calcular_preco(item["tamanho"], quantidade_total)
        subtotal = round(preco_unitario * item["quantidade"], 2)
        subtotal_total += subtotal
        itens_calculados.append(
            {**item, "preco_unitario": preco_unitario, "subtotal": subtotal}
        )
    subtotal_total = round(subtotal_total, 2)

    # a faixa e igual para 12mm/16mm hoje (mesma tabela); usa o tamanho do
    # primeiro item so como referencia para o rotulo/proxima faixa exibidos
    # uma unica vez no resumo do carrinho.
    tamanho_referencia = itens[0]["tamanho"] if itens else "16mm"

    frete_gratis = frete_gratis_reais()
    falta_frete = round(frete_gratis - subtotal_total, 2)

    return {
        "quantidade_total": quantidade_total,
        "faixa_label": faixa_label(tamanho_referencia, quantidade_total) if itens else "",
        "faixa_atual_inicio": _faixa_atual(tamanho_referencia, quantidade_total)[0] if itens else 0,
        "itens": itens_calculados,
        "subtotal_total": subtotal_total,
        "pedido_minimo_reais": pedido_minimo_reais(),
        "atinge_minimo": subtotal_total >= pedido_minimo_reais() if itens else True,
        "proxima_faixa": proxima_faixa(tamanho_referencia, quantidade_total) if itens else None,
        "frete_gratis_reais": frete_gratis,
        "frete_gratis_atingido": subtotal_total >= frete_gratis if itens else False,
        "falta_para_frete_gratis": max(0.0, falta_frete) if itens else frete_gratis,
    }
