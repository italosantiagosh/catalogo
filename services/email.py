"""
E-mail transacional via Brevo (ex-Sendinblue) -- ver
app.py:webhook_infinitepay, disparado uma unica vez por pedido quando
o pagamento e´ confirmado (services.pedidos.marcar_email_enviado evita
reenvio em webhook duplicado).

O site nao tem cadastro de cliente (ver conversa que definiu essa
escolha) -- o link de acompanhamento do pedido (/pedido/<token>) so
chega pro cliente no redirecionamento pos-pagamento. Sem esse e-mail,
se ele fechar a aba ou perder o link, nao tem como achar o pedido de
novo sozinho. /meus-pedidos (ver app.py e enviar_codigo_verificacao
abaixo) e´ um atalho OPCIONAL em cima disso -- login por CPF + codigo
de 6 digitos mandado por aqui, sem senha pra guardar -- pra quem quer
ver de nova todos os proprios pedidos sem ter salvo cada link avulso.

API da Brevo: https://developers.brevo.com/docs/send-a-transactional-email
"""

from __future__ import annotations

import html
from urllib.parse import quote

import requests

from config import (
    BREVO_API_KEY,
    BREVO_LIST_ID,
    CANONICAL_DOMAIN,
    EMAIL_NOTIFICACAO_VENDA,
    EMAIL_REMETENTE,
    EMAIL_REMETENTE_NOME,
    INSTAGRAM_URL,
    WHATSAPP_NUMBER,
)
from services.pedidos import previsoes_do_pedido
from services.pricing import pedido_minimo_reais

API_URL = "https://api.brevo.com/v3/smtp/email"
CONTATOS_API_URL = "https://api.brevo.com/v3/contacts"

# Todo campo que vem do que o cliente digitou no checkout (nome,
# telefone, descricao/frete escolhidos) ou que o admin digita no painel
# (motivo de exclusao, rastreio) passa por aqui antes de entrar num
# f-string de HTML de e-mail -- sem isso, dava pra injetar HTML no
# proprio e-mail de confirmacao do cliente OU no aviso interno de nova
# venda que o dono le (ver conversa "tornar o site e apis seguros").
_esc = html.escape


def _preco(valor: float) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


# Placeholder de peca personalizada sem foto ainda (ver
# static/js/personalizada.js e templates/pedido.html:IMAGEM_SEM_FOTO) --
# mostrar esse icone generico como "foto do produto" no e-mail confundiria
# mais do que ajudaria, entao esses itens ficam so com o texto mesmo.
_IMAGEM_SEM_FOTO = "/static/img/sem-foto.svg"


def _url_imagem_absoluta(caminho: str) -> str:
    """E-mail nao tem "base" como o navegador -- precisa da URL completa
    (com dominio) pra imagem aparecer, diferente de um <img src="/static/...">
    que funciona direto no site. Sem CANONICAL_DOMAIN configurado (dev/teste)
    devolve vazio -- melhor nenhuma miniatura do que uma quebrada."""
    if not caminho or caminho == _IMAGEM_SEM_FOTO:
        return ""
    if caminho.startswith("http://") or caminho.startswith("https://"):
        return caminho
    if not CANONICAL_DOMAIN:
        return ""
    return f"https://{CANONICAL_DOMAIN}{caminho}"


def _imagem_do_item(item: dict) -> str:
    """Miniatura pro item -- prioriza imagemRecorte (preview final ja´
    composto de peca personalizada) sobre a imagem crua; pecas de 2 lados
    (ver app.py:_itens_com_descricao_do_corpo) so guardam imagemLado1/2,
    sem "imagem" direto, entao cai nesse fallback."""
    bruta = item.get("imagemRecorte") or item.get("imagem") or item.get("imagemLado1") or ""
    return _url_imagem_absoluta(bruta)


def _linha_item_html(descricao: str, imagem: str) -> str:
    celula_imagem = (
        f'<td style="width:56px;padding:0 12px 10px 0;vertical-align:top;">'
        f'<img src="{_esc(imagem)}" width="44" height="44" alt="" '
        f'style="width:44px;height:44px;object-fit:cover;border-radius:8px;'
        f'border:1px solid #e2e7ee;display:block;"></td>'
        if imagem
        else ""
    )
    return (
        f"<tr>{celula_imagem}"
        f'<td style="padding:0 0 10px 0;vertical-align:middle;font-size:14px;">{descricao}</td></tr>'
    )


def _tabela_itens_html(linhas: list[str]) -> str:
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;">'
        + "".join(linhas)
        + "</table>"
    )


def _itens_html(pedido: dict) -> str:
    return _tabela_itens_html(
        [
            _linha_item_html(
                f"{_esc(item.get('descricao') or item.get('chave_preco', ''))} — {item['quantidade']}x",
                _imagem_do_item(item),
            )
            for item in pedido["itens"]
        ]
    )


