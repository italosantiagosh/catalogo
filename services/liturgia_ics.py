"""
Gera o feed de calendario (.ics) da "Liturgia do mes" -- complemento do
e-book em PDF (ver services/liturgia_pdf.py, mesmos dados de
DIAS_OUTUBRO_2026): a pessoa assina o calendario uma vez (botao
"Adicionar ao Google Calendar" na landing /liturgia-do-mes) e cada dia
entra sozinho na agenda dela, como evento de dia inteiro com o
santo/tempo liturgico e a leitura do dia.

Inclui o restante de setembro (dia 25 em diante, ver conversa
2026-09-25 -- o PDF em si e´ so de outubro, mas a assinatura do
calendario pode comecar a valer imediatamente) mais outubro inteiro,
mesmos dados do widget "liturgia de hoje" (services/liturgia_hoje.py:
DIAS_SETEMBRO_2026).

Formato RFC 5545 (iCalendar) escrito a mao -- nao precisa de
dependencia nova pra isso, e´ so um arquivo de texto com um bloco
VEVENT por dia. Sem VALARM proposital: calendarios assinados
(subscribed, so leitura) no Google Calendar ignoram o VALARM do feed e
aplicam a notificacao padrao da pessoa pra aquele calendario -- entao
declarar um horario de lembrete aqui seria promessa vazia.
"""

from __future__ import annotations

import datetime

from services.liturgia_pdf import DIAS_OUTUBRO_2026, ROTULO_RANK_FRASE, ROTULO_COR_LITURGICA
from services.liturgia_hoje import DIAS_SETEMBRO_2026

# (ano, mes, uid-slug, lista de dias) -- setembro so a partir do dia 25
# porque e´ quando essa assinatura foi lancada (dias anteriores ja
# passaram, nao faz sentido oferecer evento pra data que ja foi).
_MESES_DO_FEED = [
    (2026, 9, "setembro", [d for d in DIAS_SETEMBRO_2026 if d["dia"] >= 25]),
    (2026, 10, "outubro", DIAS_OUTUBRO_2026),
]

_LIMITE_LINHA = 75


def _escapar_ics(texto: str) -> str:
    return (
        texto.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _dobrar_linha(linha: str) -> str:
    """RFC 5545 exige quebrar linhas com mais de 75 octetos, continuando
    na linha seguinte com um espaco no inicio -- a maioria dos apps de
    calendario tolera linha longa, mas o Google as vezes trunca, entao
    vale fazer certo."""
    if len(linha.encode("utf-8")) <= _LIMITE_LINHA:
        return linha
    partes = []
    atual = linha
    while len(atual.encode("utf-8")) > _LIMITE_LINHA:
        corte = _LIMITE_LINHA
        while len(atual[:corte].encode("utf-8")) > _LIMITE_LINHA:
            corte -= 1
        partes.append(atual[:corte])
        atual = atual[corte:]
    partes.append(atual)
    return "\r\n ".join(partes)


def _descricao_evento(info: dict, base_url: str) -> str:
    linhas = [ROTULO_RANK_FRASE[info["rank"]]]
    if info.get("bio"):
        linhas.append(info["bio"])
    linhas.append(f"Leituras: {info['leituras']}")
    linhas.append(f"Cor litúrgica: {ROTULO_COR_LITURGICA[info['cor_liturgica']]}")
    if info.get("produto_id"):
        linhas.append(f"Ver medalha: {base_url}/produto/{info['produto_id']}")
    if info.get("novena_slug"):
        linhas.append(f"Ver novena completa: {base_url}/blog/{info['novena_slug']}")
    if info.get("blog_slug"):
        linhas.append(f"Ver artigo completo: {base_url}/blog/{info['blog_slug']}")
    return "\n".join(linhas)


def gerar_ics_liturgia_outubro(base_url: str) -> str:
    agora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    linhas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Nove de Julho//Liturgia do Mes//PT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Liturgia Diária — Nove de Julho",
        "X-WR-TIMEZONE:America/Sao_Paulo",
    ]
    for ano, mes, slug_mes, dias in _MESES_DO_FEED:
        for info in dias:
            data = datetime.date(ano, mes, info["dia"])
            proximo_dia = data + datetime.timedelta(days=1)
            # Nome do santo/tempo primeiro (ver conversa 2026-09-24: o app
            # de calendario trunca o titulo na visao de mes, e "MEMÓRIA
            # OBRIGATÓRIA..." cortado nao diz nada -- o nome e´ o que
            # importa pra reconhecer o dia de relance).
            resumo = f"{info['titulo']} ({ROTULO_RANK_FRASE[info['rank']]})" if info["rank"] != "comum" else info["titulo"]
            linhas += [
                "BEGIN:VEVENT",
                f"UID:liturgia-{slug_mes}-{ano}-{info['dia']:02d}@lojanovedejulho.com.br",
                f"DTSTAMP:{agora}",
                f"DTSTART;VALUE=DATE:{data.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{proximo_dia.strftime('%Y%m%d')}",
                _dobrar_linha(f"SUMMARY:{_escapar_ics(resumo)}"),
                _dobrar_linha(f"DESCRIPTION:{_escapar_ics(_descricao_evento(info, base_url))}"),
                "END:VEVENT",
            ]
    linhas.append("END:VCALENDAR")
    return "\r\n".join(linhas) + "\r\n"
