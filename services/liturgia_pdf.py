"""
Gera o e-book "Liturgia de Outubro" (2026) -- isca de e-mail oferecida
na landing /liturgia-de-outubro: tempo/santo de cada um dos 31 dias do
mes, referencia da leitura do dia (sem o texto completo -- so a
citacao, ver conversa 2026-09-24 sobre direito autoral) e, nos dias de
santo do catalogo, uma bio curta + link pra medalha.

Calendario liturgico de outubro/2026 (DIAS_OUTUBRO_2026 abaixo) foi
conferido contra o Diretorio da Liturgia da Igreja no Brasil / CNBB
2026 e o calendario romano geral -- especifico deste ano e deste mes,
NAO reaproveitar sem revisar de novo se algum dia isso virar recorrente
pra outros meses/anos (ordem das leituras da semana muda a cada ano,
memorias opcionais e domingos que "engolem" a memoria do santo tambem).

Mesmo padrao de services/catalogo_pdf.py: reportlab/platypus, fotos
reduzidas e cacheadas, PDF montado uma vez e cacheado em memoria.
"""

from __future__ import annotations

import datetime
import io
from pathlib import Path

from PIL import Image as PilImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image as RLImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from services.catalogo import carregar_produtos

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
FONTS_DIR = STATIC_DIR / "fonts"

COR_MARCA = colors.HexColor("#16305c")
COR_OURO = colors.HexColor("#b8860b")
COR_LINHA = colors.HexColor("#dddddd")
COR_FUNDO_SUAVE = colors.HexColor("#f5f2ea")
COR_TEXTO_MUTED = colors.HexColor("#5b6b82")

# cores por grau liturgico -- usadas no selo de cada dia em destaque E
# na grade-resumo do mes (pagina 2), pra quem folheia rapido reconhecer
# o padrao visualmente (pedido do usuario: "bonito pro jovem, facil pro
# idoso" -- cor + rotulo por extenso cobre os dois).
COR_RANK = {
    "solenidade": colors.HexColor("#b8860b"),
    "festa": colors.HexColor("#8a2f22"),
    "obrigatoria": colors.HexColor("#16305c"),
    "facultativa": colors.HexColor("#8a8578"),
    "comum": colors.HexColor("#3d6b4f"),
}
ROTULO_RANK = {
    "solenidade": "SOLENIDADE",
    "festa": "FESTA",
    "obrigatoria": "MEMÓRIA OBRIGATÓRIA",
    "facultativa": "MEMÓRIA FACULTATIVA",
    "comum": "TEMPO COMUM",
}

LADO_FOTO_DIA = 3.2 * cm
LADO_FOTO_DIA_PX = 220
QUALIDADE_JPEG = 78

_FONTES_REGISTRADAS = False