# Botao com estilo inline (obrigatorio em e-mail -- clientes de e-mail
# ignoram <style>/classe externa) -- um link cru repetido como texto
# visivel (o que tinha antes) e´ um padrao que filtro de spam pontua mal,
# alem de ficar dificil de notar no celular (ver conversa).
def _botao(url: str, texto: str) -> str:
    return (
        f'<p style="margin:22px 0;">'
        f'<a href="{url}" target="_blank" '
        f'style="display:inline-block;padding:14px 28px;background-color:#14335c;color:#ffffff;'
        f'text-decoration:none;border-radius:8px;font-weight:bold;font-size:15px;'
        f'font-family:Arial,Helvetica,sans-serif;">{texto}</a>'
        f"</p>"
    )


def _com_utm(url: str, campanha: str) -> str:
    """UTM nos links dos e-mails -- sem isso o GA4 nao separa venda vinda
    de e-mail de trafego direto (ver conversa "apurar campanhas de
    e-mail"). Mesmo nome de campanha usado na tag do Brevo (ver
    _enviar/tag= em cada enviar_*), pra cruzar facil os dois. So aplicado
    em link do proprio site -- nunca em wa.me (_botao_whatsapp) nem em
    link de fora (Instagram, nota fiscal de terceiro etc)."""
    if not url:
        return url
    separador = "&" if "?" in url else "?"
    return f"{url}{separador}utm_source=email&utm_medium=email&utm_campaign={campanha}"


# Mesmo estilo do _botao() acima, so que verde/tema WhatsApp -- link
# wa.me com a mensagem ja´ preenchida (ver _corpo_html_pedido_enviado,
# caso "Retirada no local").
def _botao_whatsapp(mensagem: str, texto: str) -> str:
    url = f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(mensagem)}"
    return (
        f'<p style="margin:22px 0;">'
        f'<a href="{url}" target="_blank" '
        f'style="display:inline-block;padding:14px 28px;background-color:#25d366;color:#ffffff;'
        f'text-decoration:none;border-radius:8px;font-weight:bold;font-size:15px;'
        f'font-family:Arial,Helvetica,sans-serif;">{texto}</a>'
        f"</p>"
    )


def _corpo_html_confirmacao(pedido: dict, url_pedido: str) -> str:
    previsoes = previsoes_do_pedido(pedido)
    previsao_html = ""
    if previsoes["previsao_envio"]:
        previsao_html = (
            f"<p>🛠️ Seu pedido já está em produção -- previsão de envio até "
            f"<strong>{previsoes['previsao_envio'].strftime('%d/%m/%Y')}</strong>"
        )
        if previsoes["previsao_entrega"]:
            previsao_html += (
                f", com entrega prevista para <strong>{previsoes['previsao_entrega'].strftime('%d/%m/%Y')}</strong>"
            )
        previsao_html += ".</p>"
        if previsoes["previsao_entrega"]:
            previsao_html += (
                '<p style="font-size:13px;color:#5b6b82;font-style:italic;">'
                "ℹ️ O prazo de entrega é uma estimativa da transportadora -- imprevistos dela fogem do "
                "nosso controle e podem alterar essa data.</p>"
            )
    else:
        previsao_html = "<p>🛠️ Seu pedido já está em produção -- prazo de <strong>5 a 10 dias úteis</strong> (conforme a quantidade) antes do envio.</p>"
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Recebemos seu pagamento. 🎉</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"{_itens_html(pedido)}"
        f"<p>Frete ({_esc(pedido.get('frete_descricao', ''))}): {_preco(pedido.get('frete_preco', 0))}</p>"
        f"<p><strong>Total: {_preco(pedido['total'])}</strong></p>"
        f"{previsao_html}"
        f"<p>Acompanhe seu pedido a qualquer momento:</p>"
        f"{_botao(_com_utm(url_pedido, 'confirmacao_pedido'), '🔎 Clique aqui e acompanhe')}"
        f"<p>Qualquer dúvida, é só chamar no WhatsApp.</p>"
    )


def _corpo_html_link_pagamento(pedido: dict, url_pagamento: str, url_acompanhamento: str) -> str:
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Recebemos seu pedido, falta só o pagamento pra confirmar.</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"{_itens_html(pedido)}"
        f"<p>Frete ({_esc(pedido.get('frete_descricao', ''))}): {_preco(pedido.get('frete_preco', 0))}</p>"
        f"<p><strong>Total: {_preco(pedido['total'])}</strong></p>"
        f"{_botao(_com_utm(url_pagamento, 'link_pagamento'), '💳 Pagar agora (Pix ou cartão)')}"
        f"<p>Se esse link não abrir mais (expirou), é só acompanhar seu pedido "
        f"por aqui e gerar um novo:</p>"
        f"{_botao(_com_utm(url_acompanhamento, 'link_pagamento'), '🔎 Clique aqui e acompanhe')}"
        f"<p>Qualquer dúvida, é só chamar no WhatsApp.</p>"
    )


