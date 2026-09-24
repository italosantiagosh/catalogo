from __future__ import annotations

from pathlib import Path

import services.liturgia_pdf as liturgia_pdf


def test_gera_pdf_valido(monkeypatch):
    monkeypatch.setattr(liturgia_pdf, "_cache_pdf", None)
    pdf = liturgia_pdf.gerar_pdf_liturgia_outubro("https://lojanovedejulho.com.br")
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 50_000


def test_cache_devolve_os_mesmos_bytes(monkeypatch):
    monkeypatch.setattr(liturgia_pdf, "_cache_pdf", None)
    primeiro = liturgia_pdf.gerar_pdf_liturgia_outubro("https://lojanovedejulho.com.br")
    segundo = liturgia_pdf.gerar_pdf_liturgia_outubro("https://outro-dominio-ignorado.com.br")
    assert primeiro == segundo


def test_nenhum_botao_usa_seta_unicode_sem_glifo_na_fonte():
    """Regressao: nenhuma das fontes embutidas (static/fonts/Fraunces*
    e PublicSans*) tem o glifo "→" -- reportlab descarta o caractere
    sem avisar, o botao saia sem seta nenhuma (ver conversa 2026-09-24).
    Todo botao deve usar "->" em vez do caractere unicode."""
    codigo = Path(liturgia_pdf.__file__).read_text(encoding="utf-8")
    assert "→" not in codigo


def test_dias_com_novena_slug_tem_bio_e_produto():
    dias_com_novena = [d for d in liturgia_pdf.DIAS_OUTUBRO_2026 if d.get("novena_slug")]
    assert len(dias_com_novena) == 5
    for info in dias_com_novena:
        assert info["bio"]
        assert info["produto_id"]


def test_todo_dia_tem_cor_liturgica_valida():
    for info in liturgia_pdf.DIAS_OUTUBRO_2026:
        assert info["cor_liturgica"] in liturgia_pdf.COR_LITURGICA_HEX, info["dia"]


def test_martires_e_apostolos_de_outubro_sao_vermelho():
    """Cunhau/Uruacu (3), Inacio de Antioquia (17, martir) e Simao e
    Judas (28, apostolos) sao os 3 dias de outubro/2026 com veste
    vermelha -- conferido contra o Diretorio da Liturgia 2026/CNBB."""
    por_dia = {d["dia"]: d for d in liturgia_pdf.DIAS_OUTUBRO_2026}
    for dia in (3, 17, 28):
        assert por_dia[dia]["cor_liturgica"] == "vermelho"
