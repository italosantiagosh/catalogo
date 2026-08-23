"""
Gera o PDF do catalogo completo -- orientacoes de pedido, tabela de
precos de atacado e a foto + nome de cada santo/devocao -- servido
pelo botao "Baixar catalogo em PDF" na home (rota /catalogo.pdf em
app.py).

O catalogo (data/produtos.json + imagens em static/img/produtos) e
estatico -- muda so quando alguem edita o repositorio, nunca em tempo
de execucao -- entao o PDF e gerado uma vez por processo e mantido em
_cache_pdf; downloads seguintes servem o mesmo PDF sem regerar (a
geracao com ~130 fotos leva alguns segundos). Como o app roda com
--workers 1 (ver docstring de app.py sobre os tokens de download em
memoria), esse cache global e seguro sem precisar de lock.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image as PilImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from services.catalogo import carregar_produtos
from services.pricing import carregar_precos

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

COR_MARCA = colors.HexColor("#16305c")
COR_OURO = colors.HexColor("#b8860b")
COR_LINHA = colors.HexColor("#dddddd")
COR_ZEBRA = colors.HexColor("#f5f2ea")

LADO_FOTO = 2.6 * cm
COLUNAS_GRADE = 4

# Fotos originais sao 480x480 (~40KB cada) -- com ~860 celulas no PDF
# (todos os modelos x formatos, pedido do usuario), embutir no tamanho
# original inchava o PDF pra quase 40MB. Reduz pra um tamanho de pixel
# que ainda fica nitido no tamanho impresso (LADO_FOTO) antes de
# embutir -- cai pra poucos MB.
LADO_FOTO_PX = 180
QUALIDADE_JPEG = 72

_cache_pdf: bytes | None = None
_cache_fotos: dict[str, io.BytesIO] = {}


def _estilos() -> dict:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", parent=base["Title"], textColor=COR_MARCA, fontSize=22),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base["Normal"], textColor=COR_OURO, fontSize=12, spaceAfter=14
        ),
        "secao": ParagraphStyle(
            "secao", parent=base["Heading2"], textColor=COR_MARCA, fontSize=13, spaceBefore=14, spaceAfter=6
        ),
        "categoria": ParagraphStyle(
            "categoria", parent=base["Heading3"], textColor=COR_MARCA, fontSize=11, spaceBefore=12, spaceAfter=6
        ),
        "corpo": ParagraphStyle("corpo", parent=base["Normal"], fontSize=9.5, leading=13.5),
        "produto_nome": ParagraphStyle(
            "produto_nome", parent=base["Normal"], fontSize=7.5, alignment=1, leading=9
        ),
    }


def _paragrafo_orientacoes(estilos: dict) -> list:
    precos = carregar_precos()
    pedido_minimo = f"{precos['pedido_minimo_reais']:.2f}".replace(".", ",")
    frete_gratis = f"{precos['frete_gratis_reais']:.2f}".replace(".", ",")
    return [
        Paragraph("Nove de Julho", estilos["titulo"]),
        Paragraph("Catálogo de atacado — medalhas, entremeios e chaveiros", estilos["subtitulo"]),
        Paragraph("Como pedir", estilos["secao"]),
        Paragraph(
            "Monte seu pedido pelo catálogo online e finalize direto pelo WhatsApp — sem "
            "cadastro, sem burocracia. O desconto de atacado é aplicado automaticamente "
            "conforme a quantidade adicionada ao carrinho, sem cupom.",
            estilos["corpo"],
        ),
        Paragraph("Pedido mínimo e frete", estilos["secao"]),
        Paragraph(
            f"Pedido mínimo de R$ {pedido_minimo}. Frete grátis para pedidos acima de "
            f"R$ {frete_gratis} — fora isso, o frete é calculado no carrinho pelo CEP de "
            "destino (Correios, Azul Express, LATAM Cargo, J&amp;T Express e outras "
            "transportadoras).",
            estilos["corpo"],
        ),
        Paragraph("Pagamento", estilos["secao"]),
        Paragraph(
            "Os valores deste catálogo são para pagamento à vista via Pix. Boleto também à "
            "vista (não parcelado/faturado) e cartão (com taxas à parte) mediante pedido "
            "pelo WhatsApp. Emitimos nota fiscal para CNPJ ou CPF.",
            estilos["corpo"],
        ),
        Paragraph("Prazo de produção", estilos["secao"]),
        Paragraph(
            "Após o pagamento confirmado, a produção do pedido tem prazo de até 5 dias "
            "úteis antes do envio.",
            estilos["corpo"],
        ),
        Paragraph("Desconto progressivo", estilos["secao"]),
        Paragraph(
            "Medalhas (12mm/16mm) e entremeios somam juntos para a faixa de desconto — pode "
            "misturar livremente santos, tamanhos e cores no mesmo pedido. Chaveiros têm "
            "tabela de atacado própria, contada separadamente. Veja as faixas completas na "
            "próxima página.",
            estilos["corpo"],
        ),
        Paragraph("Medalha personalizada", estilos["secao"]),
        Paragraph(
            "Envie a foto da sua devoção e veja a simulação da medalha antes de pedir, direto "
            "no catálogo online.",
            estilos["corpo"],
        ),
    ]


def _tabela_faixas(tabela: dict, estilos: dict) -> Table:
    linhas = [["A partir de", "Preço por unidade"]]
    for inicio, preco in sorted((int(k), v) for k, v in tabela.items()):
        linhas.append([f"{inicio} un.", f"R$ {preco:.2f}".replace(".", ",")])
    tabela_pdf = Table(linhas, colWidths=[4.5 * cm, 4.5 * cm])
    tabela_pdf.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COR_MARCA),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, COR_LINHA),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COR_ZEBRA]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tabela_pdf


def _paginas_precos(estilos: dict) -> list:
    precos = carregar_precos()
    return [
        Paragraph("Tabela de preços de atacado", estilos["titulo"]),
        Paragraph(
            "Medalhas (12mm/16mm) e entremeios — mesma tabela, faixas somadas juntas",
            estilos["categoria"],
        ),
        _tabela_faixas(precos["16mm"], estilos),
        Spacer(1, 0.7 * cm),
        Paragraph("Chaveiros — tabela própria", estilos["categoria"]),
        _tabela_faixas(precos["chaveiro"], estilos),
        PageBreak(),
    ]


# Cada modelo de um produto tem ate 4 fotos -- uma por formato/cor (ver
# services/catalogo.py). Medalha e uma so foto pro modelo (12mm/16mm sao
# so o tamanho fisico impresso, a simulacao visual e identica -- mesmo
# criterio de FORMATO_PARA_SPEC em app.py), mas entremeio tem as 2 cores
# e chaveiro tem a propria foto -- pedido do usuario pra aparecerem
# todas no PDF, nao so a medalha.
FORMATOS_MODELO = [
    ("Medalha", "imagem"),
    ("Entremeio prata", "imagem_entremeio_prata"),
    ("Entremeio ouro velho", "imagem_entremeio_ouro_velho"),
    ("Chaveiro", "imagem_chaveiro"),
]


def _foto_reduzida(caminho_relativo: str) -> io.BytesIO | None:
    """Reabre a foto original, redimensiona pro tamanho de exibicao no
    PDF e reencoda em JPEG -- cacheada por caminho pra nao reprocessar a
    mesma foto 2x (medalha e chaveiro de modelos diferentes podem
    reaproveitar a mesma imagem base em alguns produtos)."""
    if caminho_relativo in _cache_fotos:
        _cache_fotos[caminho_relativo].seek(0)
        return _cache_fotos[caminho_relativo]
    caminho = STATIC_DIR / caminho_relativo
    try:
        with PilImage.open(caminho) as imagem:
            imagem = imagem.convert("RGB")
            imagem.thumbnail((LADO_FOTO_PX, LADO_FOTO_PX), PilImage.LANCZOS)
            buffer = io.BytesIO()
            imagem.save(buffer, format="JPEG", quality=QUALIDADE_JPEG)
    except Exception:
        return None
    buffer.seek(0)
    _cache_fotos[caminho_relativo] = buffer
    return buffer


def _celula_modelo(nome_produto: str, modelo: dict, rotulo_formato: str, caminho_imagem: str, estilos: dict) -> Table:
    buffer = _foto_reduzida(caminho_imagem)
    if buffer is not None:
        foto = RLImage(buffer, width=LADO_FOTO, height=LADO_FOTO)
    else:
        foto = Spacer(LADO_FOTO, LADO_FOTO)
    legenda = f"{nome_produto}<br/>Modelo {modelo['id']} · {rotulo_formato}"
    texto = Paragraph(legenda, estilos["produto_nome"])
    celula = Table([[foto], [texto]], colWidths=[LADO_FOTO + 0.4 * cm])
    celula.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    return celula


def _celulas_produto(produto: dict, estilos: dict) -> list[Table]:
    celulas = []
    for modelo in produto["modelos"]:
        for rotulo_formato, campo_imagem in FORMATOS_MODELO:
            caminho_imagem = modelo.get(campo_imagem)
            if not caminho_imagem:
                continue
            celulas.append(_celula_modelo(produto["nome"], modelo, rotulo_formato, caminho_imagem, estilos))
    return celulas


def _grade(celulas: list[Table]) -> Table:
    celulas = list(celulas)
    while len(celulas) % COLUNAS_GRADE:
        celulas.append("")
    linhas = [celulas[i : i + COLUNAS_GRADE] for i in range(0, len(celulas), COLUNAS_GRADE)]
    grade = Table(linhas, colWidths=[(LADO_FOTO + 0.4 * cm)] * COLUNAS_GRADE)
    grade.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return grade


def _paginas_catalogo(produtos: list[dict], estilos: dict) -> list:
    # Sem separar por categoria (pedido do usuario) -- uma grade so, com
    # todos os modelos/formatos de todos os santos, em ordem alfabetica.
    celulas: list[Table] = []
    for produto in sorted(produtos, key=lambda p: p["nome"]):
        celulas += _celulas_produto(produto, estilos)
    return [Paragraph("Catálogo completo", estilos["titulo"]), _grade(celulas)]


def gerar_pdf_catalogo() -> bytes:
    global _cache_pdf
    if _cache_pdf is not None:
        return _cache_pdf

    estilos = _estilos()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        title="Catálogo Nove de Julho",
    )

    story: list = []
    story += _paragrafo_orientacoes(estilos)
    story.append(PageBreak())
    story += _paginas_precos(estilos)
    story += _paginas_catalogo(carregar_produtos(), estilos)
    doc.build(story)

    _cache_pdf = buffer.getvalue()
    return _cache_pdf
