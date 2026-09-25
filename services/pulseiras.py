"""
Pulseiras -- peca EXCLUSIVA DO VAREJO (pedido em 2026-09-25, mesma conversa
e mesmo padrao de services/colares.py), preco fixo R$197,00, sem tamanho/
cor pra escolher. Isolada no proprio GRUPO "pulseiras" do motor de preco
(ver services/pricing.py:GRUPO_DE_CHAVE) -- grupo PROPRIO, separado de
"colares": pulseira e colar sao pecas diferentes, cada uma com sua faixa
isolada.

Fotos baixadas da propria pagina do fornecedor que a usuaria revende
(lojaparresia.com.br/pulseira-de-consagracao-a-nossa-senhora-com-medalha-
milagrosa-banhada-a-ouro/p, mandada na conversa) -- mesma origem/mesmo
criterio ja usado pro Colar Sagrado Coracao de Jesus (fotos de verdade da
peca fisica revendida, nao fotos genericas). "imagens" e´ uma lista (1 a 3
fotos, ver services/colares.py -- mesmo padrao, pra o carrossel se adaptar
ao numero de fotos disponiveis de cada peca).
"""

from __future__ import annotations

PULSEIRAS = [
    {
        "id": "consagracao-nossa-senhora",
        "nome": "Pulseira de Consagração a Nossa Senhora",
        "chave_preco": "pulseira_consagracao_nossa_senhora",
        "publicado": True,
        "imagens": [
            {"src": "img/produtos/pulseira_consagracao_nossa_senhora_frente.jpg", "rotulo": None},
            {"src": "img/produtos/pulseira_consagracao_nossa_senhora_detalhe.jpg", "rotulo": "detalhe"},
            {"src": "img/produtos/pulseira_consagracao_nossa_senhora_uso.jpg", "rotulo": "sendo usada"},
        ],
        "descricao_curta": "Pulseira com medalha milagrosa e berloque de coração, banhada a ouro.",
        "descricao": [
            "Inspirada no método de consagração a Nossa Senhora de São Luís Maria "
            "Grignion de Montfort — um caminho de entrega total a Jesus pelas mãos "
            "de Maria. Mais do que um acessório, é um sinal visível dessa "
            "consagração, pra lembrar da devoção todos os dias.",
            "A medalha é inspirada na Medalha Milagrosa, revelada por Nossa "
            "Senhora a Santa Catarina Labouré, como sinal de graças pra quem a "
            "usa com fé. Vem com um pequeno berloque de coração ao lado.",
        ],
        "medidas": "Corrente banhada a ouro, fecho lagosta, tamanho ajustável",
    },
]

PRECO_PULSEIRA_REAIS = 197.00


def pulseiras_publicadas() -> list[dict]:
    return [p for p in PULSEIRAS if p["publicado"]]


def pulseira_por_id(pulseira_id: str) -> dict | None:
    for p in PULSEIRAS:
        if p["id"] == pulseira_id and p["publicado"]:
            return p
    return None