def _registrar_fontes() -> None:
    """As mesmas familias do site (Fraunces nos titulos, Public Sans no
    corpo -- ver static/css/style.css:--fonte-titulo/--fonte-corpo),
    embutidas como TTF em static/fonts/ pra nao depender de rede na
    hora de gerar o PDF. Idempotente: reportlab reclama se registrar a
    mesma fonte 2x no mesmo processo."""
    global _FONTES_REGISTRADAS
    if _FONTES_REGISTRADAS:
        return
    pdfmetrics.registerFont(TTFont("Fraunces-SemiBold", str(FONTS_DIR / "Fraunces-SemiBold.ttf")))
    pdfmetrics.registerFont(TTFont("Fraunces-Bold", str(FONTS_DIR / "Fraunces-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("PublicSans", str(FONTS_DIR / "PublicSans-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("PublicSans-SemiBold", str(FONTS_DIR / "PublicSans-SemiBold.ttf")))
    pdfmetrics.registerFont(TTFont("PublicSans-Bold", str(FONTS_DIR / "PublicSans-Bold.ttf")))
    _FONTES_REGISTRADAS = True


def _estilos() -> dict:
    _registrar_fontes()
    return {
        "capa_titulo": ParagraphStyle(
            "capa_titulo", fontName="Fraunces-Bold", fontSize=34, leading=38,
            textColor=COR_MARCA, alignment=1,
        ),
        "capa_subtitulo": ParagraphStyle(
            "capa_subtitulo", fontName="PublicSans-SemiBold", fontSize=15, leading=20,
            textColor=COR_OURO, alignment=1, spaceBefore=10,
        ),
        "capa_rodape": ParagraphStyle(
            "capa_rodape", fontName="PublicSans", fontSize=10.5, leading=15,
            textColor=COR_TEXTO_MUTED, alignment=1, spaceBefore=26,
        ),
        "secao_titulo": ParagraphStyle(
            "secao_titulo", fontName="Fraunces-Bold", fontSize=19, leading=23,
            textColor=COR_MARCA, spaceAfter=10,
        ),
        "legenda_corpo": ParagraphStyle(
            "legenda_corpo", fontName="PublicSans", fontSize=11, leading=16.5,
            textColor=colors.HexColor("#142238"), spaceAfter=12,
        ),
        "dia_numero": ParagraphStyle(
            "dia_numero", fontName="Fraunces-Bold", fontSize=20, leading=22, alignment=1,
        ),
        "dia_titulo_compacto": ParagraphStyle(
            "dia_titulo_compacto", fontName="PublicSans-SemiBold", fontSize=10.5, leading=14.5,
            textColor=colors.HexColor("#142238"),
        ),
        "dia_leitura_compacta": ParagraphStyle(
            "dia_leitura_compacta", fontName="PublicSans", fontSize=9, leading=13,
            textColor=COR_TEXTO_MUTED, spaceBefore=2,
        ),
        "selo_rank": ParagraphStyle(
            "selo_rank", fontName="PublicSans-Bold", fontSize=8.5, leading=10,
            textColor=colors.white, alignment=1,
        ),
        "dia_titulo_grande": ParagraphStyle(
            "dia_titulo_grande", fontName="Fraunces-SemiBold", fontSize=15.5, leading=19,
            textColor=COR_MARCA, spaceBefore=6, spaceAfter=4,
        ),
        "dia_data_grande": ParagraphStyle(
            "dia_data_grande", fontName="PublicSans-SemiBold", fontSize=9.5, leading=13,
            textColor=COR_TEXTO_MUTED,
        ),
        "dia_bio": ParagraphStyle(
            "dia_bio", fontName="PublicSans", fontSize=10.5, leading=16,
            textColor=colors.HexColor("#142238"), spaceBefore=4, spaceAfter=8,
        ),
        "dia_leitura_grande": ParagraphStyle(
            "dia_leitura_grande", fontName="PublicSans", fontSize=9.5, leading=13,
            textColor=COR_TEXTO_MUTED,
        ),
        "botao_texto": ParagraphStyle(
            "botao_texto", fontName="PublicSans-Bold", fontSize=10.5, leading=13,
            textColor=colors.white, alignment=1,
        ),
        "indice_numero": ParagraphStyle(
            "indice_numero", fontName="PublicSans-Bold", fontSize=10, leading=12,
            textColor=colors.white, alignment=1,
        ),
        "cta_final_titulo": ParagraphStyle(
            "cta_final_titulo", fontName="Fraunces-SemiBold", fontSize=16, leading=20,
            textColor=COR_MARCA, alignment=1, spaceAfter=8,
        ),
        "cta_final_corpo": ParagraphStyle(
            "cta_final_corpo", fontName="PublicSans", fontSize=10.5, leading=16,
            textColor=COR_TEXTO_MUTED, alignment=1, spaceAfter=18,
        ),
    }


DIAS_PT = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]

# titulo: nome do santo/festa OU descricao do tempo comum (+ memorias
# opcionais nao destacadas, quando houver, numa linha soh informativa).
# bio/produto_id: só nos ~9 dias com destaque (conteudo reaproveitado
# dos artigos/novenas do blog, ver services/blog.py).
DIAS_OUTUBRO_2026 = [
    {"dia": 1, "titulo": "Santa Teresinha do Menino Jesus e da Sagrada Face", "rank": "obrigatoria",
     "leituras": "Jó 19,21-27 · Sl 26(27) · Lc 10,1-12", "produto_id": "santa-teresinha",
     "bio": "Carmelita descalça francesa, morreu aos 24 anos sem nunca ter saído do convento — "
            "e mesmo assim se tornou Doutora da Igreja e padroeira das missões, pelo seu "
            "\"caminhozinho\" de confiança simples em Deus. Uma das santas mais amadas por "
            "jovens no Brasil e no mundo.",
     "novena_slug": "novena-de-santa-teresinha"},
    {"dia": 2, "titulo": "Santos Anjos da Guarda", "rank": "obrigatoria",
     "leituras": "Êx 23,20-23 · Sl 90(91) · Mt 18,1-5.10", "produto_id": None,
     "bio": "A Igreja ensina que cada pessoa recebe de Deus um anjo pra guiá-la e protegê-la "
            "a vida inteira — uma das certezas mais simples e consoladoras da fé católica."},
    {"dia": 3, "titulo": "Beatos Mártires de Cunhaú e Uruaçu", "rank": "facultativa",
     "leituras": "Jó 42,1-3.5-6.12-16 · Sl 118(119) · Lc 10,17-24", "produto_id": "santos-martires-do-rn",
     "bio": "Em 1645, durante a invasão holandesa no litoral potiguar, dois grupos de fiéis "
            "foram mortos por se recusarem a abandonar a fé católica — os primeiros santos "
            "nascidos em solo brasileiro, canonizados em 2017."},
    {"dia": 4, "titulo": "27º Domingo do Tempo Comum — tradicionalmente, dia de São Francisco de Assis",
     "rank": "comum", "leituras": "Is 5,1-7 · Sl 79(80) · Fl 4,6-9 · Mt 21,33-43", "produto_id": "sao-francisco",
     "bio": "Filho de comerciante rico que trocou tudo pela pobreza radical, fundou a ordem "
            "franciscana e é hoje um dos santos mais universalmente amados, dentro e fora da "
            "Igreja — padroeiro da ecologia e dos animais. Em 2026 seu dia cai num domingo, "
            "que \"tem precedência\" no calendário — mas a devoção popular segue firme.",
     "novena_slug": "novena-de-sao-francisco-de-assis"},
    {"dia": 5, "titulo": "27ª Semana do Tempo Comum · opcional: São Bento, o Preto, religioso",
     "rank": "comum", "leituras": "Gl 1,6-12 · Sl 110(111) · Lc 10,25-37", "produto_id": None, "bio": None},
    {"dia": 6, "titulo": "Santa Faustina Kowalska · opcional também: São Bruno, presbítero",
     "rank": "facultativa", "leituras": "Gl 1,13-24 · Sl 138(139) · Lc 10,38-42", "produto_id": "santa-faustina",
     "bio": "Freira polonesa simples que recebeu de Jesus a mensagem da Divina Misericórdia — "
            "a imagem \"Jesus, eu confio em Vós\", hoje presente em incontáveis lares "
            "católicos, nasceu das visões dela."},
    {"dia": 7, "titulo": "Nossa Senhora do Rosário", "rank": "obrigatoria",
     "leituras": "At 1,12-14 · Lc 1,46-55 · Lc 1,26-38", "produto_id": "nossa-senhora-do-rosario",
     "bio": "Instituída no século 16 após a vitória na Batalha de Lepanto, atribuída à "
            "intercessão de Maria através do terço, a festa celebra a mesma oração repetida "
            "há séculos em lares católicos — inclusive no coração da devoção brasileira."},
    {"dia": 8, "titulo": "27ª Semana do Tempo Comum", "rank": "comum",
     "leituras": "Gl 3,1-5 · Sl (Lc 1) · Lc 11,5-13", "produto_id": None, "bio": None},
    {"dia": 9, "titulo": "27ª Semana do Tempo Comum · opcional: São Dionísio e companheiros; São João Leonardi",
     "rank": "comum", "leituras": "Gl 3,7-14 · Sl 110(111) · Lc 11,15-26", "produto_id": None, "bio": None},
    {"dia": 10, "titulo": "27ª Semana do Tempo Comum", "rank": "comum",
     "leituras": "Gl 3,22-29 · Sl 104(105) · Lc 11,27-28", "produto_id": None, "bio": None},
    {"dia": 11, "titulo": "28º Domingo do Tempo Comum", "rank": "comum",
     "leituras": "Is 25,6-10a · Sl 22(23) · Fl 4,12-14.19-20 · Mt 22,1-14", "produto_id": None, "bio": None},
    {"dia": 12, "titulo": "Nossa Senhora Aparecida, padroeira do Brasil", "rank": "solenidade",
     "leituras": "Est 5,1b-2.7,2b-3 · Sl 44(45) · Ap 12,1.5.13a.15-16a · Jo 2,1-11",
     "produto_id": "nossa-senhora-aparecida",
     "bio": "Padroeira do Brasil desde 1930, a imagem foi encontrada por pescadores no rio "
            "Paraíba do Sul em 1717 — hoje é venerada no maior santuário mariano do mundo, em "
            "Aparecida (SP). É também, por coincidência marcante, o dia em que São Carlo "
            "Acutis partiu para o Céu em 2006, aos 15 anos.",
     "novena_slug": "novena-de-nossa-senhora-aparecida",
     "produto_extra_id": "carlo-acutis", "produto_extra_rotulo": "Ver medalha de São Carlo Acutis ->",
     "produto_extra_novena_slug": "novena-de-sao-carlo-acutis"},
    {"dia": 13, "titulo": "28ª Semana do Tempo Comum", "rank": "comum",
     "leituras": "Gl 5,1-6 · Sl 118(119) · Lc 11,37-41", "produto_id": None, "bio": None},
    {"dia": 14, "titulo": "28ª Semana do Tempo Comum · opcional: São Calisto I, papa e mártir",
     "rank": "comum", "leituras": "Gl 5,18-25 · Sl 1 · Lc 11,42-46", "produto_id": None, "bio": None},
    {"dia": 15, "titulo": "Santa Teresa de Jesus (d'Ávila)", "rank": "obrigatoria",
     "leituras": "Ef 1,1-10 · Sl 97(98) · Lc 11,47-54", "produto_id": "santa-teresa-davila",
     "bio": "Reformadora do Carmelo no século 16, mística e Doutora da Igreja, escreveu sobre "
            "oração com uma clareza que atravessa séculos — ao lado de Santa Teresinha, uma "
            "das grandes referências vivas da espiritualidade carmelita.",
     "novena_slug": "novena-de-santa-teresa-davila"},
    {"dia": 16, "titulo": "28ª Semana do Tempo Comum · opcional: Santa Edviges; Santa Margarida Maria Alacoque",
     "rank": "comum", "leituras": "Ef 1,11-14 · Sl 32(33) · Lc 12,1-7", "produto_id": None, "bio": None},
    {"dia": 17, "titulo": "Santo Inácio de Antioquia", "rank": "obrigatoria",
     "leituras": "Ef 1,15-23 · Sl 8 · Lc 12,8-12", "produto_id": None,
     "bio": "Bispo de Antioquia e discípulo dos apóstolos, escreveu cartas cheias de fé a "
            "caminho do martírio em Roma, no início do século 2 — um dos elos mais diretos "
            "entre a Igreja de hoje e a geração que conheceu os apóstolos."},
    {"dia": 18, "titulo": "29º Domingo do Tempo Comum — tradicionalmente, dia de São Lucas Evangelista",
     "rank": "comum", "leituras": "Is 45,1.4-6 · Sl 95(96) · 1Ts 1,1-5b · Mt 22,15-21",
     "produto_id": None, "bio": None},
    {"dia": 19, "titulo": "29ª Semana do Tempo Comum · opcional: vários mártires e santos do dia",
     "rank": "comum", "leituras": "Ef 2,1-10 · Sl 99(100) · Lc 12,13-21", "produto_id": None, "bio": None},
    {"dia": 20, "titulo": "29ª Semana do Tempo Comum", "rank": "comum",
     "leituras": "Ef 2,12-22 · Sl 84(85) · Lc 12,35-38", "produto_id": None, "bio": None},
    {"dia": 21, "titulo": "29ª Semana do Tempo Comum", "rank": "comum",
     "leituras": "Ef 3,2-12 · Is 12 · Lc 12,39-48", "produto_id": None, "bio": None},
    {"dia": 22, "titulo": "São João Paulo II, papa", "rank": "facultativa",
     "leituras": "Ef 3,14-21 · Sl 32(33) · Lc 12,49-53", "produto_id": "sao-joao-paulo-ii",
     "bio": "Primeiro papa não-italiano em mais de 450 anos e sobrevivente de um atentado, "
            "João Paulo II liderou a Igreja por 27 anos e se tornou um dos maiores nomes "
            "religiosos do século 20 — especialmente querido pela juventude, que reunia às "
            "centenas de milhares nas Jornadas Mundiais.",
     "novena_slug": "novena-de-sao-joao-paulo-ii"},
    {"dia": 23, "titulo": "29ª Semana do Tempo Comum · opcional: São João de Capistrano, presbítero",
     "rank": "comum", "leituras": "Ef 4,1-6 · Sl 23(24) · Lc 12,54-59", "produto_id": None, "bio": None},
    {"dia": 24, "titulo": "29ª Semana do Tempo Comum · opcional: Santo Antônio Maria Claret, bispo",
     "rank": "comum", "leituras": "Ef 4,7-16 · Sl 121(122) · Lc 13,1-9", "produto_id": None, "bio": None},
    {"dia": 25, "titulo": "30º Domingo do Tempo Comum", "rank": "comum",
     "leituras": "Êx 22,20-26 · Sl 17(18) · 1Ts 1,5c-10 · Mt 22,34-40", "produto_id": None, "bio": None},
    {"dia": 26, "titulo": "30ª Semana do Tempo Comum", "rank": "comum",
     "leituras": "Ef 4,32–5,8 · Sl 1 · Lc 13,10-17", "produto_id": None, "bio": None},
    {"dia": 27, "titulo": "30ª Semana do Tempo Comum", "rank": "comum",
     "leituras": "Ef 5,21-33 · Sl 127(128) · Lc 13,18-21", "produto_id": None, "bio": None},
    {"dia": 28, "titulo": "Santos Simão e Judas Tadeu, Apóstolos", "rank": "festa",
     "leituras": "Ef 2,19-22 · Sl 18(19A) · Lc 6,12-19", "produto_id": "sao-judas-tadeu",
     "bio": "Judas Tadeu, apóstolo de Jesus e primo do Senhor, tornou-se o santo mais "
            "invocado nas causas urgentes e impossíveis — devoção especialmente forte no "
            "Brasil, com filas que dão volta ao quarteirão em seu dia."},
    {"dia": 29, "titulo": "30ª Semana do Tempo Comum", "rank": "comum",
     "leituras": "Ef 6,10-20 · Sl 143(144) · Lc 13,31-35", "produto_id": None, "bio": None},
    {"dia": 30, "titulo": "30ª Semana do Tempo Comum", "rank": "comum",
     "leituras": "Fl 1,1-11 · Sl 110(111) · Lc 14,1-6", "produto_id": None, "bio": None},
    {"dia": 31, "titulo": "30ª Semana do Tempo Comum", "rank": "comum",
     "leituras": "Fl 1,18b-26 · Sl 41(42) · Lc 14,1.7-11", "produto_id": None, "bio": None},
]

_cache_pdf: bytes | None = None
_cache_fotos: dict[tuple[str, int], io.BytesIO] = {}


def _foto_reduzida(caminho_relativo: str) -> io.BytesIO | None:
    chave_cache = (caminho_relativo, LADO_FOTO_DIA_PX)
    if chave_cache in _cache_fotos:
        _cache_fotos[chave_cache].seek(0)
        return _cache_fotos[chave_cache]
    caminho = STATIC_DIR / caminho_relativo
    try:
        with PilImage.open(caminho) as imagem:
            imagem = imagem.convert("RGB")
            imagem.thumbnail((LADO_FOTO_DIA_PX, LADO_FOTO_DIA_PX), PilImage.LANCZOS)
            buffer = io.BytesIO()
            imagem.save(buffer, format="JPEG", quality=QUALIDADE_JPEG)
    except Exception:
        return None
    buffer.seek(0)
    _cache_fotos[chave_cache] = buffer
    return buffer


def _regua_dourada(largura: float = 4 * cm) -> Table:
    regua = Table([[""]], colWidths=[largura], rowHeights=[0.09 * cm])
    regua.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), COR_OURO)]))
    regua.hAlign = "CENTER"
    return regua


