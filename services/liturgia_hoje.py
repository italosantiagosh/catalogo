"""
Widget "liturgia de hoje" da home (ver templates/index.html) -- teaser
gratis com o tempo/santo do dia, puxando da mesma familia de dados do
e-book (services/liturgia_pdf.py:DIAS_OUTUBRO_2026) mais o mes de
setembro aqui embaixo, pra ter conteudo real ja no ar mesmo antes de
outubro comecar (ver conversa 2026-09-24: "precisa ter la os de
setembro, porque outubro ainda nao começou").

So cobre 2026 (mesmo motivo do aviso em liturgia_pdf.py: leituras e
calendario mudam a cada ano) -- em outro ano, ou fora de
setembro/outubro, o widget simplesmente nao aparece (contexto_liturgia_
de_hoje devolve None), nao mostra dado errado.
"""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from services.liturgia_pdf import DIAS_OUTUBRO_2026, ROTULO_COR_LITURGICA, ROTULO_RANK_FRASE

FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")

# Mesma fonte/conferencia do DIAS_OUTUBRO_2026 (Diretorio da Liturgia
# 2026/CNBB) -- so rank/leituras/cor, sem bio/produto: aqui e´ so o
# teaser da home, quem quiser mais baixa o e-book de outubro.
DIAS_SETEMBRO_2026 = [
    {"dia": 1, "titulo": "22ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "1Cor 2,10b-16 · Sl 144(145) · Lc 4,31-37"},
    {"dia": 2, "titulo": "22ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "1Cor 3,1-9 · Sl 32(33) · Lc 4,38-44"},
    {"dia": 3, "titulo": "São Gregório Magno, papa e doutor da Igreja", "rank": "obrigatoria", "cor_liturgica": "branco",
     "leituras": "1Cor 3,18-23 · Sl 23(24) · Lc 5,1-11"},
    {"dia": 4, "titulo": "22ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "1Cor 4,1-5 · Sl 36(37) · Lc 5,33-39"},
    {"dia": 5, "titulo": "22ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "1Cor 4,6b-15 · Sl 144(145) · Lc 6,1-5"},
    {"dia": 6, "titulo": "23º Domingo do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "Ez 33,7-9 · Sl 94(95) · Rm 13,8-10 · Mt 18,15-20"},
    {"dia": 7, "titulo": "23ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "1Cor 5,1-8 · Sl 5 · Lc 6,6-11"},
    {"dia": 8, "titulo": "Natividade da Bem-Aventurada Virgem Maria", "rank": "festa", "cor_liturgica": "branco",
     "leituras": "Mq 5,1-4a ou Rm 8,28-30 · Sl 70(71);12(13) · Mt 1,1-16.18-23"},
    {"dia": 9, "titulo": "23ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "1Cor 7,25-31 · Sl 44(45) · Lc 6,20-26"},
    {"dia": 10, "titulo": "23ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "1Cor 8,1b-7.11-13 · Sl 138(139) · Lc 6,27-38"},
    {"dia": 11, "titulo": "23ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "1Cor 9,16-19.22b-27 · Sl 83(84) · Lc 6,39-42"},
    {"dia": 12, "titulo": "23ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "1Cor 10,14-22 · Sl 115(116) · Lc 6,43-49"},
    {"dia": 13, "titulo": "24º Domingo do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "Eclo 27,33-28,9 · Sl 102(103) · Rm 14,7-9 · Mt 18,21-35"},
    {"dia": 14, "titulo": "Exaltação da Santa Cruz", "rank": "festa", "cor_liturgica": "vermelho",
     "leituras": "Nm 21,4b-9 ou Fl 2,6-11 · Sl 77(78) · Jo 3,13-17"},
    {"dia": 15, "titulo": "Nossa Senhora das Dores", "rank": "obrigatoria", "cor_liturgica": "branco",
     "leituras": "Hb 5,7-9 · Sl 30(31) · Jo 19,25-27 ou Lc 2,33-35"},
    {"dia": 16, "titulo": "Santos Cornélio, papa, e Cipriano, bispo, mártires", "rank": "obrigatoria", "cor_liturgica": "vermelho",
     "leituras": "1Cor 12,31-13,13 · Sl 32(33) · Lc 7,31-35"},
    {"dia": 17, "titulo": "24ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "1Cor 15,1-11 · Sl 117(118) · Lc 7,36-50"},
    {"dia": 18, "titulo": "24ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "1Cor 15,12-20 · Sl 16(17) · Lc 8,1-13"},
    {"dia": 19, "titulo": "24ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "1Cor 15,35-37.42-49 · Sl 55(56) · Lc 8,4-15"},
    {"dia": 20, "titulo": "25º Domingo do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "Is 55,6-9 · Sl 144(145) · Fl 1,20c-24.27a · Mt 20,1-16a"},
    {"dia": 21, "titulo": "São Mateus, apóstolo e evangelista", "rank": "festa", "cor_liturgica": "vermelho",
     "leituras": "Ef 4,1-7.11-13 · Sl 18(19A) · Mt 9,9-13"},
    {"dia": 22, "titulo": "25ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "Pr 21,1-6.10-13 · Sl 118(119) · Lc 8,19-21"},
    {"dia": 23, "titulo": "São Pio de Pietrelcina, presbítero", "rank": "obrigatoria", "cor_liturgica": "branco",
     "leituras": "Pr 30,5-9 · Sl 118(119) · Lc 9,1-6"},
    {"dia": 24, "titulo": "25ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "Ecl 1,2-11 · Sl 89(90) · Lc 9,7-9"},
    {"dia": 25, "titulo": "25ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "Ecl 3,1-11 · Sl 143(144) · Lc 9,18-22"},
    {"dia": 26, "titulo": "25ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "Ecl 11,9-12,8 · Sl 89(90) · Lc 9,43b-45"},
    {"dia": 27, "titulo": "26º Domingo do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "Ez 18,25-28 · Sl 24(25) · Fl 2,1-11 · Mt 21,28-32"},
    {"dia": 28, "titulo": "26ª Semana do Tempo Comum", "rank": "comum", "cor_liturgica": "verde",
     "leituras": "Jó 1,6-22 · Sl 16(17) · Lc 9,46-50"},
    {"dia": 29, "titulo": "Santos Miguel, Gabriel e Rafael, arcanjos", "rank": "festa", "cor_liturgica": "branco",
     "leituras": "Dn 7,9-10.13-14 ou Ap 12,7-12a · Sl 137(138) · Jo 1,47-51"},
    {"dia": 30, "titulo": "São Jerônimo, presbítero e doutor da Igreja", "rank": "obrigatoria", "cor_liturgica": "branco",
     "leituras": "Jó 9,1-12.14-16 · Sl 87(88) · Lc 9,57-62"},
]

_MESES_DISPONIVEIS = {9: DIAS_SETEMBRO_2026, 10: DIAS_OUTUBRO_2026}
_NOME_MES = {9: "setembro", 10: "outubro"}

# Mesmas cores de COR_RANK em services/liturgia_pdf.py, mas como string
# hex simples (aquele dict usa colors.HexColor do reportlab, so serve
# dentro de um PDF -- aqui e´ pra CSS/HTML).
COR_RANK_HEX = {
    "solenidade": "#b8860b",
    "festa": "#8a2f22",
    "obrigatoria": "#16305c",
    "facultativa": "#8a8578",
    "comum": "#3d6b4f",
}


def liturgia_de_hoje(hoje: datetime.date | None = None) -> dict | None:
    hoje = hoje or datetime.datetime.now(FUSO_BRASILIA).date()
    if hoje.year != 2026:
        return None
    dias = _MESES_DISPONIVEIS.get(hoje.month)
    if dias is None:
        return None
    return next((d for d in dias if d["dia"] == hoje.day), None)


def contexto_liturgia_de_hoje(hoje: datetime.date | None = None) -> dict | None:
    """Pronto pro template (ver templates/index.html) -- devolve None
    quando nao ha´ dado pro dia de hoje (fora de set/out de 2026), e o
    widget simplesmente nao renderiza."""
    hoje = hoje or datetime.datetime.now(FUSO_BRASILIA).date()
    info = liturgia_de_hoje(hoje)
    if info is None:
        return None
    return {
        "data_extenso": f"{info['dia']} de {_NOME_MES[hoje.month]}",
        "titulo": info["titulo"],
        "leituras": info["leituras"],
        "rank_rotulo": ROTULO_RANK_FRASE[info["rank"]],
        "rank_cor_hex": COR_RANK_HEX[info["rank"]],
        "cor_liturgica_rotulo": ROTULO_COR_LITURGICA[info["cor_liturgica"]],
    }
