"""
Motor de preco por atacado.

Duas "familias" de produto, cada uma com seu proprio GRUPO de atacado --
a quantidade que conta pra faixa de desconto NAO se mistura entre grupos:

    "padrao"   -- medalhas (12mm/16mm) e entremeios. Mesma regra de
                  sempre (secao 25 do briefing original): a faixa depende
                  da quantidade TOTAL desse grupo no carrinho, somando
                  todos os santos/tamanhos/cores livremente.
    "chaveiro" -- tabela de precos propria (varejo R$15, atacado proprio).
                  Conta pra faixa dele isoladamente; nao soma com
                  medalhas/entremeios nem eles somam com ele.

Cada item do carrinho manda uma "chave_preco" (12mm | 16mm | entremeio |
chaveiro) que serve dois propositos: indexa a tabela certa em
data/precos.json E diz a qual grupo o item pertence (GRUPO_DE_CHAVE).

pedido_minimo_reais / frete_gratis_reais continuam avaliados sobre o
SUBTOTAL COMBINADO (todos os grupos juntos) -- sao sobre o pedido
inteiro, nao por grupo.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PRECOS_PATH = DATA_DIR / "precos.json"

GRUPO_DE_CHAVE = {
    "12mm": "padrao",
    "16mm": "padrao",
    "entremeio": "padrao",
    "chaveiro": "chaveiro",
}
CHAVES_PRECO = tuple(GRUPO_DE_CHAVE)
GRUPOS = ("padrao", "chaveiro")

# Desconto no FRETE (nao no preco do produto) quando um grupo atinge a
# primeira faixa de atacado (ver conversa: "antes do frete gratis...
# quando um item atinge a primeira quantidade de atacado, 8% desse
# valor vai ser desconto nos fretes"). Exemplo dado pelo usuario: 20
# medalhas 16mm ja e´ atacado (R$4,50/un = R$90,00) -> 8% de 90 =
# R$7,20 de desconto no frete. Independente por grupo (padrao e
# chaveiro cada um so conta se ELE MESMO atingiu a propria primeira
# faixa de atacado, mesmo criterio de GRUPO ja usado no resto do
# motor de preco) -- se nenhum grupo atingiu atacado, sem desconto
# (frete cheio). Regra separada e ANTERIOR ao credito de frete gratis
# (frete_gratis_reais, ver calcular_carrinho) -- so faz sentido
# aplicar quando o pedido ainda nao chegou la.
DESCONTO_FRETE_ATACADO_PCT = 0.08


def carregar_precos() -> dict:
    with PRECOS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def pedido_minimo_reais() -> float:
    return carregar_precos()["pedido_minimo_reais"]


def frete_gratis_reais() -> float:
    return carregar_precos()["frete_gratis_reais"]


def preco_varejo(chave_preco: str = "16mm") -> float:
    """Preco unitario da faixa "1" (antes de qualquer desconto de atacado)
    -- usado na home e nas paginas de produto/personalizada para mostrar um
    preco de referencia antes do cliente adicionar ao carrinho, ja que o
    preco real so e conhecido depois (depende da quantidade TOTAL do
    grupo no carrinho)."""
    return calcular_preco(chave_preco, 1)


def _faixas_ordenadas(chave_preco: str) -> list[tuple[int, float]]:
    tabela = carregar_precos()[chave_preco]
    return sorted((int(inicio), preco) for inicio, preco in tabela.items())


def _faixa_atual(chave_preco: str, quantidade_total_grupo: int) -> tuple[int, float]:
    """(inicio, preco) da faixa em que a quantidade dada se encontra."""
    faixas = _faixas_ordenadas(chave_preco)
    atual = faixas[0]
    for inicio, valor in faixas:
        if quantidade_total_grupo >= inicio:
            atual = (inicio, valor)
        else:
            break
    return atual


def calcular_preco(chave_preco: str, quantidade_total_grupo: int) -> float:
    """Preco unitario da faixa atual, para a quantidade TOTAL do GRUPO
    (padrao ou chaveiro) a que essa chave pertence."""
    return _faixa_atual(chave_preco, quantidade_total_grupo)[1]


def proxima_faixa(chave_preco: str, quantidade_total_grupo: int) -> dict | None:
    """Proxima faixa a desbloquear (quantidade/faltam/preco), ou None se o
    grupo ja esta na maior faixa cadastrada. `economia` e quanto o pedido
    inteiro passa a custar A MENOS ao cruzar essa faixa -- preco por
    unidade cai pra TODAS as unidades do grupo, nao so as adicionadas
    (mesmo modelo de faixa "por degrau" ja usado em calcular_preco), entao
    e (preco atual - preco da faixa) vezes a quantidade que a faixa exige."""
    preco_atual = calcular_preco(chave_preco, quantidade_total_grupo)
    for inicio, valor in _faixas_ordenadas(chave_preco):
        if quantidade_total_grupo < inicio:
            return {
                "quantidade": inicio,
                "faltam": inicio - quantidade_total_grupo,
                "preco": valor,
                "economia": round((preco_atual - valor) * inicio, 2),
            }
    return None


def faixa_label(chave_preco: str, quantidade_total_grupo: int) -> str:
    """Rotulo de exibicao tipo '50-99 unidades' para a faixa atual."""
    faixas = _faixas_ordenadas(chave_preco)
    for i, (inicio, _) in enumerate(faixas):
        fim = faixas[i + 1][0] - 1 if i + 1 < len(faixas) else None
        if quantidade_total_grupo >= inicio and (fim is None or quantidade_total_grupo <= fim):
            return f"{inicio}+ unidades" if fim is None else f"{inicio}-{fim} unidades"
    return ""


def _grupo_atingiu_atacado(chave_preco: str, quantidade_total_grupo: int) -> bool:
    """True quando a quantidade ja passou da faixa "1" (varejo) pra
    qualquer faixa de atacado seguinte -- ver DESCONTO_FRETE_ATACADO_PCT."""
    if quantidade_total_grupo <= 0:
        return False
    faixas = _faixas_ordenadas(chave_preco)
    return _faixa_atual(chave_preco, quantidade_total_grupo)[0] > faixas[0][0]


def _calcular_grupo(chave_referencia: str, quantidade_total_grupo: int) -> dict:
    if quantidade_total_grupo == 0:
        # carrinho (ou grupo) vazio: nao ha faixa atingida nem "proxima
        # faixa" a exibir ainda -- so aparece depois do primeiro item.
        return {
            "quantidade_total": 0,
            "faixa_label": "",
            "faixa_atual_inicio": 0,
            "proxima_faixa": None,
        }
    return {
        "quantidade_total": quantidade_total_grupo,
        "faixa_label": faixa_label(chave_referencia, quantidade_total_grupo),
        "faixa_atual_inicio": _faixa_atual(chave_referencia, quantidade_total_grupo)[0],
        "proxima_faixa": proxima_faixa(chave_referencia, quantidade_total_grupo),
    }


def calcular_carrinho(itens: list[dict]) -> dict:
    """
    Recalcula o carrinho inteiro de uma vez, respeitando os grupos de
    atacado independentes (ver docstring do modulo): soma a quantidade
    TOTAL de cada grupo separadamente, acha a faixa de cada grupo, e
    aplica o preco da faixa do GRUPO CORRESPONDENTE em cada item.

    `itens` e uma lista de {"chave_preco": "12mm"|"16mm"|"entremeio"|
    "chaveiro", "quantidade": int}. A ordem da lista de retorno espelha a
    ordem recebida.
    """
    quantidade_por_grupo = {g: 0 for g in GRUPOS}
    chave_referencia_por_grupo: dict[str, str] = {}
    for item in itens:
        grupo = GRUPO_DE_CHAVE[item["chave_preco"]]
        quantidade_por_grupo[grupo] += item["quantidade"]
        chave_referencia_por_grupo.setdefault(grupo, item["chave_preco"])
    # "padrao" tem 3 chaves possiveis com a mesma tabela hoje -- qualquer
    # uma serve de referencia pro rotulo/proxima faixa do grupo. "chaveiro"
    # so tem a propria chave.
    chave_referencia_por_grupo.setdefault("padrao", "16mm")
    chave_referencia_por_grupo.setdefault("chaveiro", "chaveiro")

    itens_calculados = []
    subtotal_total = 0.0
    subtotal_por_grupo = {g: 0.0 for g in GRUPOS}
    for item in itens:
        grupo = GRUPO_DE_CHAVE[item["chave_preco"]]
        preco_unitario = calcular_preco(item["chave_preco"], quantidade_por_grupo[grupo])
        subtotal = round(preco_unitario * item["quantidade"], 2)
        subtotal_total += subtotal
        subtotal_por_grupo[grupo] += subtotal
        itens_calculados.append(
            {**item, "preco_unitario": preco_unitario, "subtotal": subtotal}
        )
    subtotal_total = round(subtotal_total, 2)

    grupos_calculados = {
        g: _calcular_grupo(chave_referencia_por_grupo[g], quantidade_por_grupo[g])
        for g in GRUPOS
    }

    # Desconto de frete por atacado (ver DESCONTO_FRETE_ATACADO_PCT) --
    # soma 8% do subtotal de CADA grupo que, sozinho, ja atingiu a
    # propria primeira faixa de atacado (nao mistura grupo com grupo).
    desconto_frete_atacado = round(
        sum(
            subtotal_por_grupo[g] * DESCONTO_FRETE_ATACADO_PCT
            for g in GRUPOS
            if _grupo_atingiu_atacado(chave_referencia_por_grupo[g], quantidade_por_grupo[g])
        ),
        2,
    )

    frete_gratis = frete_gratis_reais()
    falta_frete = round(frete_gratis - subtotal_total, 2)

    return {
        "quantidade_total": sum(quantidade_por_grupo.values()),
        "grupos": grupos_calculados,
        "itens": itens_calculados,
        "subtotal_total": subtotal_total,
        "pedido_minimo_reais": pedido_minimo_reais(),
        "atinge_minimo": subtotal_total >= pedido_minimo_reais() if itens else True,
        "frete_gratis_reais": frete_gratis,
        "frete_gratis_atingido": subtotal_total >= frete_gratis if itens else False,
        "falta_para_frete_gratis": max(0.0, falta_frete) if itens else frete_gratis,
        "desconto_frete_atacado": desconto_frete_atacado,
    }
