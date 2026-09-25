"""
Colares -- peca EXCLUSIVA DO VAREJO (pedido em 2026-09-25: "quero adicionar
eles nessa minha loja... sem tabela de atacado"), preco fixo R$97,00, sem
tamanho/cor pra escolher (ao contrario do catalogo normal em
data/produtos.json). Isolada no proprio GRUPO "colares" do motor de preco
(ver services/pricing.py:GRUPO_DE_CHAVE) pelo mesmo motivo do "cruz_terco":
um preco fixo que nao deve nem sofrer nem causar desconto de outro grupo.

So entra aqui quando tem FOTO DE VERDADE da peca -- "publicado: False" fica
fora da home/pagina /colares ate a foto chegar (ver conversa: Nossa Senhora
e Sao Jose ainda nao tem nenhuma foto no Drive, so a descricao pretendida).
"""

from __future__ import annotations

COLARES = [
    {
        "id": "sagrado-coracao-de-jesus",
        "nome": "Colar Sagrado Coração de Jesus",
        "chave_preco": "colar_sagrado_coracao_de_jesus",
        "publicado": True,
        "imagem_frente": "img/produtos/colar_sagrado_coracao_de_jesus_frente.jpg",
        "imagem_detalhe": "img/produtos/colar_sagrado_coracao_de_jesus_detalhe.jpg",
        "imagem_uso": "img/produtos/colar_sagrado_coracao_de_jesus_uso.jpg",
        "descricao_curta": "Pingente de coração vermelho com coroa de espinhos e cruz, banhado a ouro.",
        "descricao": [
            "O Sagrado Coração de Jesus é o amor de Cristo entregue por inteiro — "
            "o coração vermelho representa esse amor, a coroa de espinhos o "
            "sacrifício, e a pequena cruz no topo lembra que tudo isso aconteceu "
            "por nós.",
            "Peça delicada e discreta, banhada a ouro, pensada pra usar no dia a "
            "dia sem perder o significado — ou presentear alguém com uma lembrança "
            "de fé que fica perto do coração.",
        ],
        "medidas": "Pingente ≈ 16mm x 12mm · Corrente ≈ 40cm + 5cm de extensor",
    },
    {
        "id": "nossa-senhora",
        "nome": "Colar Nossa Senhora (rosa)",
        "chave_preco": None,
        "publicado": False,
        "imagem_frente": None,
        "imagem_detalhe": None,
        "imagem_uso": None,
        "descricao_curta": "Pingente de Nossa Senhora em cristal rosa, banhado a ouro.",
        "descricao": [],
        "medidas": "",
    },
    {
        "id": "sao-jose",
        "nome": "Colar São José",
        "chave_preco": None,
        "publicado": False,
        "imagem_frente": None,
        "imagem_detalhe": None,
        "imagem_uso": None,
        "descricao_curta": "Pingente de São José, banhado a ouro.",
        "descricao": [],
        "medidas": "",
    },
]

PRECO_COLAR_REAIS = 97.00


def colares_publicados() -> list[dict]:
    return [c for c in COLARES if c["publicado"]]


def colar_por_id(colar_id: str) -> dict | None:
    for c in COLARES:
        if c["id"] == colar_id and c["publicado"]:
            return c
    return None
