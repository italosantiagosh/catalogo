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
Tiny garante que funciona.

Estrutura gerada por MODELO (produto + modelo, ja que ~50 produtos tem
mais de um modelo -- ver data/produtos.json):
  - "Medalha <Nome> <Modelo>"    (pai, tipo V) -> filhos 12mm / 16mm (tipo S)
  - "Entremeio <Nome> <Modelo>"  (pai, tipo V) -> filhos Ouro Velho / Prata (tipo S)
  - "Chaveiro <Nome> <Modelo>"   (simples, tipo S, sem variacao)

Categoria de cada linha-filha segue exatamente o pedido do usuario
("Medalha 1 lado 12mm", "Medalha 1 lado 16mm", "Entremeio 1 lado Ouro
Velho", "Entremeio 1 lado Prata", "Chaveiro 1 lado") -- de propocito
diferente da amostra da Tiny (que repete a mesma categoria pai/filhos),
pra bater com o relatorio que o usuario quer separar por formato+tamanho
independente do santo.

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


def _linha_base(*, sku: str, descricao: str, categoria: str, tipo: str,
                 preco: float | None, peso_kg: float, imagem: str | None,
                 codigo_pai: str | None = None, variacoes: str | None = None) -> dict:
    linha = {c: "" for c in COLUNAS}
    linha.update({
        "Código (SKU)": sku,
        "Descrição": descricao,
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
    })
    if imagem:
        linha["URL imagem externa 1"] = f"{DOMINIO}/static/{imagem}"
    return linha


def gerar_linhas(produtos: list[dict]) -> list[dict]:
    linhas: list[dict] = []
    for produto in produtos:
        produto_id = produto["id"]
        nome_santo = produto["nome"]
        for modelo in produto["modelos"]:
            modelo_id = modelo["id"]
            modelo_nome = modelo["nome"]
            base_id = f"{produto_id.upper()}-M{modelo_id}"
            descricao_base = f"{nome_santo} — {modelo_nome}"

            # Medalha (pai com variacao de tamanho) -- a Tiny rejeita
            # linha de produto pai (tipo V) sem Preco preenchido (visto
            # na pratica: das 436 linhas que deram erro na importacao,
            # TODAS eram linhas pai sem preco -- nenhuma variacao/filho
            # deu erro). Repete o preco de entrada da propria familia.
            sku_pai_medalha = f"MED-{base_id}"
            linhas.append(_linha_base(
                sku=sku_pai_medalha, descricao=f"Medalha {descricao_base}",
                categoria="Medalhas", tipo="V", preco=PRECO_VAREJO_POR_CHAVE["12mm"],
                peso_kg=0.0, imagem=modelo.get("imagem"),
            ))
            for tamanho in modelo["tamanhos"]:
                chave = tamanho
                linhas.append(_linha_base(
                    sku=f"{sku_pai_medalha}-{tamanho}",
                    descricao=f"Medalha {descricao_base} - {tamanho}",
                    categoria=f"Medalha 1 lado {tamanho}", tipo="S",
                    preco=PRECO_VAREJO_POR_CHAVE[chave],
                    peso_kg=PESO_KG_POR_CHAVE[chave],
                    imagem=modelo.get("imagem"),
                    codigo_pai=sku_pai_medalha, variacoes=f"Tamanho:{tamanho}",
                ))

            # Entremeio (pai com variacao de cor)
            sku_pai_entremeio = f"ENT-{base_id}"
            linhas.append(_linha_base(
                sku=sku_pai_entremeio, descricao=f"Entremeio {descricao_base}",
                categoria="Entremeios", tipo="V", preco=PRECO_VAREJO_POR_CHAVE["entremeio"],
                peso_kg=0.0, imagem=modelo.get("imagem_entremeio_prata"),
            ))
            for cor, campo_imagem in (
                ("Ouro Velho", "imagem_entremeio_ouro_velho"),
                ("Prata", "imagem_entremeio_prata"),
            ):
                linhas.append(_linha_base(
                    sku=f"{sku_pai_entremeio}-{cor[:2].upper()}",
                    descricao=f"Entremeio {descricao_base} - {cor}",
                    categoria=f"Entremeio 1 lado {cor}", tipo="S",
                    preco=PRECO_VAREJO_POR_CHAVE["entremeio"],
                    peso_kg=PESO_KG_POR_CHAVE["entremeio"],
                    imagem=modelo.get(campo_imagem),
                    codigo_pai=sku_pai_entremeio, variacoes=f"Cor:{cor}",
                ))

            # Chaveiro (simples, sem variacao)
            linhas.append(_linha_base(
                sku=f"CHAV-{base_id}", descricao=f"Chaveiro {descricao_base}",
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