def _corpo_html_boleto_gerado(pedido: dict, url_acompanhamento: str) -> str:
    linha_html = (
        f"<p>Linha digitável: <strong>{_esc(pedido.get('inter_linha_digitavel', ''))}</strong></p>"
        if pedido.get("inter_linha_digitavel")
        else ""
    )
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Recebemos seu pedido -- seu boleto já está pronto.</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"{_itens_html(pedido)}"
        f"<p>Frete ({_esc(pedido.get('frete_descricao', ''))}): {_preco(pedido.get('frete_preco', 0))}</p>"
        f"<p><strong>Total: {_preco(pedido['total'])}</strong></p>"
        f"{linha_html}"
        f"<p>Baixe o boleto (PDF) ou pague com o Pix embutido nele acompanhando seu pedido:</p>"
        f"{_botao(_com_utm(url_acompanhamento, 'boleto_gerado'), '🔎 Ver boleto e acompanhar pedido')}"
        f'<p style="font-size:13px;color:#5b6b82;font-style:italic;">'
        "ℹ️ O pagamento do boleto é confirmado em até 2 dias úteis após você pagar -- "
        "o prazo de produção só começa depois dessa confirmação, não na hora em que você paga.</p>"
        f"<p>Qualquer dúvida, é só chamar no WhatsApp.</p>"
    )


def enviar_boleto_gerado(pedido: dict, url_acompanhamento: str) -> dict:
    """Disparado assim que o boleto e´ emitido na Inter (ver
    app.py:api_pedido_criar_boleto) -- garante que o cliente tem como
    achar a linha digitavel/PDF mesmo se fechar a aba antes de anotar.
    Devolve {"ok": True} ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=f"Seu boleto está pronto — Pedido #{pedido['codigo']}",
        corpo_html=_corpo_html_boleto_gerado(pedido, url_acompanhamento),
        tag="boleto_gerado",
    )


# Logo no topo de todo e-mail (ver conversa) -- mesmo brasao usado no
# painel admin e na aba do site (static/img/logo-icone.png). PNG com
# transparencia em vez do .webp usado no site: e-mail (Outlook em
# particular) tem suporte inconsistente a webp, PNG funciona em qualquer
# cliente. Some sozinho sem CANONICAL_DOMAIN (dev/teste), mesmo criterio
# de _url_imagem_absoluta -- melhor sem cabecalho do que um <img> quebrado.
def _cabecalho_html() -> str:
    logo_url = _url_imagem_absoluta("/static/img/logo-icone.png")
    if not logo_url:
        return ""
    return (
        f'<div style="text-align:center;padding:20px 0 22px;">'
        f'<img src="{logo_url}" alt="Nove de Julho" width="56" height="66" '
        f'style="width:56px;height:66px;display:inline-block;">'
        f"</div>"
    )


def _moldura_html(corpo_html: str) -> str:
    return (
        f'<div style="max-width:520px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:15px;line-height:1.5;color:#142238;">'
        f"{_cabecalho_html()}"
        f"{corpo_html}"
        f"</div>"
    )


def _enviar(*, email_cliente: str, nome_cliente: str, assunto: str, corpo_html: str, tag: str = "") -> dict:
    if not BREVO_API_KEY:
        return {"erro": "Envio de e-mail não configurado (falta BREVO_API_KEY)."}
    if not email_cliente:
        return {"erro": "Pedido sem e-mail do cliente."}

    destinatario = {"email": email_cliente}
    if nome_cliente:
        # Brevo rejeita "name" vazio com 400 -- enviar_notificacao_venda
        # (aviso interno pra loja, ver conversa) manda nome_cliente=""
        # de proposito, entao so inclui a chave quando tiver valor.
        destinatario["name"] = nome_cliente
    payload = {
        "sender": {"name": EMAIL_REMETENTE_NOME, "email": EMAIL_REMETENTE},
        "to": [destinatario],
        "subject": assunto,
        "htmlContent": _moldura_html(corpo_html),
    }
    if tag:
        # Sem isso, todo envio transacional aparece igual no Brevo (so´ da
        # pra ver o total, nunca separar lembrete de recompra de
        # confirmacao) -- ver conversa "apurar campanhas de e-mail": a
        # tag e´ o que deixa filtrar/comparar abertura e clique POR TIPO
        # de e-mail no painel do Brevo (Estatisticas > Transacional).
        payload["tags"] = [tag]
    try:
        resposta = requests.post(
            API_URL,
            json=payload,
            headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )
        resposta.raise_for_status()
    except requests.RequestException as exc:
        return {"erro": f"Não foi possível enviar o e-mail agora ({exc})."}
    return {"ok": True}


def inscrever_newsletter(email: str) -> dict:
    """Adiciona um e-mail na lista de newsletter do Brevo (novenas,
    historias de santos, produtos novos e novidades -- rodape do site,
    ver app.py:api_newsletter). updateEnabled=True faz o Brevo tratar
    reinscricao como um upsert em vez de erro 400 de duplicado -- quem
    ja´ assinou e assina de novo simplesmente nao muda nada."""
    if not BREVO_API_KEY or not BREVO_LIST_ID:
        return {"erro": "Newsletter não configurada (falta BREVO_API_KEY ou BREVO_LIST_ID)."}
    if not email or "@" not in email:
        return {"erro": "E-mail inválido."}
    try:
        resposta = requests.post(
            CONTATOS_API_URL,
            json={"email": email, "listIds": [int(BREVO_LIST_ID)], "updateEnabled": True},
            headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )
        resposta.raise_for_status()
    except requests.RequestException as exc:
        return {"erro": f"Não foi possível inscrever agora ({exc})."}
    return {"ok": True}


def listar_contatos_newsletter(limite: int = 200) -> dict:
    """Lista os contatos da lista de newsletter direto do Brevo, pro
    painel /admin/newsletter (ver app.py) -- consulta ao vivo, sem
    guardar copia local: o Brevo continua sendo a unica fonte de
    verdade (decisao do usuario, ver conversa 2026-09-24)."""
    if not BREVO_API_KEY or not BREVO_LIST_ID:
        return {"erro": "Newsletter não configurada (falta BREVO_API_KEY ou BREVO_LIST_ID).", "contatos": [], "total": 0}
    try:
        resposta = requests.get(
            f"{CONTATOS_API_URL}/lists/{BREVO_LIST_ID}/contacts",
            params={"limit": limite, "sort": "desc"},
            headers={"api-key": BREVO_API_KEY, "Accept": "application/json"},
            timeout=10,
        )
        resposta.raise_for_status()
    except requests.RequestException as exc:
        return {"erro": f"Não foi possível buscar os contatos agora ({exc}).", "contatos": [], "total": 0}
    dados = resposta.json()
    contatos = [
        {"email": contato.get("email", ""), "criado_em": contato.get("createdAt", "")}
        for contato in dados.get("contacts", [])
    ]
    return {"contatos": contatos, "total": dados.get("count", len(contatos))}


def _corpo_html_codigo_verificacao(codigo: str) -> str:
    return (
        f"<p>Use o código abaixo pra entrar em <strong>Meus Pedidos</strong> no site da "
        f"Nove de Julho:</p>"
        f'<p style="font-size:28px;font-weight:bold;letter-spacing:4px;color:#14335c;">{_esc(codigo)}</p>'
        f"<p>Válido por 10 minutos. Se você não pediu esse código, pode ignorar este e-mail.</p>"
    )


def enviar_codigo_verificacao(email_cliente: str, codigo: str) -> dict:
    """Codigo de login de /meus-pedidos (ver app.py e
    services/pedidos.py:gerar_codigo_verificacao_documento). Sem nome do
    cliente aqui de proposito -- quem chama so tem o e-mail associado ao
    documento, nao um pedido inteiro."""
    return _enviar(
        email_cliente=email_cliente,
        nome_cliente="",
        assunto="Seu código de acesso — Nove de Julho",
        corpo_html=_corpo_html_codigo_verificacao(codigo),
        tag="codigo_verificacao",
    )


def enviar_confirmacao_pedido(pedido: dict, url_pedido: str) -> dict:
    """Disparado quando o webhook confirma o pagamento. Devolve
    {"ok": True} ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=f"Pagamento confirmado — Pedido #{pedido['codigo']}",
        corpo_html=_corpo_html_confirmacao(pedido, url_pedido),
        tag="confirmacao_pedido",
    )


