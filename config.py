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

# Sincronizacao de pedidos pagos com a Tiny/Olist ERP (API v2, ver
# services/tiny.py). Credencial de verdade -- NUNCA gravar o valor
# aqui, so variavel de ambiente TINY_API_TOKEN no servidor. Sem ela, a
# sincronizacao so fica desligada (o pedido continua sendo salvo
# normalmente no site, so nao entra na Tiny sozinho).
TINY_API_TOKEN = os.environ.get("TINY_API_TOKEN", "")

# E-mail transacional via Brevo (ver services/email.py) -- disparado
# quando o pagamento e´ confirmado, com o link de acompanhamento do
# pedido (o site nao tem login, ver conversa que definiu essa escolha
# -- sem o e-mail, se o cliente perder a aba/link, nao acha o pedido
# de novo sozinho). Credencial de verdade -- NUNCA gravar o valor
# aqui, so variavel de ambiente BREVO_API_KEY no servidor.
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")

# Remetente dos e-mails -- nao e´ segredo (aparece publico em todo
# e-mail enviado), pode ficar no codigo como padrao.
EMAIL_REMETENTE = os.environ.get("EMAIL_REMETENTE", "pedidos@lojanovedejulho.com.br")
EMAIL_REMETENTE_NOME = os.environ.get("EMAIL_REMETENTE_NOME", "Nove de Julho")

# Pra onde manda o aviso de "nova venda confirmada" (ver
# services/email.py:enviar_notificacao_venda) -- nao e´ segredo, padrao
# ja´ e´ o e-mail que voce ja monitora hoje.
EMAIL_NOTIFICACAO_VENDA = os.environ.get("EMAIL_NOTIFICACAO_VENDA", "9djulho@gmail.com")

# Notificacao push no navegador (ver services/push.py) -- par de chaves
# VAPID gerado uma unica vez (identifica o servidor pros servicos de
# push do navegador, tipo Google/Mozilla). Credencial de verdade --
# NUNCA gravar o valor aqui, so variavel de ambiente no servidor. Sem
# essas duas configuradas, a notificacao push fica desligada (mesmo
# padrao de BREVO_API_KEY ausente) -- so o e-mail de venda continua
# funcionando normalmente.
VAPID_PRIVATE_KEY_PEM = os.environ.get("VAPID_PRIVATE_KEY_PEM", "")
VAPID_PUBLIC_KEY_PEM = os.environ.get("VAPID_PUBLIC_KEY_PEM", "")
VAPID_SUBSCRIBER_EMAIL = os.environ.get("VAPID_SUBSCRIBER_EMAIL", "9djulho@gmail.com")

# Painel interno de pedidos (/admin/pedidos, ver app.py) -- autenticacao
# HTTP Basic simples (um usuario so, sem sessao/cookie). As duas
# credenciais SAO segredo -- NUNCA gravar aqui, so variavel de
# ambiente no servidor. Sem as duas configuradas, o painel fica
# bloqueado por padrao (nunca expõe pedido de ninguem sem senha).
ADMIN_USER = os.environ.get("ADMIN_USER", "")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

# Segredo compartilhado do webhook de pagamento (ver app.py:webhook_infinitepay
# e services/infinitepay.py:criar_link_pagamento) -- vai como query string
# (?chave=...) na webhook_url que a gente manda pra InfinitePay na hora de
# criar o link de pagamento, e o servidor exige o mesmo valor de volta em
# toda chamada. Sem isso, qualquer um que descobrisse o token de um pedido
# (aparece na URL de acompanhamento, /pedido/<token>) podia forjar uma
# chamada de webhook e marcar o proprio pedido como pago sem ter pago de
# verdade. NUNCA gravar o valor aqui -- variavel de ambiente
# WEBHOOK_INFINITEPAY_SECRET no servidor (gere algo aleatorio longo, ex:
# `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`). Sem
# configurar, o webhook continua aceitando qualquer chamada (comportamento
# de antes) -- configure em producao assim que possivel.
WEBHOOK_INFINITEPAY_SECRET = os.environ.get("WEBHOOK_INFINITEPAY_SECRET", "")

