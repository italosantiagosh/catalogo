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


def test_paginas_precos_inclui_tabela_e_imagem_de_2lados():
    """Ver conversa: faltava a tabela de atacado de 2 lados no PDF --
    tabela propria (mesmos precos de medalha_2lados/entremeio_2lados) +
    a imagem ilustrativa do combo Teresinha/Sagrada Face logo abaixo,
    sem grade de fotos por santo (essa base ainda nao tem todo o
    catalogo com foto propria no PDF). Cabecalho+tabela+imagem viajam
    num KeepTogether (ver _bloco_precos_2lados) -- por isso o teste olha
    tambem dentro de ._content, nao so na lista plana."""
    from reportlab.platypus import Image as RLImage, KeepTogether

    estilos = catalogo_pdf._estilos()
    elementos = catalogo_pdf._paginas_precos(estilos)
    achatados = []
    for e in elementos:
        achatados += e._content if isinstance(e, KeepTogether) else [e]
    textos = [e.text for e in achatados if hasattr(e, "text")]
    assert any("2 lados" in t for t in textos)
    assert any(isinstance(e, RLImage) for e in achatados)


def test_itens_kit_bate_com_a_configuracao(monkeypatch):
    from config import KIT_LIVRARIA_SHALOM
    from services.catalogo import carregar_produtos

    itens = catalogo_pdf._itens_kit(carregar_produtos())
    assert len(itens) == len(KIT_LIVRARIA_SHALOM)
    assert sum(qtd for _, qtd in itens) == sum(e["quantidade_sugerida"] for e in KIT_LIVRARIA_SHALOM)
    nomes = [nome for nome, _ in itens]
    assert any("modelo longe" in nome for nome in nomes)
    assert any("modelo perto" in nome for nome in nomes)