def enviar_link_pagamento(pedido: dict, url_pagamento: str, url_acompanhamento: str) -> dict:
    """Disparado assim que o pedido e´ criado (ainda pendente) -- pro
    cliente ter o link mesmo se fechar a aba antes de terminar de
    pagar. Devolve {"ok": True} ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=f"Finalize seu pagamento — Pedido #{pedido['codigo']}",
        corpo_html=_corpo_html_link_pagamento(pedido, url_pagamento, url_acompanhamento),
        tag="link_pagamento",
    )


def _corpo_html_lembrete(pedido: dict, url_pagamento: str, url_acompanhamento: str) -> str:
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Notamos que seu pedido ainda não foi pago.</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"{_itens_html(pedido)}"
        f"<p><strong>Total: {_preco(pedido['total'])}</strong></p>"
        f"{_botao(_com_utm(url_pagamento, 'lembrete_pedido_pendente'), '💳 Pagar agora (Pix ou cartão)')}"
        f"<p>Alguma dúvida ou dificuldade pra pagar? É só chamar no WhatsApp que a gente ajuda.</p>"
        f"<p>Acompanhe seu pedido por aqui:</p>"
        f"{_botao(_com_utm(url_acompanhamento, 'lembrete_pedido_pendente'), '🔎 Clique aqui e acompanhe')}"
    )


def enviar_lembrete_pedido_pendente(pedido: dict, url_pagamento: str, url_acompanhamento: str) -> dict:
    """Disparado pelo job agendado (ver app.py) quando um pedido fica
    pendente por tempo demais sem pagar -- manda um novo link (o
    original pode ter expirado). Devolve {"ok": True} ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=f"Seu pedido ainda não foi pago — Pedido #{pedido['codigo']}",
        corpo_html=_corpo_html_lembrete(pedido, url_pagamento, url_acompanhamento),
        tag="lembrete_pedido_pendente",
    )


