"""
Configuracao central do catalogo -- valores que nao devem ficar
espalhados pelo codigo.
"""

import os
import re

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
# Checkout automatico via InfinitePay (Pix + cartao, ver
# services/infinitepay.py). O "handle" (@usuario) NAO e credencial --
# aparece publico em todo link de pagamento gerado, mesmo raciocinio do
# PIX_CHAVE acima. Sem o "$" do inicio (a API pede assim).
INFINITEPAY_HANDLE = os.environ.get("INFINITEPAY_HANDLE", "novedejulho")

# Token de API da InfinitePay -- esse SIM e credencial (Bearer token
# opcional, ver services/infinitepay.py). NUNCA gravar o valor aqui, so
# variavel de ambiente INFINITEPAY_API_TOKEN no servidor. A criacao de
# link de pagamento funciona mesmo sem ele (endpoint publico) -- fica
# vazio ate ser necessario.
INFINITEPAY_API_TOKEN = os.environ.get("INFINITEPAY_API_TOKEN", "")

GA4_MEASUREMENT_ID = os.environ.get("GA4_MEASUREMENT_ID", "G-RXVM530CM6")
META_PIXEL_ID = os.environ.get("META_PIXEL_ID", "28592446083693889")

# Codigo de verificacao de propriedade do Google Search Console (metodo
# "tag HTML" -- cole so o valor do content="..." que o Search Console
# mostra, sem o resto da tag). Vazio por padrao: o <meta> em base.html
# so aparece quando essa variavel de ambiente estiver definida.
GOOGLE_SITE_VERIFICATION = os.environ.get("GOOGLE_SITE_VERIFICATION", "")

# Dominio canonico definitivo do site (o custom domain configurado no
# Render, ex: "atacado.lojanovedejulho.com.br", SEM "https://"). Quando
# definido, todo acesso por outro host (o subdominio gratuito do
# Render, catalogo-medalhas.onrender.com) e redirecionado 301 pra ca --
# evita conteudo duplicado no Google (a mesma pagina acessivel por duas
# URLs diferentes). Ver app.py:_redirecionar_para_dominio_canonico.
#
# Vazio por padrao = redirecionamento desligado. So defina isso DEPOIS
# que o dominio customizado estiver configurado no Render E o DNS
# propagado -- ativar antes disso tira o site do ar (ninguem chega a
# nenhum dos dois enderecos).
#
# Tolera colar o valor com "http(s)://" na frente e/ou "/" no final
# (jeito mais natural de copiar um endereco) -- sem isso, colar com o
# esquema gera um redirect quebrado tipo "https://https://dominio/"
# (o navegador mostra so "http" e da erro de DNS).
def _normalizar_dominio(valor: str) -> str:
    return re.sub(r"^https?://", "", valor.strip()).rstrip("/")


CANONICAL_DOMAIN = _normalizar_dominio(os.environ.get("CANONICAL_DOMAIN", ""))

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

# "Mais procurados" -- 4 santos em destaque logo no topo da home
# (pedido explicito do usuario), com botao pra ver o catalogo completo
# logo depois. A grade completa continua na mesma pagina, mais abaixo
# (nao vira uma pagina separada) -- crawler ainda ve todos os 130+
# produtos no HTML da home, so a ordem visual muda. As 2 devocoes
# marianas foram escolhidas por serem provavelmente as mais populares
# no Brasil: Aparecida (padroeira do Brasil) e Desatadora dos Nos
# (devocao muito procurada atualmente).
PROCURADOS_HOME = ["sao-miguel", "sao-bento", "nossa-senhora-aparecida", "nossa-senhora-desatadora-dos-nos"]

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
        # mostra os modelos do proprio Sao Francisco (nao produtos
        # diferentes) -- ver _montar_destaques em app.py.
        "modelos_de": "sao-francisco",
    },
    {
        "titulo": "✨ Novidades",
        "produtos": ["sao-pier-giorgio-frassati", "beata-sandra-sabatine", "filho-prodigo-acamps"],
    },
]

