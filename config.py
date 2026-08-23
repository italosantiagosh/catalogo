"""
Configuracao central do catalogo -- valores que nao devem ficar
espalhados pelo codigo.
"""

import os

# Numero de WhatsApp para onde os pedidos sao enviados (ETAPA 9). So a
# constante por enquanto -- os botoes de finalizar pedido/tirar duvida
# ainda nao existem.
WHATSAPP_NUMBER = "5584981276650"

# Frete (calculadora do carrinho, ver services/frete.py). O token da
# Frenet e uma credencial -- NUNCA gravar o valor aqui nem em nenhum
# outro arquivo do repositorio; configurar como variavel de ambiente
# FRENET_TOKEN no servidor (Render: Settings > Environment) e, para
# rodar local, exportar no shell antes de `flask run`.
FRENET_TOKEN = os.environ.get("FRENET_TOKEN", "")

# CEP de onde os pedidos sao despachados -- usado como origem em toda
# cotacao de frete. Nao e segredo, pode ficar no codigo -- variavel de
# ambiente so se precisar sobrescrever sem redeploy.
CEP_ORIGEM = os.environ.get("CEP_ORIGEM", "59088-040")

# Token de acesso pessoal do Melhor Envio -- usado so pra cotar Azul
# Express com a tarifa contratada pelo usuario ali (nao pra gerar
# etiqueta/frete de verdade). Mesma regra do FRENET_TOKEN: NUNCA
# gravar o valor aqui, so variavel de ambiente MELHOR_ENVIO_TOKEN no
# servidor. Esse token em especial tem escopos bem mais amplos que o
# necessario (inclui shipping-generate, products-write, users-write
# etc.) -- o codigo aqui so chama o endpoint de cotacao
# (shipping-calculate), mas se puder gerar um token so com esse
# escopo no painel do Melhor Envio, e mais seguro trocar por um mais
# restrito.
MELHOR_ENVIO_TOKEN = os.environ.get("MELHOR_ENVIO_TOKEN", "")

# Pix (recebimento, ver services/pix.py). A chave Pix NAO e uma
# credencial no sentido de senha/token -- e feita pra ser publicada e
# escaneada por qualquer cliente (mesmo principio de um QR impresso
# numa maquininha de cartao): so permite que mandem dinheiro pra
# conta, nao da acesso a nada. Por isso fica direto no codigo, como o
# CEP_ORIGEM -- variavel de ambiente so se quiser trocar sem redeploy.
# Nome e cidade aparecem pro cliente no app do banco ao escanear;
# CIDADE foi assumida como Natal/RN a partir do CEP_ORIGEM (faixa
# 590xx-599xx) -- confirme/corrija se estiver errado.
PIX_CHAVE = os.environ.get("PIX_CHAVE", "39390354000125")
PIX_NOME_RECEBEDOR = os.environ.get("PIX_NOME_RECEBEDOR", "NOVE DE JULHO")
PIX_CIDADE = os.environ.get("PIX_CIDADE", "NATAL")

# Analytics/rastreamento de conversao (ver templates/base.html). Nao
# sao segredos -- IDs de rastreamento vao direto no HTML publico de
# qualquer site que os usa, quem os ve nao ganha acesso a nada (so
# permitem MANDAR eventos pra essas contas, e so funciona com a conta
# ja logada do dono no painel do Google/Meta). Variavel de ambiente so
# se quiser trocar sem redeploy.
GA4_MEASUREMENT_ID = os.environ.get("GA4_MEASUREMENT_ID", "G-RXVM530CM6")
META_PIXEL_ID = os.environ.get("META_PIXEL_ID", "28592446083693889")

# Instagram da loja -- usado no bloco de prova social da pagina de
# produto (ver templates/produto.html).
INSTAGRAM_URL = "https://www.instagram.com/novedjulho/"

# Video de apresentacao (bolinha flutuante, ver base.html/
# video_flutuante.js). Hospedado pelo proprio usuario fora do
# repositorio (Cloudflare R2) -- so o link, o navegador do visitante
# busca direto, o servidor nunca baixa/processa esse arquivo.
VIDEO_APRESENTACAO_URL = os.environ.get(
    "VIDEO_APRESENTACAO_URL",
    "https://pub-dedea83ede484eb2bb09060b6522aaa2.r2.dev/Video%20reduzido%20para%20shopee.mp4",
)

# Prova social (ver templates/produto.html) -- fotos e legendas que o
# usuario ja usava no site oficial (Yampi), reaproveitadas aqui.
# Imagens hospedadas externamente (ibb.co/postimg.cc) pelo proprio
# usuario -- o servidor so referencia a URL, quem busca a imagem e o
# navegador de quem esta vendo a pagina, entao nao depende de rede do
# servidor pra funcionar.
PROVA_SOCIAL = [
    {
        "src": "https://i.ibb.co/gZXzWrHM/Whats-App-Image-2026-01-21-at-18-39-05-4.jpg",
        "texto": "Fornecemos para diversas livrarias",
    },
    {
        "src": "https://i.postimg.cc/QCyCWrYV/Whats-App-Image-2026-01-21-at-18-59-47.jpg",
        "texto": "Ótima qualidade e durável!",
    },
    {
        "src": "https://i.postimg.cc/ncpD8HB5/Whats-App-Image-2026-01-21-at-18-39-05-5.jpg",
        "texto": "Para presentear em retiros, grupos e eventos",
    },
    {
        "src": "https://i.postimg.cc/R0HF68wL/Whats-App-Image-2026-01-21-at-18-39-05-3.jpg",
        "texto": "Para devoção pessoal e colecionar",
    },
    {
        "src": "https://i.postimg.cc/pTWwb5Vn/Whats-App-Image-2026-01-21-at-18-39-05.jpg",
        "texto": "Presente em datas comemorativas",
    },
    {
        "src": "https://i.postimg.cc/28sgjKjW/Whats-App-Image-2026-01-21-at-18-39-05-2.jpg",
        "texto": "Presente entre namorados, agora casados",
    },
    {
        "src": "https://i.postimg.cc/Y2Vs8sFF/Whats-App-Image-2026-01-21-at-18-39-05-1.jpg",
        "texto": "Quem compra sempre quer mais uma depois!",
    },
]

# Destaques da home (ver app.py:_montar_destaques, templates/index.html)
# -- reduz a paralisia de escolha de quem chega e ve os 130+ santos
# todos "iguais". IDs conferidos contra data/produtos.json; um id que
# nao existir mais e simplesmente ignorado (nao quebra a pagina).
DESTAQUES_HOME = [
    {
        "titulo": "🔥 Mais vendidos",
        "produtos": ["sao-jose", "santa-teresinha", "carlo-acutis", "sagrada-familia", "sao-joao-paulo-ii"],
    },
    {
        "titulo": "🕊️ Ano Jubilar de São Francisco",
        "produtos": ["sao-francisco", "santa-clara"],
    },
    {
        "titulo": "✨ Novidades",
        "produtos": ["sao-pier-giorgio-frassati", "beata-sandra-sabatine", "filho-prodigo-acamps"],
    },
]
