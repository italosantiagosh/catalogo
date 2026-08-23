from __future__ import annotations

import re

import services.catalogo_pdf as catalogo_pdf


def test_gerar_pdf_catalogo_produz_pdf_valido(monkeypatch):
    monkeypatch.setattr(catalogo_pdf, "_cache_pdf", None)
    pdf = catalogo_pdf.gerar_pdf_catalogo()
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_gerar_pdf_catalogo_usa_cache(monkeypatch):
    monkeypatch.setattr(catalogo_pdf, "_cache_pdf", None)
    primeiro = catalogo_pdf.gerar_pdf_catalogo()
    segundo = catalogo_pdf.gerar_pdf_catalogo()
    assert primeiro is segundo  # segunda chamada nao regera, devolve o cache


def test_gerar_pdf_catalogo_tem_uma_pagina_por_categoria_no_minimo(monkeypatch):
    monkeypatch.setattr(catalogo_pdf, "_cache_pdf", None)
    pdf = catalogo_pdf.gerar_pdf_catalogo()
    # heuristica simples sem depender de biblioteca externa de leitura de
    # PDF -- conta objetos "/Type /Page" (sem contar "/Type /Pages").
    paginas = len(re.findall(rb"/Type\s*/Page[^s]", pdf))
    assert paginas >= 3  # orientacoes + precos + pelo menos 1 de catalogo