# Kit inicial sugerido "Livraria Shalom" (ver app.py:kit_livraria_shalom,
# templates/kit.html) -- sortimento que o cliente ja mandava manualmente
# pelo WhatsApp pra quem pede em quantidade grande e nao sabe por onde
# comecar. As quantidades aqui sao SO um ponto de partida: a pagina deixa
# o cliente aumentar/diminuir/zerar cada item, e o tamanho da medalha
# (12mm/16mm/misturado) e escolhido na propria pagina, nao aqui.
# "rotulo_extra" desambigua quando o mesmo produto entra duas vezes com
# modelos diferentes (Toda Pequena e Jardim Fechado, um modelo mais
# "aberto"/de corpo inteiro e outro mais fechado/de rosto).
KIT_LIVRARIA_SHALOM = [
    {"produto_id": "santa-teresinha", "modelo_id": 1, "quantidade_sugerida": 20},
    {"produto_id": "sao-jose", "modelo_id": 1, "quantidade_sugerida": 20},
    {"produto_id": "sagrada-familia", "modelo_id": 1, "quantidade_sugerida": 8},
    {"produto_id": "santa-teresa-davila", "modelo_id": 1, "quantidade_sugerida": 4},
    {"produto_id": "sao-francisco", "modelo_id": 1, "quantidade_sugerida": 4},
    {"produto_id": "nossa-senhora-toda-pequena", "modelo_id": 1, "quantidade_sugerida": 4, "rotulo_extra": "modelo longe"},
    {"produto_id": "nossa-senhora-toda-pequena", "modelo_id": 2, "quantidade_sugerida": 4, "rotulo_extra": "modelo perto"},
    {"produto_id": "esposa-do-espirito", "modelo_id": 1, "quantidade_sugerida": 2},
    {"produto_id": "nossa-senhora-rainha-da-paz", "modelo_id": 1, "quantidade_sugerida": 2},
    {"produto_id": "nossa-senhora-porta-do-ceu", "modelo_id": 1, "quantidade_sugerida": 2},
    {"produto_id": "chiara-luce", "modelo_id": 1, "quantidade_sugerida": 2},
    {"produto_id": "chiara-corbella", "modelo_id": 1, "quantidade_sugerida": 2},
    {"produto_id": "carlo-acutis", "modelo_id": 1, "quantidade_sugerida": 4},
    {"produto_id": "nossa-senhora-do-sorriso", "modelo_id": 1, "quantidade_sugerida": 2},
    {"produto_id": "sao-joao-paulo-ii", "modelo_id": 1, "quantidade_sugerida": 4},
    {"produto_id": "sao-miguel", "modelo_id": 1, "quantidade_sugerida": 4},
    {"produto_id": "santa-gianna", "modelo_id": 1, "quantidade_sugerida": 4},
    {"produto_id": "pais-de-teresinha", "modelo_id": 1, "quantidade_sugerida": 4},
    {"produto_id": "sao-padre-pio", "modelo_id": 1, "quantidade_sugerida": 4},
]

