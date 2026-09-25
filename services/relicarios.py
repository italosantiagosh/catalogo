"""
Relicarios -- peca EXCLUSIVA DO VAREJO (pedido em 2026-09-25, mesma
conversa/mesmo padrao de services/colares.py e services/pulseiras.py).
Fotos baixadas da propria pagina do fornecedor que a usuaria revende
(lojaparresia.com.br), mesmo criterio ja usado pros colares/pulseira.

Precos (pedido: "Precos iguais ao parresia. So diminui 3 pra ficar com
terminacao 7") aplicados sobre o preco ATUAL (com desconto) que a Parresia
mostra hoje, nao o preco "de": relicario coracao ouro R$100,00-3=R$97,00,
relicario redondo prata R$280,00-3=R$277,00, oval familia R$120,00-3=
R$117,00.

Dois modelos sao PERSONALIZAVEIS com foto do cliente (coracao-banhado-a-
ouro e redondo-prata-zirconia) -- igual a Parresia faz, mas SEM gerar
previa automatica (a loja nao tem gerador de mockup pra relicario ainda,
ver conversa: "não gerar previa(não criei modelo)") -- o cliente pode
anexar a foto na propria pagina (so fica guardada junto do pedido, sem
compor nenhuma imagem) ou deixar pra enviar depois; o aviso avisa que a
Nove de Julho entra em contato pelo WhatsApp pra confirmar/mostrar uma
possivel previa antes de produzir. O Pingente Relicario Oval "Familia" NAO
e personalizavel -- a propria pagina de origem no fornecedor mostra que ja
vem como colar completo (pingente + corrente), sem opcao de foto.

Cada relicario personalizavel tem uma CORRENTE companheira pra upsell
("aviso" no proprio card do relicario + popup ao adicionar no carrinho,
ver templates/relicarios.html e static/js/relicarios.js) -- NAO e um
catalogo proprio de "Correntes", so um complemento oferecido junto (pedido:
"as correntes entram só como complemento... sem página própria"). Preco
da corrente tambem "igual Parresia menos 3", mas o preco delas termina em
5 (R$115,00/R$135,00) entao "menos 3" NAO cai em terminacao 7
(R$112,00/R$132,00) -- aplicado do jeito que foi pedido (regra literal),
sem inventar outro ajuste. O Oval Familia NAO tem corrente companheira
(ver acima -- ja vem com a propria corrente incluida)."""

from __future__ import annotations

RELICARIOS = [
    {
        "id": "coracao-banhado-a-ouro",
        "nome": "Relicário Coração Banhado a Ouro Personalizado",
        "chave_preco": "relicario_coracao_ouro",
        "publicado": True,
        "personalizavel": True,
        "imagens": [
            {"src": "img/produtos/relicario_coracao_ouro_frente.jpg", "rotulo": None},
        ],
        "descricao_curta": "Pingente relicário em formato de coração, banhado a ouro, com espaço pra guardar uma foto especial.",
        "descricao": [
            "Algumas joias vão além da beleza: carregam histórias, rostos e "
            "lembranças que merecem estar sempre por perto. Este pingente "
            "relicário em formato de coração foi pensado pra guardar uma foto "
            "especial, transformando um momento importante em algo que você "
            "pode levar todos os dias junto ao peito.",
            "Discreto, delicado e cheio de significado — ideal pra quem busca "
            "uma joia que fale de amor, família, fé ou saudade sem exageros, "
            "mas com profundidade.",
        ],
        "medidas": "Pingente relicário com abertura frontal · Banhado a ouro",
        "corrente": {
            "nome": "Corrente Veneziana Fio Fechada (40+5cm) Banhada a Ouro",
            "chave_preco": "corrente_veneziana_ouro",
            "imagem": "img/produtos/corrente_veneziana_ouro.jpg",
        },
    },
    {
        "id": "redondo-prata-zirconia",
        "nome": "Relicário Redondo Prata com Zircônia Coração",
        "chave_preco": "relicario_redondo_prata",
        "publicado": True,
        "personalizavel": True,
        "imagens": [
            {"src": "img/produtos/relicario_redondo_prata_frente.jpg", "rotulo": None},
            {"src": "img/produtos/relicario_redondo_prata_detalhe.jpg", "rotulo": "fechado"},
        ],
        "descricao_curta": "Relicário redondo em prata 925 com coração de zircônias, com espaço pra guardar uma foto especial.",
        "descricao": [
            "Um relicário é mais do que uma joia: é um lugar de memória. Um "
            "jeito delicado e discreto de carregar perto do coração a imagem "
            "de alguém especial — família, filhos, casal, amigos ou até um "
            "santo de devoção.",
            "Este modelo é em prata 925 e traz um detalhe encantador: um "
            "coração com zircônias na parte frontal, dando brilho e "
            "sofisticação sem perder a leveza.",
        ],
        "medidas": "Relicário redondo com abertura frontal · Prata 925",
        "corrente": {
            "nome": "Corrente Prata Veneziana Diamantada (45cm)",
            "chave_preco": "corrente_veneziana_prata",
            "imagem": "img/produtos/corrente_veneziana_prata.jpg",
        },
    },
    {
        "id": "oval-familia",
        "nome": "Pingente Relicário Oval Família Coração",
        "chave_preco": "relicario_oval_familia",
        "publicado": True,
        "personalizavel": False,
        "imagens": [
            {"src": "img/produtos/relicario_oval_familia_frente.jpg", "rotulo": None},
            {"src": "img/produtos/relicario_oval_familia_uso.jpg", "rotulo": "sendo usado"},
        ],
        "descricao_curta": "Pingente relicário oval com a palavra Família e coração cravejado, banhado a ouro.",
        "descricao": [
            "Uma joia delicada e cheia de significado, criada pra representar "
            "aquilo que temos de mais precioso: o amor, a união e a proteção "
            "de Deus sobre a nossa casa.",
            "Com a palavra Família e um coração cravejado, este relicário é "
            "um lembrete diário de carinho, fé e gratidão por aqueles que "
            "Deus colocou em nossa vida — já vem completo, com a corrente "
            "inclusa, pronto pra usar.",
        ],
        "medidas": "Pingente ≈ 18mm · Banhado a ouro · Já vem com corrente",
        "corrente": None,
    },
]

PRECO_RELICARIO_CORACAO_OURO_REAIS = 97.00
PRECO_RELICARIO_REDONDO_PRATA_REAIS = 277.00
PRECO_RELICARIO_OVAL_FAMILIA_REAIS = 117.00


def relicarios_publicados() -> list[dict]:
    return [r for r in RELICARIOS if r["publicado"]]


def relicario_por_id(relicario_id: str) -> dict | None:
    for r in RELICARIOS:
        if r["id"] == relicario_id and r["publicado"]:
            return r
    return None