def _pagina_capa(estilos: dict) -> list:
    return [
        Spacer(1, 4.2 * cm),
        Paragraph("LITURGIA DE OUTUBRO", estilos["capa_titulo"]),
        Paragraph("os santos e os dias do mês do Rosário", estilos["capa_subtitulo"]),
        Spacer(1, 0.5 * cm),
        _regua_dourada(),
        Spacer(1, 0.9 * cm),
        Paragraph(
            "Tempo litúrgico e leitura de cada um dos 31 dias, com a história dos santos "
            "celebrados em outubro — de Santa Teresinha a Nossa Senhora Aparecida.",
            estilos["capa_rodape"],
        ),
        Spacer(1, 3.5 * cm),
        _regua_dourada(2.2 * cm),
        Spacer(1, 0.4 * cm),
        Paragraph("Nove de Julho · outubro de 2026", estilos["capa_rodape"]),
        PageBreak(),
    ]


def _selo_legenda(rank: str, estilos: dict) -> Table:
    cor = COR_RANK[rank]
    celula = Table([[Paragraph(ROTULO_RANK[rank], estilos["selo_rank"])]], colWidths=[4.6 * cm])
    celula.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), cor),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return celula


def _pagina_como_usar(estilos: dict) -> list:
    elementos = [
        Paragraph("Como usar este e-book", estilos["secao_titulo"]),
        Paragraph(
            "Cada dia traz o tempo litúrgico e a referência das leituras do dia (o livro, "
            "capítulo e versículo — não o texto completo, pra você abrir na sua Bíblia ou "
            "app de preferência). Nos dias de santo, tem uma bio curta e, quando o santo "
            "tem medalha no nosso catálogo, um link direto pra conhecer.",
            estilos["legenda_corpo"],
        ),
        Paragraph("O que cada selo colorido significa:", estilos["legenda_corpo"]),
    ]
    linhas_legenda = []
    descricoes = {
        "solenidade": "a celebração mais importante do calendário (ex: Nossa Senhora Aparecida)",
        "festa": "celebração de grande relevância (ex: um apóstolo)",
        "obrigatoria": "todo padre celebra esse santo/mistério nesse dia",
        "facultativa": "o padre pode escolher celebrar esse santo ou o dia comum",
        "comum": "tempo comum, sem festa ou memória específica",
    }
    for rank in ["solenidade", "festa", "obrigatoria", "facultativa", "comum"]:
        linhas_legenda.append([_selo_legenda(rank, estilos), Paragraph(descricoes[rank], estilos["legenda_corpo"])])
    tabela_legenda = Table(linhas_legenda, colWidths=[5 * cm, 10.5 * cm])
    tabela_legenda.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabela_legenda)
    elementos.append(Spacer(1, 0.8 * cm))
    elementos.append(Paragraph("Outubro de relance", estilos["secao_titulo"]))
    elementos.append(_grade_mes(estilos))
    elementos.append(PageBreak())
    return elementos


