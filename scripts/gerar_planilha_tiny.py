"""
Gera a planilha de importacao em massa de produtos da Tiny (mesmo
formato do modelo baixado direto na Tiny -- colunas "Codigo do pai" e
"Variacoes" seguem o padrao deles) a partir do catalogo real do site
(data/produtos.json).

Por que planilha e nao API: a integracao atual com a Tiny (services/tiny.py)
usa a API v2 (token), so pra pedidos. Criar produto pai + variacoes por
API nunca foi testado contra a Tiny de verdade (o proprio services/tiny.py
ja registra que o ambiente de dev nao alcanca tiny.com.br) -- um erro af
la bagunçaria o catalogo inteiro. A planilha usa o formato que a propria
Tiny garante que funciona (confirmado: 1a leva importou com sucesso
depois do ajuste de preco na linha pai, ver historico do commit).

Estrutura gerada por MODELO (produto + modelo, ja que ~50 produtos tem
mais de um modelo -- ver data/produtos.json):
  - "Medalha <Nome> <Modelo>"    (pai, tipo V) -> filhos 12mm / 16mm (tipo S)
  - "Entremeio <Nome> <Modelo>"  (pai, tipo V) -> filhos Ouro Velho / Prata (tipo S)
  - "Chaveiro <Nome> <Modelo>"   (simples, tipo S, sem variacao)

Categoria de cada linha-filha segue exatamente o pedido do usuario
("Medalha 1 lado 12mm", "Medalha 1 lado 16mm", "Entremeio 1 lado Ouro
Velho", "Entremeio 1 lado Prata", "Chaveiro 1 lado") -- de proposito
diferente da amostra da Tiny (que repete a mesma categoria pai/filhos),
pra bater com o relatorio que o usuario quer separar por formato+tamanho
independente do santo.

Imagem: usa as colunas "URL imagem 1..6" (NAO "URL imagem externa"), pra
a Tiny baixar e ANEXAR a imagem ao produto -- confirmado pelo usuario que
a 1a leva (com "URL imagem externa") caiu na aba "imagens externas" (so
link, nao anexada de verdade).

Descricao/SEO/Tags: textos padrao por FORMATO (medalha/entremeio/
chaveiro), reaproveitando so fatos ja publicados no proprio site (material,
cuidados -- ver services/paginas_institucionais.py "perguntas-frequentes")
pra nao inventar caracteristica de produto fisico.

LIMITACOES ASSUMIDAS (avisar sempre que rodar):
  - Preco: so o preco de VAREJO (faixa "1" de data/precos.json) vai pra
    Tiny/Shopee. As faixas de desconto por quantidade sao logica propria
    do site (services/pricing.py) e nao tem equivalente nesse import.
  - NCM (7113.20.00) e dimensoes (11x3x16cm, "Pacote / Caixa") sao os
    que o usuario informou que ja usa no cadastro da Tiny -- repetidos
    em toda linha.
  - Peso: services/frete.py::PESO_KG_POR_CHAVE (confirmado contra o
    cadastro real na Yampi). Peso liquido = peso bruto (nao ha peso de
    embalagem individual separado).
  - "Embalagem" (perfil nomeado tipo "Caixa Mini Envios", visto no
    cadastro do usuario) NAO tem coluna nesse modelo de importacao (so
    existe "Formato embalagem" + dimensoes) -- nao da pra preencher via
    planilha, precisa configurar direto na Tiny (padrao de embalagem ou
    edicao em massa).
  - "Tags" (campo separado na tela de produto da Tiny, visto no print do
    usuario) tambem NAO tem coluna nesse modelo de importacao -- so
    "Descrição", "Descrição complementar", "Título SEO", "Descrição SEO"
    e "Palavras chave SEO" existem. A categoria tematica do santo
    (Nossa Senhora, Santos, Devoções...) foi colocada dentro de
    "Palavras chave SEO" em vez de inventar uma coluna que nao existe.
  - Estoque, preco de custo, fornecedor, GTIN/marca: NAO preenchidos
    (dado que nao temos confirmado) -- ficam em branco pra completar
    direto na Tiny, de proposito, pra nao inventar numero.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOMINIO = "https://atacado.lojanovedejulho.com.br"

NCM = "7113.20.00"
ORIGEM = 0
UNIDADE = "Un"
FORMATO_EMBALAGEM = "Pacote / Caixa"
LARGURA_CM = 11
ALTURA_CM = 3
COMPRIMENTO_CM = 16

PESO_KG_POR_CHAVE = {
    "12mm": 0.001,
    "16mm": 0.002,
    "entremeio": 0.002,
    "chaveiro": 0.015,
}

PRECO_VAREJO_POR_CHAVE = {
    "12mm": 5.00,
    "16mm": 5.00,
    "entremeio": 5.00,
    "chaveiro": 15.00,
}

# Fatos de material/cuidado ja publicados em
# services/paginas_institucionais.py ("perguntas-frequentes") -- reaproveitados
# aqui pra nao inventar caracteristica de produto fisico numa descricao de venda.
_CUIDADOS = (
    "Pode molhar sem problema no dia a dia (banho, chuva, suor) -- só evite "
    "exposição exagerada e constante a sol/água quente, evite passar produto "
    "químico ou perfume direto em cima da peça, e guarde longe de umidade "
    "excessiva quando não estiver usando, pra manter o brilho por mais tempo."
)

_DESCRICOES_POR_FORMATO = {
    "medalha": lambda nome: (
        f"Medalha de {nome} (1 lado), produzida artesanalmente pela Nove de "
        f"Julho em aço inoxidável de qualidade, resinada à mão. Disponível "
        f"nos tamanhos 12mm e 16mm. Ótima opção pra uso no dia a dia ou de "
        f"presente em batizados, casamentos, crismas, retiros e outras "
        f"celebrações -- uma forma de evangelizar pela beleza e pela tradição "
        f"da Igreja. Cuidados com a peça: {_CUIDADOS}"
    ),
    "entremeio": lambda nome: (
        f"Entremeio de {nome} para terço, em liga de zinco resinada, nas "
        f"colorações ouro velho ou prata antigo. Ideal pra quem monta ou "
        f"personaliza terços e rosários artesanais -- também funciona como "
        f"lembrancinha de devoção. Cuidados com a peça: {_CUIDADOS}"
    ),
    "chaveiro": lambda nome: (
        f"Chaveiro de {nome} (1 lado), em liga de zinco resinada. Uma forma "
        f"de levar a devoção pra onde for -- na bolsa, mochila ou no molho de "
        f"chaves -- e também uma boa lembrancinha de batizado, crisma, "
        f"casamento ou evento paroquial. Cuidados com a peça: {_CUIDADOS}"
    ),
}

_SEO_POR_FORMATO = {
    "medalha": lambda nome: (
        f"Medalha de {nome} 12mm/16mm, aço inox resinado. Presente de "
        f"batizado, casamento ou devoção -- compre no atacado, com nota fiscal."
    ),
    "entremeio": lambda nome: (
        f"Entremeio de {nome} pra terço, ouro velho ou prata antigo. "
        f"Ideal pra montar rosários artesanais -- compre no atacado, com nota fiscal."
    ),
    "chaveiro": lambda nome: (
        f"Chaveiro de {nome}, liga de zinco resinada. Lembrancinha de "
        f"devoção pra batizado, crisma ou casamento -- compre no atacado."
    ),
}

_KEYWORDS_POR_FORMATO = {
    "medalha": lambda nome: (
        f"medalha {nome.lower()}, medalha católica, medalha de santo atacado, "
        f"medalha 12mm, medalha 16mm, presente batizado, medalha resinada aço inox"
    ),
    "entremeio": lambda nome: (
        f"entremeio {nome.lower()}, entremeio para terço, entremeio ouro velho, "
        f"entremeio prata antigo, miçanga para rosário, terço artesanal"
    ),
    "chaveiro": lambda nome: (
        f"chaveiro {nome.lower()}, chaveiro católico, chaveiro de santo, "
        f"lembrancinha católica, chaveiro devoção"
    ),
}

COLUNAS = [
    "ID", "Código (SKU)", "Descrição", "Unidade", "NCM (Classificação fiscal)",
    "Origem", "Preço", "Valor IPI fixo", "Observações", "Situação", "Estoque",
    "Preço de custo", "Cód do fornecedor", "Fornecedor", "Localização",
    "Estoque máximo", "Estoque mínimo", "Peso líquido (Kg)", "Peso bruto (Kg)",
    "GTIN/EAN", "GTIN/EAN tributável", "Descrição complementar", "CEST",
    "Código de Enquadramento IPI", "Formato embalagem", "Largura embalagem",
    "Altura Embalagem", "Comprimento embalagem", "Diâmetro embalagem",
    "Tipo do produto", "URL imagem 1", "URL imagem 2", "URL imagem 3",
    "URL imagem 4", "URL imagem 5", "URL imagem 6", "Categoria",
    "Código do pai", "Variações", "Marca", "Garantia", "Sob encomenda",
    "Preço promocional", "URL imagem externa 1", "URL imagem externa 2",
    "URL imagem externa 3", "URL imagem externa 4", "URL imagem externa 5",
    "URL imagem externa 6", "Link do vídeo", "Título SEO", "Descrição SEO",
    "Palavras chave SEO", "Slug", "Dias para preparação", "Controlar lotes",
    "Unidade por caixa", "URL imagem externa 7", "URL imagem externa 8",
    "URL imagem externa 9", "URL imagem externa 10", "Markup",
    "Permitir inclusão nas vendas", "EX TIPI",
]


def _linha_base(*, sku: str, descricao_titulo: str, nome_santo: str, formato: str,
                 categoria_produto: str, categoria: str, tipo: str,
                 preco: float | None, peso_kg: float, imagem: str | None,
                 codigo_pai: str | None = None, variacoes: str | None = None) -> dict:
    linha = {c: "" for c in COLUNAS}
    linha.update({
        "Código (SKU)": sku,
        "Descrição": descricao_titulo,
        "Unidade": UNIDADE,
        "NCM (Classificação fiscal)": NCM,
        "Origem": ORIGEM,
        "Preço": preco if preco is not None else "",
        "Situação": "Ativo",
        "Peso líquido (Kg)": round(peso_kg, 3),
        "Peso bruto (Kg)": round(peso_kg, 3),
        "Formato embalagem": FORMATO_EMBALAGEM,
        "Largura embalagem": LARGURA_CM,
        "Altura Embalagem": ALTURA_CM,
        "Comprimento embalagem": COMPRIMENTO_CM,
        "Tipo do produto": tipo,
        "Categoria": categoria,
        "Código do pai": codigo_pai or "",
        "Variações": variacoes or "",
        "Sob encomenda": "Não",
        "Controlar lotes": "Não",
        "Descrição complementar": _DESCRICOES_POR_FORMATO[formato](nome_santo),
        "Título SEO": descricao_titulo,
        "Descrição SEO": _SEO_POR_FORMATO[formato](nome_santo),
        "Palavras chave SEO": f"{_KEYWORDS_POR_FORMATO[formato](nome_santo)}, {categoria_produto.lower()}",
        "Marca": "Nove de Julho",
    })
    if imagem:
        linha["URL imagem 1"] = f"{DOMINIO}/static/{imagem}"
    return linha


def gerar_linhas(produtos: list[dict]) -> list[dict]:
    linhas: list[dict] = []
    for produto in produtos:
        produto_id = produto["id"]
        nome_santo = produto["nome"]
        categoria_produto = produto["categoria"]
        for modelo in produto["modelos"]:
            modelo_id = modelo["id"]
            modelo_nome = modelo["nome"]
            base_id = f"{produto_id.upper()}-M{modelo_id}"
            descricao_base = f"{nome_santo} — {modelo_nome}"

            # Medalha (pai com variacao de tamanho) -- a Tiny rejeita
            # linha de produto pai (tipo V) sem Preco preenchido (visto
            # na pratica: das 436 linhas que deram erro na 1a importacao,
            # TODAS eram linhas pai sem preco -- nenhuma variacao/filho
            # deu erro). Repete o preco de entrada da propria familia.
            sku_pai_medalha = f"MED-{base_id}"
            linhas.append(_linha_base(
                sku=sku_pai_medalha, descricao_titulo=f"Medalha {descricao_base}",
                nome_santo=nome_santo, formato="medalha", categoria_produto=categoria_produto,
                categoria="Medalhas", tipo="V", preco=PRECO_VAREJO_POR_CHAVE["12mm"],
                peso_kg=0.0, imagem=modelo.get("imagem"),
            ))
            for tamanho in modelo["tamanhos"]:
                chave = tamanho
                linhas.append(_linha_base(
                    sku=f"{sku_pai_medalha}-{tamanho}",
                    descricao_titulo=f"Medalha {descricao_base} - {tamanho}",
                    nome_santo=nome_santo, formato="medalha", categoria_produto=categoria_produto,
                    categoria=f"Medalha 1 lado {tamanho}", tipo="S",
                    preco=PRECO_VAREJO_POR_CHAVE[chave],
                    peso_kg=PESO_KG_POR_CHAVE[chave],
                    imagem=modelo.get("imagem"),
                    codigo_pai=sku_pai_medalha, variacoes=f"Tamanho:{tamanho}",
                ))

            # Entremeio (pai com variacao de cor)
            sku_pai_entremeio = f"ENT-{base_id}"
            linhas.append(_linha_base(
                sku=sku_pai_entremeio, descricao_titulo=f"Entremeio {descricao_base}",
                nome_santo=nome_santo, formato="entremeio", categoria_produto=categoria_produto,
                categoria="Entremeios", tipo="V", preco=PRECO_VAREJO_POR_CHAVE["entremeio"],
                peso_kg=0.0, imagem=modelo.get("imagem_entremeio_prata"),
            ))
            for cor, campo_imagem in (
                ("Ouro Velho", "imagem_entremeio_ouro_velho"),
                ("Prata", "imagem_entremeio_prata"),
            ):
                linhas.append(_linha_base(
                    sku=f"{sku_pai_entremeio}-{cor[:2].upper()}",
                    descricao_titulo=f"Entremeio {descricao_base} - {cor}",
                    nome_santo=nome_santo, formato="entremeio", categoria_produto=categoria_produto,
                    categoria=f"Entremeio 1 lado {cor}", tipo="S",
                    preco=PRECO_VAREJO_POR_CHAVE["entremeio"],
                    peso_kg=PESO_KG_POR_CHAVE["entremeio"],
                    imagem=modelo.get(campo_imagem),
                    codigo_pai=sku_pai_entremeio, variacoes=f"Cor:{cor}",
                ))

            # Chaveiro (simples, sem variacao)
            linhas.append(_linha_base(
                sku=f"CHAV-{base_id}", descricao_titulo=f"Chaveiro {descricao_base}",
                nome_santo=nome_santo, formato="chaveiro", categoria_produto=categoria_produto,
                categoria="Chaveiro 1 lado", tipo="S",
                preco=PRECO_VAREJO_POR_CHAVE["chaveiro"],
                peso_kg=PESO_KG_POR_CHAVE["chaveiro"],
                imagem=modelo.get("imagem_chaveiro"),
            ))
    return linhas


def main() -> None:
    produtos = json.loads((DATA_DIR / "produtos.json").read_text(encoding="utf-8"))
    linhas = gerar_linhas(produtos)
    df = pd.DataFrame(linhas, columns=COLUNAS)

    saida = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DIR / "planilha_tiny_catalogo.xlsx"
    df.to_excel(saida, index=False, sheet_name="Planilha 1")
    print(f"{len(df)} linhas geradas em {saida}")


if __name__ == "__main__":
    main()
