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
    assert paginas >= 4  # orientacoes + precos + kit + pelo menos 1 de catalogo


def test_itens_kit_bate_com_a_configuracao(monkeypatch):
    from config import KIT_LIVRARIA_SHALOM
    from services.catalogo import carregar_produtos

    itens = catalogo_pdf._itens_kit(carregar_produtos())
    assert len(itens) == len(KIT_LIVRARIA_SHALOM)
    assert sum(qtd for _, qtd in itens) == sum(e["quantidade_sugerida"] for e in KIT_LIVRARIA_SHALOM)
    nomes = [nome for nome, _ in itens]
    assert any("modelo longe" in nome for nome in nomes)
    assert any("modelo perto" in nome for nome in nomes)