def _grade_mes(estilos: dict) -> Table:
    """Mini-calendario com o numero de cada dia colorido pelo grau
    liturgico -- pra quem folheia o e-book achar rapido um dia especial
    (ex: "quero ver o dia 12") sem precisar ler pagina por pagina."""
    por_dia = {d["dia"]: d for d in DIAS_OUTUBRO_2026}
    primeiro_dia_semana = datetime.date(2026, 10, 1).weekday()  # 0=segunda
    celulas: list = [""] * primeiro_dia_semana
    for dia in range(1, 32):
        info = por_dia[dia]
        cor = COR_RANK[info["rank"]]
        texto_cor = colors.white if info["rank"] != "comum" else colors.white
        num = Table([[Paragraph(str(dia), estilos["indice_numero"])]], colWidths=[1.9 * cm], rowHeights=[1.1 * cm])
        num.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), cor),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        celulas.append(num)
    while len(celulas) % 7:
        celulas.append("")
    linhas = [celulas[i:i + 7] for i in range(0, len(celulas), 7)]
    cabecalho = [Paragraph(d[:3], estilos["dia_leitura_compacta"]) for d in DIAS_PT]
    grade = Table([cabecalho] + linhas, colWidths=[1.9 * cm] * 7)
    grade.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return grade


def _linha_dia_compacto(info: dict, estilos: dict) -> KeepTogether:
    data = datetime.date(2026, 10, info["dia"])
    numero = Paragraph(str(info["dia"]), estilos["dia_numero"])
    numero_cel = Table([[numero]], colWidths=[1.4 * cm])
    numero_cel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COR_FUNDO_SUAVE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    weekday = DIAS_PT[data.weekday()]
    texto = Paragraph(f"{weekday} — {info['titulo']}", estilos["dia_titulo_compacto"])
    leitura = Paragraph(info["leituras"], estilos["dia_leitura_compacta"])
    bloco_texto = Table([[texto], [leitura]], colWidths=[13.4 * cm])
    bloco_texto.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    linha = Table([[numero_cel, bloco_texto]], colWidths=[1.4 * cm, 13.4 * cm])
    linha.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return KeepTogether(linha)


