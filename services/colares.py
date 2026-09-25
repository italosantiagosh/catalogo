"""
Colares -- peca EXCLUSIVA DO VAREJO (pedido em 2026-09-25: "quero adicionar
eles nessa minha loja... sem tabela de atacado"), preco fixo R$97,00, sem
tamanho/cor pra escolher (ao contrario do catalogo normal em
data/produtos.json). Isolada no proprio GRUPO "colares" do motor de preco
(ver services/pricing.py:GRUPO_DE_CHAVE) pelo mesmo motivo do "cruz_terco":
um preco fixo que nao deve nem sofrer nem causar desconto de outro grupo.

So entra aqui quando tem FOTO DE VERDADE da peca -- "publicado: False" fica
fora da home/pagina de produto ate a foto chegar. "imagens" e´ uma lista (1
a 3 fotos) -- Sagrado Coracao de Jesus tem 3 (frente/detalhe/uso), Castissimo
Coracao de Sao Jose e Imaculado Coracao de Maria (fotos mandadas em
2026-09-25, depois do pedido inicial) tem so 1 cada por enquanto -- o
carrossel (templates/linha_premium_item.html, pagina individual por peca
desde 2026-09-25 2a parte) se adapta ao numero de fotos disponiveis, sem
inventar foto repetida so pra "completar" 3."""

from __future__ import annotations

COLARES = [
    {
        "id": "sagrado-coracao-de-jesus",
        "nome": "Colar Sagrado Coração de Jesus",
        "chave_preco": "colar_sagrado_coracao_de_jesus",
        "publicado": True,
        "imagens": [
            {"src": "img/produtos/colar_sagrado_coracao_de_jesus_frente.jpg", "rotulo": None},
            {"src": "img/produtos/colar_sagrado_coracao_de_jesus_detalhe.jpg", "rotulo": "detalhe do pingente"},
            {"src": "img/produtos/colar_sagrado_coracao_de_jesus_uso.jpg", "rotulo": "sendo usado"},
        ],
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
        "id": "imaculado-coracao-de-maria",
        "nome": "Colar Imaculado Coração de Maria",
        "chave_preco": "colar_imaculado_coracao_maria",
        "publicado": True,
        "imagens": [
            {"src": "img/produtos/colar_imaculado_coracao_maria_frente.jpg", "rotulo": None},
        ],
        "descricao_curta": "Pingente de coração rosa trespassado por espada, banhado a ouro.",
        "descricao": [
            "O Imaculado Coração de Maria é sinal do amor puro e da entrega total "
            "de Nossa Senhora a Deus — o coração rosa trespassado pela espada "
            "lembra a profecia de Simeão (\"uma espada trespassará também a tua "
            "alma\"), e a dor que Maria viveu junto de Jesus.",
            "Peça delicada e discreta, banhada a ouro, pensada pra quem vive a "
            "consagração a Nossa Senhora no dia a dia — ou pra presentear alguém "
            "com essa devoção.",
        ],
        "medidas": "Pingente ≈ 16mm x 12mm · Corrente ≈ 40cm + 5cm de extensor",
    },
    {
        "id": "castissimo-coracao-de-sao-jose",
        "nome": "Colar Castíssimo Coração de São José",
        "chave_preco": "colar_castissimo_coracao_sao_jose",
        "publicado": True,
        "imagens": [
            {"src": "img/produtos/colar_castissimo_coracao_sao_jose_frente.jpg", "rotulo": None},
        ],
        "descricao_curta": "Pingente de coração vermelho com ramo de lírio, banhado a ouro.",
        "descricao": [
            "O Castíssimo Coração de São José representa a pureza e a fidelidade "
            "do esposo de Maria e pai adotivo de Jesus — o ramo de lírio junto ao "
            "coração é o símbolo tradicional da castidade de São José.",
            "Peça delicada e discreta, banhada a ouro, pensada pra quem tem "
            "devoção a São José — patrono das famílias, dos trabalhadores e da "
            "Igreja — ou pra presentear alguém com essa proteção.",
        ],
        "medidas": "Pingente ≈ 16mm x 12mm · Corrente ≈ 40cm + 5cm de extensor",
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
