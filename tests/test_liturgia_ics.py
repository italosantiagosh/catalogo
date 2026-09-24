from __future__ import annotations

from services.liturgia_ics import gerar_ics_liturgia_outubro
from services.liturgia_pdf import DIAS_OUTUBRO_2026
from app import app


def test_gera_um_evento_por_dia_de_outubro():
    ics = gerar_ics_liturgia_outubro("https://lojanovedejulho.com.br")
    assert ics.count("BEGIN:VEVENT") == len(DIAS_OUTUBRO_2026) == 31
    assert ics.startswith("BEGIN:VCALENDAR\r\n")
    assert ics.rstrip().endswith("END:VCALENDAR")


def test_datas_de_inicio_e_fim_sao_dia_inteiro_consecutivo():
    ics = gerar_ics_liturgia_outubro("https://lojanovedejulho.com.br")
    assert "DTSTART;VALUE=DATE:20261001" in ics
    assert "DTEND;VALUE=DATE:20261002" in ics
    assert "DTSTART;VALUE=DATE:20261012" in ics
    assert "DTEND;VALUE=DATE:20261013" in ics


def _desdobrar(ics: str) -> str:
    """RFC 5545: linha de continuacao comeca com um espaco que precisa
    ser removido pra reconstituir o texto original antes de comparar
    substring (ver services/liturgia_ics.py:_dobrar_linha)."""
    return ics.replace("\r\n ", "")


def test_escapa_caracteres_especiais_da_descricao():
    ics = _desdobrar(gerar_ics_liturgia_outubro("https://lojanovedejulho.com.br"))
    assert "confiança simples" in ics
    assert "\\," in ics


def test_links_de_medalha_e_novena_aparecem_na_descricao():
    ics = _desdobrar(gerar_ics_liturgia_outubro("https://lojanovedejulho.com.br"))
    assert "https://lojanovedejulho.com.br/produto/santa-teresinha" in ics
    assert "https://lojanovedejulho.com.br/blog/novena-de-santa-teresinha" in ics


def test_rota_ics_serve_com_content_type_correto():
    client = app.test_client()
    resposta = client.get("/ebook/liturgia-do-mes.ics")
    assert resposta.status_code == 200
    assert resposta.headers["Content-Type"] == "text/calendar; charset=utf-8"
    assert resposta.data.count(b"BEGIN:VEVENT") == 31


def test_landing_linka_direto_pro_ics_sem_o_truque_quebrado_do_google():
    """Ver conversa 2026-09-24: o link calendar.google.com/calendar/render
    ?cid=... deu erro no celular do usuario -- trocado pelo link direto
    pro .ics, que o proprio navegador/SO sabe abrir em qualquer app de
    calendario (Google, Apple, Outlook)."""
    resposta = app.test_client().get("/liturgia-do-mes")
    assert b"calendar.google.com/calendar/render" not in resposta.data
    assert b"/ebook/liturgia-do-mes.ics" in resposta.data