def _botao(texto: str, url: str, estilos: dict, cor=COR_MARCA) -> Table:
    paragrafo = Paragraph(f'<link href="{url}">{texto}</link>', estilos["botao_texto"])
    botao = Table([[paragrafo]], colWidths=[9 * cm])
    botao.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), cor),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return botao


def _cartao_dia_destaque(info: dict, base_url: str, produtos_por_id: dict, estilos: dict) -> KeepTogether:
    data = datetime.date(2026, 10, info["dia"])
    weekday = DIAS_PT[data.weekday()]
    selo = _selo_legenda(info["rank"], estilos)

    produto = produtos_por_id.get(info["produto_id"]) if info["produto_id"] else None
    foto = None
    if produto is not None:
        caminho_imagem = produto["modelos"][0].get("imagem")
        if caminho_imagem:
            buffer = _foto_reduzida(caminho_imagem)
            if buffer is not None:
                foto = RLImage(buffer, width=LADO_FOTO_DIA, height=LADO_FOTO_DIA)

    bloco_texto = [
        Paragraph(f"{info['dia']} de outubro · {weekday}", estilos["dia_data_grande"]),
        Paragraph(info["titulo"], estilos["dia_titulo_grande"]),
        Paragraph(info["bio"], estilos["dia_bio"]),
        Paragraph(info["leituras"], estilos["dia_leitura_grande"]),
    ]
    if foto is not None:
        linha_conteudo = Table(
            [[foto, bloco_texto]],
            colWidths=[LADO_FOTO_DIA + 0.4 * cm, 11.4 * cm],
        )
        linha_conteudo.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
    else:
        linha_conteudo = Table([[bloco_texto]], colWidths=[14.8 * cm])

    partes = [selo, Spacer(1, 0.25 * cm), linha_conteudo, Spacer(1, 0.3 * cm)]
    if produto is not None:
        url_produto = f"{base_url}/produto/{produto['id']}"
        partes.append(_botao(f"Ver medalha de {produto['nome']} ->", url_produto, estilos))
    novena_slug = info.get("novena_slug")
    if novena_slug:
        partes.append(Spacer(1, 0.2 * cm))
        url_novena = f"{base_url}/blog/{novena_slug}"
        partes.append(_botao("Ver novena completa ->", url_novena, estilos, cor=COR_OURO))
    produto_extra_id = info.get("produto_extra_id")
    if produto_extra_id and produtos_por_id.get(produto_extra_id):
        partes.append(Spacer(1, 0.2 * cm))
        url_extra = f"{base_url}/produto/{produto_extra_id}"
        partes.append(_botao(info.get("produto_extra_rotulo", "Ver medalha ->"), url_extra, estilos))
    produto_extra_novena_slug = info.get("produto_extra_novena_slug")
    if produto_extra_novena_slug:
        partes.append(Spacer(1, 0.2 * cm))
        url_extra_novena = f"{base_url}/blog/{produto_extra_novena_slug}"
        partes.append(_botao("Ver novena de São Carlo Acutis ->", url_extra_novena, estilos, cor=COR_OURO))
    partes.append(Spacer(1, 0.5 * cm))
    return KeepTogether(partes)