# Descricoes por categoria -- usadas na pagina /categoria/<slug>
# (app.py/templates/categoria.html) como H1/intro + meta description,
# pra cada categoria virar uma URL indexavel de verdade (SEO), em vez
# de so um filtro por clique na home. Estrutura igual em todas (pedido
# do usuario): 1a frase com exemplos reais de produtos da categoria
# (conteudo unico por pagina), 2a frase padrao sobre formato/atacado.
DESCRICOES_CATEGORIA = {
    "Nossa Senhora": (
        "Mais de 30 apresentações e títulos de Nossa Senhora — Aparecida, Desatadora dos "
        "Nós, Imaculado Coração, La Salete e outras devoções marianas — em medalha, "
        "entremeio ou chaveiro. Desconto de atacado automático conforme a quantidade, "
        "sem cupom."
    ),
    "Santos": (
        "O maior grupo do catálogo, com 36 santos canonizados — de Santo Antônio e Santo "
        "Expedito a Carlo Acutis e São José — em medalha, entremeio ou chaveiro. Desconto "
        "de atacado automático conforme a quantidade, sem cupom."
    ),
    "Santas": (
        "20 santas da Igreja Católica — Santa Clara, Santa Dulce, Santa Faustina, Edith "
        "Stein e outras — em medalha, entremeio ou chaveiro. Desconto de atacado "
        "automático conforme a quantidade, sem cupom."
    ),
    "Devoções": (
        "Devoções e passagens marcantes da fé católica — Bodas de Caná, Cântico dos "
        "Cânticos, Filho Pródigo, Frei Damião — em medalha, entremeio ou chaveiro. "
        "Desconto de atacado automático conforme a quantidade, sem cupom."
    ),
    "Jesus": (
        "Representações de Jesus Cristo — Bom Pastor, Cristo Rei, Jesus Misericordioso, "
        "Sagrada Face — em medalha, entremeio ou chaveiro. Desconto de atacado automático "
        "conforme a quantidade, sem cupom."
    ),
    "Outros": (
        "Peças e devoções que não se encaixam nas demais categorias, com a mesma "
        "variedade e qualidade do catálogo — em medalha, entremeio ou chaveiro. Desconto "
        "de atacado automático conforme a quantidade, sem cupom."
    ),
    "Famílias": (
        "Representações de família na tradição católica — Sagrada Família, Família "
        "Martin, Pais de Teresinha — em medalha, entremeio ou chaveiro. Desconto de "
        "atacado automático conforme a quantidade, sem cupom."
    ),
    "Beatos": (
        "Beatos e beatas da Igreja, em diferentes etapas do processo de canonização — "
        "Carlo Acutis, Sandra Sabattini, Beata Nhá Xica — em medalha, entremeio ou "
        "chaveiro. Desconto de atacado automático conforme a quantidade, sem cupom."
    ),
    "Anjos": (
        "Anjos e arcanjos da tradição católica — São Miguel, São Gabriel, São Rafael e "
        "os Santos Arcanjos — em medalha, entremeio ou chaveiro. Desconto de atacado "
        "automático conforme a quantidade, sem cupom."
    ),
    "Espírito Santo": (
        "O Espírito Santo, Pentecostes e a Santíssima Trindade — presente tradicional de "
        "crisma e confirmação — em medalha, entremeio ou chaveiro. Desconto de atacado "
        "automático conforme a quantidade, sem cupom."
    ),
}

# Descricoes por FORMATO (nao confundir com DESCRICOES_CATEGORIA acima,
# que e por santo/devocao) -- pedido do usuario: "uma descricao padrao
# pra medalha, uma pra entremeio (16mm de diametro interno) e chaveiro
# (30mm de diametro interno)". Usada em templates/produto.html, embaixo
# do seletor de formato (services/gerador/config.py:MEDAL_SPECS tem a
# geometria calibrada -- aqui e so o texto explicativo pro cliente).
DESCRICOES_FORMATO = {
    "medalha": (
        "Medalha resinada em aço inoxidável, disponível em 1,2 cm ou 1,6 cm de diâmetro. "
        "O formato mais tradicional, ideal pra usar em colar ou pulseira no dia a dia."
    ),
    "entremeio": (
        "Entremeio resinado em aço inoxidável, com 1,6 cm de diâmetro interno. Passa "
        "direto no cordão do terço/rosário, pra montar seu próprio terço com o santo "
        "de devoção."
    ),
    "chaveiro": (
        "Peça resinada em aço inoxidável, com 3 cm de diâmetro interno — o maior formato "
        "do catálogo. Ótimo pra levar na bolsa, mochila ou chaveiro, ou pra presentear."
    ),
}