def _corpo_html_lembrete_precoce(pedido: dict, url_pagamento: str, url_acompanhamento: str) -> str:
    # Tom mais suave/de ajuda (nao de cobranca) que _corpo_html_lembrete
    # acima -- pedido do usuario 2026-09-24, pro 1o toque (6h, ainda
    # "morno"). Sem "ainda nao foi pago"/prazo -- so um "ficou alguma
    # duvida?" com o link a mao, caso a pessoa queira retomar.
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Vimos que você começou um pedido "
        f"com a gente e ainda não finalizou.</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"{_itens_html(pedido)}"
        f"<p><strong>Total: {_preco(pedido['total'])}</strong></p>"
        f"<p>Ficou alguma dúvida sobre as peças, o prazo ou o pagamento? A gente fica à "
        f"disposição no WhatsApp pra ajudar com o que precisar.</p>"
        f"{_botao(_com_utm(url_pagamento, 'lembrete_pedido_pendente_precoce'), '💳 Continuar meu pedido')}"
        f"<p>Se preferir, acompanhe por aqui:</p>"
        f"{_botao(_com_utm(url_acompanhamento, 'lembrete_pedido_pendente_precoce'), '🔎 Clique aqui e acompanhe')}"
    )


def enviar_lembrete_precoce_pedido_pendente(pedido: dict, url_pagamento: str, url_acompanhamento: str) -> dict:
    """Mesma logica de enviar_lembrete_pedido_pendente, so que com tom
    mais suave (ver _corpo_html_lembrete_precoce acima) -- usado no 1o
    toque, 6h depois de criado (ver app.py:
    _enviar_lembretes_precoces_pedidos_pendentes)."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=f"Ficou alguma dúvida no seu pedido? — Pedido #{pedido['codigo']}",
        corpo_html=_corpo_html_lembrete_precoce(pedido, url_pagamento, url_acompanhamento),
        tag="lembrete_pedido_pendente_precoce",
    )


def _itens_carrinho_abandonado_html(itens: list[dict]) -> str:
    # Formato CRU do carrinho do navegador (ver static/js/carrinho.js),
    # diferente do formato de um pedido ja´ persistido (_itens_html
    # acima) -- mesmo fallback de nome ja usado no rastreamento GA4
    # de add_to_cart, pra peca personalizada sem nome de produto. Mesma
    # miniatura de imagem de _itens_html (os campos imagem/imagemRecorte/
    # imagemLado1 sao os mesmos nos dois formatos).
    return _tabela_itens_html(
        [
            _linha_item_html(
                f"{_esc(item.get('produtoNome') or 'Medalha personalizada')} — {item.get('quantidade', 0)}x",
                _imagem_do_item(item),
            )
            for item in itens
        ]
    )


def _aviso_abaixo_do_minimo_html(subtotal: float) -> str:
    """Aviso extra (ver conversa) quando o carrinho abandonado nem
    chega no pedido minimo do site (services.pricing.pedido_minimo_reais)
    -- sem isso a pessoa podia voltar, clicar no botao, e so descobrir
    no checkout que falta completar o pedido. Vazio quando ja atinge o
    minimo (a maioria dos carrinhos)."""
    minimo = pedido_minimo_reais()
    falta = round(minimo - subtotal, 2)
    if falta <= 0:
        return ""
    return (
        f"<p>⚠️ Seu carrinho está em {_preco(subtotal)} -- o pedido mínimo do site é "
        f"{_preco(minimo)}. Falta só {_preco(falta)} em produtos pra conseguir finalizar.</p>"
    )


def _corpo_html_carrinho_abandonado(carrinho: dict, url_carrinho: str) -> str:
    subtotal = carrinho.get("subtotal", 0) or 0
    return (
        f"<p>Olá, {_esc(carrinho.get('nome', ''))}! Vimos que você separou algumas peças "
        f"mas não chegou a finalizar o pedido.</p>"
        f"{_itens_carrinho_abandonado_html(carrinho.get('itens', []))}"
        f"{_aviso_abaixo_do_minimo_html(subtotal)}"
        f"<p>Ficou alguma dúvida no meio do caminho? Seu carrinho continua salvo, é só continuar "
        f"de onde parou:</p>"
        f"{_botao(_com_utm(url_carrinho, 'lembrete_carrinho_abandonado'), '🛒 Continuar meu pedido')}"
        f"<p>Se preferir, também é só chamar no WhatsApp que a gente ajuda a fechar.</p>"
    )


def enviar_lembrete_carrinho_abandonado(carrinho: dict, url_carrinho: str) -> dict:
    """Disparado pelo job agendado (ver app.py) pra quem preencheu nome
    + e-mail no carrinho mas nunca chegou a criar um pedido de verdade
    -- ver services/carrinhos_abandonados.py. Devolve {"ok": True} ou
    {"erro": "..."}."""
    return _enviar(
        email_cliente=carrinho.get("email", ""),
        nome_cliente=carrinho.get("nome", ""),
        assunto="Você deixou algo no carrinho 🛒",
        corpo_html=_corpo_html_carrinho_abandonado(carrinho, url_carrinho),
        tag="lembrete_carrinho_abandonado",
    )


def _corpo_html_pedido_enviado(
    pedido: dict, codigo_rastreio: str, link_rastreio: str, url_acompanhamento: str, transportadora: str = ""
) -> str:
    # "Enviado" nao faz sentido pra quem vai retirar no local (mesmo
    # criterio de app.py:FRETE_RETIRADA_DESCRICAO/_mensagem_whatsapp_cliente)
    # -- manda um e-mail proprio avisando que ja´ esta´ pronto, com um
    # botao de WhatsApp com a mensagem pronta pra combinar o horario.
    if pedido.get("frete_descricao") == "Retirada no local":
        mensagem_whatsapp = (
            f"Oi! Meu pedido #{pedido['codigo']} está pronto pra retirada e eu gostaria de "
            f"combinar o horário."
        )
        return (
            f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Seu pedido já está pronto pra "
            f"retirada. 🏬</p>"
            f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
            f"{_itens_html(pedido)}"
            f"<p>Chama a gente no WhatsApp pra combinar o melhor horário:</p>"
            f"{_botao_whatsapp(mensagem_whatsapp, '💬 Combinar retirada pelo WhatsApp')}"
            f"<p>Ou acompanhe os detalhes do pedido a qualquer momento:</p>"
            f"{_botao(_com_utm(url_acompanhamento, 'pedido_enviado'), '🔎 Ver detalhes do pedido')}"
        )

    rastreio_html = (
        f'<p>Código de rastreio: <strong>{_esc(codigo_rastreio)}</strong><br>'
        f'<a href="{_esc(link_rastreio)}">{_esc(link_rastreio)}</a></p>'
        if link_rastreio
        else f"<p>Código de rastreio: <strong>{_esc(codigo_rastreio)}</strong></p>"
    )
    transportadora_html = f"<p>Transportadora: <strong>{_esc(transportadora)}</strong></p>" if transportadora else ""
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Seu pedido foi enviado. 📦</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"{_itens_html(pedido)}"
        f"{transportadora_html}"
        f"{rastreio_html}"
        f"<p>Acompanhe seu pedido a qualquer momento:</p>"
        f"{_botao(_com_utm(url_acompanhamento, 'pedido_enviado'), '🔎 Clique aqui e acompanhe')}"
        f"<p>Qualquer dúvida, é só chamar no WhatsApp.</p>"
    )


def enviar_pedido_enviado(
    pedido: dict, codigo_rastreio: str, link_rastreio: str, url_acompanhamento: str, transportadora: str = ""
) -> dict:
    """Disparado quando o pedido passa pro status "enviado" -- hoje via
    painel admin (ver app.py:admin_pedido_status), no futuro tambem
    podera´ vir de um webhook da Tiny (ver services.pedidos.atualizar_status).
    Devolve {"ok": True} ou {"erro": "..."}."""
    assunto = (
        f"Pedido pronto para retirada — Pedido #{pedido['codigo']}"
        if pedido.get("frete_descricao") == "Retirada no local"
        else f"Pedido enviado — Pedido #{pedido['codigo']}"
    )
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=assunto,
        corpo_html=_corpo_html_pedido_enviado(
            pedido, codigo_rastreio, link_rastreio, url_acompanhamento, transportadora
        ),
        tag="pedido_enviado",
    )


def _corpo_html_nota_fiscal_disponivel(pedido: dict, url_acompanhamento: str) -> str:
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! A nota fiscal do seu pedido já está "
        f"disponível. 🧾</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"{_botao(pedido.get('link_nota_fiscal', ''), '🧾 Baixar nota fiscal')}"
        f"<p>Acompanhe seu pedido a qualquer momento:</p>"
        f"{_botao(_com_utm(url_acompanhamento, 'nota_fiscal_disponivel'), '🔎 Clique aqui e acompanhe')}"
        f"<p>Qualquer dúvida, é só chamar no WhatsApp.</p>"
    )


def enviar_nota_fiscal_disponivel(pedido: dict, url_acompanhamento: str) -> dict:
    """Disparado quando o link da nota fiscal e´ preenchido pela primeira
    vez (ver app.py:admin_pedido_status) -- hoje sempre manual (admin
    cola o link), no futuro tambem podera´ vir sozinho do webhook da
    Tiny quando a nota for autorizada (ver
    app.py:webhook_tiny_captura, ainda descobrindo o formato real).
    Devolve {"ok": True} ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=f"Nota fiscal disponível — Pedido #{pedido['codigo']}",
        corpo_html=_corpo_html_nota_fiscal_disponivel(pedido, url_acompanhamento),
        tag="nota_fiscal_disponivel",
    )