def _pagina_final_cta(estilos: dict, base_url: str) -> list:
    """Ultima pagina, leve e discreta de proposito (pedido do usuario:
    "de uma forma leve e sutil") -- um convite curto pro catalogo, nao
    uma pagina de vendas. Kit Livraria Shalom cobre o publico de
    atacado/revenda (e´ a pagina que ja existe pra isso, ver
    /kit-livraria-shalom); o catalogo cobre varejo -- o desconto por
    quantidade entra sozinho no mesmo carrinho, nao tem pagina separada
    de "atacado" no site."""
    botao_catalogo = _botao("Ver catálogo completo ->", f"{base_url}/catalogo", estilos)
    botao_catalogo.hAlign = "CENTER"
    botao_kit = _botao("Kit Livraria Shalom, pra revenda ->", f"{base_url}/kit-livraria-shalom", estilos, cor=COR_OURO)
    botao_kit.hAlign = "CENTER"
    return [
        Spacer(1, 8 * cm),
        Paragraph("Antes de você ir", estilos["cta_final_titulo"]),
        Paragraph(
            "Se esse e-book ajudou a rezar outubro com mais atenção, talvez você "
            "goste de conhecer as medalhas dos santos do mês — pra presentear, "
            "colecionar ou revender (o desconto por quantidade entra sozinho, sem cupom).",
            estilos["cta_final_corpo"],
        ),
        botao_catalogo,
        Spacer(1, 0.3 * cm),
        botao_kit,
    ]


def gerar_pdf_liturgia_outubro(base_url: str) -> bytes:
    global _cache_pdf
    if _cache_pdf is not None:
        return _cache_pdf

    estilos = _estilos()
    produtos_por_id = {p["id"]: p for p in carregar_produtos()}

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        title="Liturgia de Outubro — Nove de Julho",
    )

    story: list = []
    story += _pagina_capa(estilos)
    story += _pagina_como_usar(estilos)

    for info in DIAS_OUTUBRO_2026:
        if info.get("bio"):
            story.append(_cartao_dia_destaque(info, base_url, produtos_por_id, estilos))
        else:
            story.append(_linha_dia_compacto(info, estilos))

    story.append(PageBreak())
    story += _pagina_final_cta(estilos, base_url)

    doc.build(story)
    _cache_pdf = buffer.getvalue()
    return _cache_pdf