# Lembrete automatico pra pedido criado (pendente) que nao foi pago
# depois de um tempo -- job agendado com APScheduler (ver app.py).
# Desligado por padrao -- so liga em producao, setando
# ENABLE_SCHEDULER=true no servidor. NUNCA ligar em teste/dev: senao
# sobe uma thread de fundo rodando de verdade, mandando e-mail de
# verdade sem querer.
ENABLE_SCHEDULER = os.environ.get("ENABLE_SCHEDULER", "").lower() in ("1", "true", "yes")

# Quanto tempo esperar (pedido "pendente" sem pagar) antes do lembrete.
LEMBRETE_MINUTOS = int(os.environ.get("LEMBRETE_MINUTOS", "30"))

# Quanto tempo esperar DEPOIS do lembrete (2o link) antes de cancelar
# automaticamente um pedido que continua "pendente" -- job agendado
# junto com o lembrete acima (ver app.py). Contagem a partir de
# email_lembrete_enviado_em, nao de criado_em -- ou seja, o pedido e´
# cancelado LEMBRETE_MINUTOS + CANCELAMENTO_MINUTOS_APOS_LEMBRETE
# depois de criado, no total.
CANCELAMENTO_MINUTOS_APOS_LEMBRETE = int(os.environ.get("CANCELAMENTO_MINUTOS_APOS_LEMBRETE", "30"))

# Quanto tempo esperar depois do PAGAMENTO confirmado antes de mandar o
# e-mail de oportunidade (empurrao pra proxima faixa de desconto no
# proximo pedido) -- ver app.py:_enviar_upsell_pedidos_pagos.
UPSELL_HORAS_APOS_PAGAMENTO = int(os.environ.get("UPSELL_HORAS_APOS_PAGAMENTO", "24"))

# Quanto tempo esperar depois do pagamento antes de pedir avaliacao por
# e-mail (link pra um dos santos do pedido) -- ver
# app.py:_enviar_pedidos_para_avaliacao.
AVALIACAO_DIAS_APOS_PAGAMENTO = int(os.environ.get("AVALIACAO_DIAS_APOS_PAGAMENTO", "30"))

# Prazo de producao em DIAS UTEIS depois do pagamento confirmado, antes
# do pedido ser enviado -- mesma promessa ja usada como texto fixo em
# varias paginas ("prazo de ate 5 dias uteis antes do envio"). Usado
# pra calcular a previsao de envio/entrega mostrada no painel admin e
# na timeline do cliente (ver app.py:_previsoes_do_pedido).
PRODUCAO_DIAS_UTEIS = int(os.environ.get("PRODUCAO_DIAS_UTEIS", "5"))

GA4_MEASUREMENT_ID = os.environ.get("GA4_MEASUREMENT_ID", "G-RXVM530CM6")
META_PIXEL_ID = os.environ.get("META_PIXEL_ID", "28592446083693889")

# Dashboard de leitura no painel admin (ver services/analytics.py,
# /admin/analytics) -- API DIFERENTE do GA4_MEASUREMENT_ID acima (aquele
# so ENVIA eventos pro Google; esta le os numeros de volta). Precisa de
# uma conta de servico do Google Cloud com acesso de Leitor na
# propriedade GA4 (gerada em console.cloud.google.com, adicionada como
# leitora em analytics.google.com -> Administrador -> Gerenciamento de
# acesso). Credencial de verdade -- NUNCA gravar aqui, so variavel de
# ambiente no servidor. GA4_SERVICE_ACCOUNT_JSON e´ o conteudo INTEIRO
# do arquivo JSON baixado do Google Cloud (cole como veio, com quebras
# de linha e tudo).
GA4_SERVICE_ACCOUNT_JSON = os.environ.get("GA4_SERVICE_ACCOUNT_JSON", "")
GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "")

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
        # "chave" e´ so uso interno (template da home intercala esses 3
        # grupos com outras secoes, ver index() em app.py) -- nao
        # aparece pro usuario, so o "titulo" abaixo.
        "chave": "mais_vendidos",
        "titulo": "🔥 Mais vendidos",
        "produtos": ["sao-jose", "santa-teresinha", "carlo-acutis", "sagrada-familia", "sao-joao-paulo-ii"],
    },
    {
        "chave": "ano_jubilar",
        "titulo": "🕊️ Ano Jubilar de São Francisco",
        # mostra os modelos do proprio Sao Francisco (nao produtos
        # diferentes) -- ver _montar_destaques em app.py.
        "modelos_de": "sao-francisco",
    },
    {
        "chave": "novidades",
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