def _corpo_html_pedido_cancelado(pedido: dict, url_reativar_pix: str, url_reativar_boleto: str) -> str:
    mensagem_whatsapp = quote(
        f"Oi! Meu pedido #{pedido['codigo']} foi cancelado, mas quero fechar mesmo assim. Pode me ajudar?"
    )
    url_whatsapp = f"https://wa.me/{WHATSAPP_NUMBER}?text={mensagem_whatsapp}"
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Seu pedido #{pedido['codigo']} não foi pago a "
        f"tempo e acabou sendo cancelado automaticamente.</p>"
        f"<p>Mas as medalhas continuam esperando por você -- e o pedido continua montado do jeitinho que "
        f"você deixou (mesmas peças, mesma foto personalizada se tiver enviado uma). Escolha como prefere "
        f"fechar, sem precisar refazer nada:</p>"
        f"{_botao(_com_utm(url_reativar_pix, 'pedido_cancelado'), '💳 Pagar com Pix ou cartão')}"
        f"{_botao(_com_utm(url_reativar_boleto, 'pedido_cancelado'), '🧾 Gerar boleto')}"
        f"{_botao(url_whatsapp, '💬 Fechar pelo WhatsApp')}"
        f"<p>Qualquer dúvida, é só chamar. Deus abençoe! 🙏</p>"
    )


def _corpo_html_oportunidade_upsell(pedido: dict, quantidade_entremeios: int) -> str:
    mensagem_whatsapp = (
        f"Oi! Vi que dá pra completar meu pedido #{pedido['codigo']} com cruzes pro terço "
        f"antes de enviar. Queria fazer esse pedido extra."
    )
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Vimos que seu pedido #{pedido['codigo']} tem "
        f"{quantidade_entremeios} entremeios, mas nenhuma cruz pra completar o terço. 📿</p>"
        f"<p>Como a cruz já é peça pronta (sem produção), ainda dá tempo de somar ao seu pedido, que "
        f"continua em produção -- sem atrasar nada.</p>"
        f"<p>É só fazer um pedido novo só com as cruzes (a partir de R$ 2,50 cada) e escolher "
        f"<strong>retirada no local</strong> -- a gente junta tudo antes de enviar pra você.</p>"
        f"{_botao_whatsapp(mensagem_whatsapp, '💬 Combinar pelo WhatsApp')}"
        f"<p>Se preferir não, sem problema -- seu pedido segue normal do jeitinho que está.</p>"
    )


def enviar_oportunidade_upsell(pedido: dict, quantidade_entremeios: int) -> dict:
    """Disparado pelo job agendado (ver app.py) UPSELL_HORAS_APOS_
    PAGAMENTO horas depois do pagamento confirmado -- so pra quem
    comprou pelo menos UPSELL_ENTREMEIOS_MINIMO entremeios e NENHUMA
    cruz no mesmo pedido (ver app.py:_pedido_elegivel_upsell_cruz e
    conversa "upsell de cruz durante producao"). Cruz e´ peca pronta
    (sem producao propria), da´ pra somar ao pedido AINDA em producao --
    diferente do upsell generico antigo (empurrava pro PROXIMO pedido,
    sem aproveitar essa janela). Devolve {"ok": True} ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto="Falta só a cruz pro seu terço — Nove de Julho",
        corpo_html=_corpo_html_oportunidade_upsell(pedido, quantidade_entremeios),
        tag="oportunidade_upsell",
    )


def _corpo_html_pedido_avaliacao(pedido: dict, url_avaliar: str) -> str:
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Esperamos que as peças do seu pedido "
        f"#{pedido['codigo']} estejam alegrando o dia a dia de quem recebeu. 🙏</p>"
        f"<p>Poderia contar pra gente como foi sua experiência? Leva menos de 1 minuto -- escolha o "
        f"produto, dê uma nota de 1 a 5 estrelas, e deixe uma foto (se quiser) e um comentário "
        f"(opcional).</p>"
        f"{_botao(_com_utm(url_avaliar, 'pedido_avaliacao'), '👉 Avaliar minha compra')}"
        f"<p>Sua avaliação ajuda outras pessoas a comprar com mais confiança. Muito obrigado!</p>"
        f"<p>E se tiver uma foto da peça, adoraríamos ver -- poste no Instagram marcando "
        f"<strong>@novedjulho</strong>! 📸</p>"
        f"{_botao(INSTAGRAM_URL, '📷 Ver/seguir @novedjulho no Instagram')}"
    )


def enviar_pedido_avaliacao(pedido: dict, url_avaliar: str) -> dict:
    """Pede avaliacao da compra, linkando pra pagina geral de avaliacao
    (/avaliar, ver app.py:avaliar_geral) -- o cliente escolhe o produto
    na hora, em vez de a gente adivinhar qual dos itens do pedido
    avaliar. Convida tambem a marcar @novedjulho no Instagram.
    Disparado NA HORA que o pedido vira "entregue" (ver
    app.py:admin_pedido_status), e de novo
    AVALIACAO_SEGUIMENTO_DIAS_APOS_ENTREGA dias depois pra quem ainda
    nao avaliou (ver app.py:_enviar_seguimento_avaliacao_entregues) --
    so esses 2 e-mails de avaliacao no total por pedido. Devolve
    {"ok": True} ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto="O que você achou da sua compra?",
        corpo_html=_corpo_html_pedido_avaliacao(pedido, url_avaliar),
        tag="pedido_avaliacao",
    )


_RECOMPRA_TEXTO_POR_ESTAGIO = {
    30: "Já faz um mês que seu pedido chegou -- ",
    60: "Já faz dois meses que seu pedido chegou -- ",
    90: "Já faz três meses que seu pedido chegou -- ",
}


def _corpo_html_pedido_recompra(pedido: dict, dias: int, url_repetir_ou_catalogo: str, tem_repetir: bool) -> str:
    intro = _RECOMPRA_TEXTO_POR_ESTAGIO.get(dias, "Faz um tempinho que seu pedido chegou -- ")
    if tem_repetir:
        convite = (
            f"que tal fazer um pedido novo? Preparamos um atalho: clique abaixo e o MESMO pedido "
            f"(mesmos santos, formatos e quantidades) já entra pronto no seu carrinho, sem precisar "
            f"escolher tudo de novo."
        )
        texto_botao = "🔁 Repetir meu pedido"
    else:
        convite = "que tal dar uma olhada no catálogo e fazer um pedido novo?"
        texto_botao = "👉 Ver o catálogo completo"
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! {intro}{convite}</p>"
        f"{_botao(_com_utm(url_repetir_ou_catalogo, 'pedido_recompra'), texto_botao)}"
        f"<p>Qualquer dúvida ou pedido especial, é só chamar no WhatsApp.</p>"
    )


def enviar_pedido_recompra(pedido: dict, dias: int, url_repetir_ou_catalogo: str, *, tem_repetir: bool) -> dict:
    """Convite pra um pedido novo, disparado 30/60/90 dias depois da
    ENTREGA (ver app.py:_enviar_emails_recompra_entregues) -- os 3
    estagios sao independentes (quem nao abriu o de 30 dias ainda
    recebe o de 60). Quando o pedido tem pelo menos 1 item "repetivel"
    (santo do catalogo com produtoId, ver app.py:
    _itens_repetiveis_do_pedido), o botao leva direto pro carrinho ja´
    preenchido com o MESMO pedido (`tem_repetir=True`); senao (pedido
    so´ de peca personalizada) leva pro catalogo geral. Devolve
    {"ok": True} ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto="Bora fazer um novo pedido? — Nove de Julho",
        corpo_html=_corpo_html_pedido_recompra(pedido, dias, url_repetir_ou_catalogo, tem_repetir),
        tag="pedido_recompra",
    )


def enviar_pedido_cancelado(pedido: dict, url_reativar_pix: str, url_reativar_boleto: str) -> dict:
    """Disparado pelo job agendado (ver app.py) quando um pedido "pendente"
    e´ cancelado automaticamente por falta de pagamento apos o lembrete
    -- e-mail de recuperacao com 3 jeitos de reaproveitar o MESMO
    pedido (mesmos itens, foto personalizada se tiver) sem precisar
    refazer nada: Pix/cartao, boleto (ver app.py:pedido_reativar_pix/
    pedido_reativar_boleto) ou fechar pelo WhatsApp. Devolve {"ok": True}
    ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=f"Seu pedido #{pedido['codigo']} foi cancelado -- mas ainda dá tempo",
        corpo_html=_corpo_html_pedido_cancelado(pedido, url_reativar_pix, url_reativar_boleto),
        tag="pedido_cancelado",
    )


def _corpo_html_pedido_excluido(pedido: dict, motivo: str, url_catalogo: str) -> str:
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Precisamos te avisar que seu pedido "
        f"#{pedido['codigo']} foi cancelado pela nossa equipe.</p>"
        f"<p><strong>Motivo:</strong> {_esc(motivo)}</p>"
        f"<p>Se você já tinha pago e ainda não recebeu o reembolso, ou tiver qualquer dúvida "
        f"sobre isso, é só chamar no WhatsApp que a gente resolve.</p>"
        f"{_botao(_com_utm(url_catalogo, 'pedido_excluido'), '👉 Ver o catálogo e fazer um novo pedido')}"
    )


def enviar_pedido_excluido(pedido: dict, motivo: str, url_catalogo: str) -> dict:
    """Disparado quando o admin exclui um pedido pelo painel (ver
    app.py:admin_pedido_excluir) -- explica o motivo pro cliente, ja
    que a exclusao e´ uma decisao manual (nao automatica como o
    cancelamento por falta de pagamento, ver enviar_pedido_cancelado
    acima). Devolve {"ok": True} ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=f"Seu pedido #{pedido['codigo']} foi cancelado",
        corpo_html=_corpo_html_pedido_excluido(pedido, motivo, url_catalogo),
        tag="pedido_excluido",
    )


def _corpo_html_notificacao_venda(pedido: dict, url_admin: str) -> str:
    return (
        f"<p>🎉 Nova venda confirmada!</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong> -- {_preco(pedido['total'])} "
        f"({pedido.get('forma_pagamento', '')})</p>"
        f"<p>Cliente: {_esc(pedido.get('cliente_nome', ''))} -- {_esc(pedido.get('cliente_telefone', ''))}</p>"
        f"{_itens_html(pedido)}"
        f"{_botao(url_admin, '👉 Ver pedido no painel')}"
    )


def enviar_notificacao_venda(pedido: dict, url_admin: str) -> dict:
    """Aviso interno pra loja quando uma venda e´ confirmada (ver
    app.py:webhook_infinitepay) -- vai pra EMAIL_NOTIFICACAO_VENDA
    (config.py), nao pro cliente. Nunca deve derrubar o webhook: quem
    chama isso ja´ trata qualquer excecao/erro como nao-critico.
    Devolve {"ok": True} ou {"erro": "..."}."""
    if not EMAIL_NOTIFICACAO_VENDA:
        return {"erro": "Notificação de venda não configurada (falta EMAIL_NOTIFICACAO_VENDA)."}
    return _enviar(
        email_cliente=EMAIL_NOTIFICACAO_VENDA,
        nome_cliente="",
        assunto=f"🎉 Nova venda — Pedido #{pedido['codigo']} ({_preco(pedido['total'])})",
        corpo_html=_corpo_html_notificacao_venda(pedido, url_admin),
        tag="notificacao_venda",
    )
