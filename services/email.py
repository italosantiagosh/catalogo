"""
E-mail transacional via Brevo (ex-Sendinblue) -- ver
app.py:webhook_infinitepay, disparado uma unica vez por pedido quando
o pagamento e´ confirmado (services.pedidos.marcar_email_enviado evita
reenvio em webhook duplicado).

O site nao tem login de cliente (ver conversa que definiu essa
escolha) -- o link de acompanhamento do pedido (/pedido/<token>) so
chega pro cliente no redirecionamento pos-pagamento. Sem esse e-mail,
se ele fechar a aba ou perder o link, nao tem como achar o pedido de
novo sozinho.

API da Brevo: https://developers.brevo.com/docs/send-a-transactional-email
"""

from __future__ import annotations

import html

import requests

from config import BREVO_API_KEY, EMAIL_NOTIFICACAO_VENDA, EMAIL_REMETENTE, EMAIL_REMETENTE_NOME
from services.pedidos import previsoes_do_pedido

API_URL = "https://api.brevo.com/v3/smtp/email"

# Todo campo que vem do que o cliente digitou no checkout (nome,
# telefone, descricao/frete escolhidos) ou que o admin digita no painel
# (motivo de exclusao, rastreio) passa por aqui antes de entrar num
# f-string de HTML de e-mail -- sem isso, dava pra injetar HTML no
# proprio e-mail de confirmacao do cliente OU no aviso interno de nova
# venda que o dono le (ver conversa "tornar o site e apis seguros").
_esc = html.escape


def _preco(valor: float) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


def _itens_html(pedido: dict) -> str:
    return "".join(
        f"<li>{_esc(item.get('descricao') or item.get('chave_preco', ''))} — {item['quantidade']}x</li>"
        for item in pedido["itens"]
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
        previsao_html = "<p>🛠️ Seu pedido já está em produção -- prazo de até <strong>5 dias úteis</strong> antes do envio.</p>"
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Recebemos seu pagamento. 🎉</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"<ul>{_itens_html(pedido)}</ul>"
        f"<p>Frete ({_esc(pedido.get('frete_descricao', ''))}): {_preco(pedido.get('frete_preco', 0))}</p>"
        f"<p><strong>Total: {_preco(pedido['total'])}</strong></p>"
        f"{previsao_html}"
        f"<p>Acompanhe seu pedido a qualquer momento:</p>"
        f"{_botao(url_pedido, '🔎 Clique aqui e acompanhe')}"
        f"<p>Qualquer dúvida, é só chamar no WhatsApp.</p>"
    )


def _corpo_html_link_pagamento(pedido: dict, url_pagamento: str, url_acompanhamento: str) -> str:
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Recebemos seu pedido, falta só o pagamento pra confirmar.</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"<ul>{_itens_html(pedido)}</ul>"
        f"<p>Frete ({_esc(pedido.get('frete_descricao', ''))}): {_preco(pedido.get('frete_preco', 0))}</p>"
        f"<p><strong>Total: {_preco(pedido['total'])}</strong></p>"
        f"{_botao(url_pagamento, '💳 Pagar agora (Pix ou cartão)')}"
        f"<p>Se esse link não abrir mais (expirou), é só acompanhar seu pedido "
        f"por aqui e gerar um novo:</p>"
        f"{_botao(url_acompanhamento, '🔎 Clique aqui e acompanhe')}"
        f"<p>Qualquer dúvida, é só chamar no WhatsApp.</p>"
    )


def _enviar(*, email_cliente: str, nome_cliente: str, assunto: str, corpo_html: str) -> dict:
    if not BREVO_API_KEY:
        return {"erro": "Envio de e-mail não configurado (falta BREVO_API_KEY)."}
    if not email_cliente:
        return {"erro": "Pedido sem e-mail do cliente."}

    payload = {
        "sender": {"name": EMAIL_REMETENTE_NOME, "email": EMAIL_REMETENTE},
        "to": [{"email": email_cliente, "name": nome_cliente}],
        "subject": assunto,
        "htmlContent": corpo_html,
    }
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


def enviar_confirmacao_pedido(pedido: dict, url_pedido: str) -> dict:
    """Disparado quando o webhook confirma o pagamento. Devolve
    {"ok": True} ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=f"Pagamento confirmado — Pedido #{pedido['codigo']}",
        corpo_html=_corpo_html_confirmacao(pedido, url_pedido),
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
    )


def _corpo_html_lembrete(pedido: dict, url_pagamento: str, url_acompanhamento: str) -> str:
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Notamos que seu pedido ainda não foi pago.</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"<ul>{_itens_html(pedido)}</ul>"
        f"<p><strong>Total: {_preco(pedido['total'])}</strong></p>"
        f"{_botao(url_pagamento, '💳 Pagar agora (Pix ou cartão)')}"
        f"<p>Alguma dúvida ou dificuldade pra pagar? É só chamar no WhatsApp que a gente ajuda.</p>"
        f"<p>Acompanhe seu pedido por aqui:</p>"
        f"{_botao(url_acompanhamento, '🔎 Clique aqui e acompanhe')}"
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
    )


def _corpo_html_pedido_enviado(
    pedido: dict, codigo_rastreio: str, link_rastreio: str, url_acompanhamento: str, transportadora: str = ""
) -> str:
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
        f"<ul>{_itens_html(pedido)}</ul>"
        f"{transportadora_html}"
        f"{rastreio_html}"
        f"<p>Acompanhe seu pedido a qualquer momento:</p>"
        f"{_botao(url_acompanhamento, '🔎 Clique aqui e acompanhe')}"
        f"<p>Qualquer dúvida, é só chamar no WhatsApp.</p>"
    )


def enviar_pedido_enviado(
    pedido: dict, codigo_rastreio: str, link_rastreio: str, url_acompanhamento: str, transportadora: str = ""
) -> dict:
    """Disparado quando o pedido passa pro status "enviado" -- hoje via
    painel admin (ver app.py:admin_pedido_status), no futuro tambem
    podera´ vir de um webhook da Tiny (ver services.pedidos.atualizar_status).
    Devolve {"ok": True} ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=f"Pedido enviado — Pedido #{pedido['codigo']}",
        corpo_html=_corpo_html_pedido_enviado(
            pedido, codigo_rastreio, link_rastreio, url_acompanhamento, transportadora
        ),
    )


def _corpo_html_pedido_cancelado(pedido: dict, url_catalogo: str) -> str:
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Seu pedido #{pedido['codigo']} não foi pago a "
        f"tempo e acabou sendo cancelado automaticamente.</p>"
        f"<p>Mas as medalhas continuam esperando por você -- e cada uma carrega uma história de fé "
        f"que vale a pena levar adiante. 🙏</p>"
        f"{_botao(url_catalogo, '👉 Voltar ao catálogo e fazer um novo pedido')}"
        f"<p>Se o pagamento deu algum problema ou você tiver qualquer dúvida, é só chamar no "
        f"WhatsApp -- a gente ajuda a resolver.</p>"
    )


def _corpo_html_oportunidade_upsell(pedido: dict, oportunidades: list[dict], url_catalogo: str) -> str:
    linhas_oportunidade = "".join(
        f"<li>Em <strong>{o['label']}</strong>: peça mais <strong>{o['faltam']}</strong> peças no seu "
        f"próximo pedido e o preço cai pra <strong>{_preco(o['preco'])}/un</strong>"
        + (f" — economia de até <strong>{_preco(o['economia'])}</strong>!" if o["economia"] > 0 else "!")
        + "</li>"
        for o in oportunidades
    )
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Esperamos que esteja aproveitando as peças do "
        f"pedido #{pedido['codigo']}.</p>"
        f"<p>Separamos uma oportunidade pro seu próximo pedido:</p>"
        f"<ul>{linhas_oportunidade}</ul>"
        f"{_botao(url_catalogo, '👉 Ver o catálogo completo')}"
        f"<p>Qualquer dúvida, é só chamar no WhatsApp.</p>"
    )


def enviar_oportunidade_upsell(pedido: dict, oportunidades: list[dict], url_catalogo: str) -> dict:
    """Disparado pelo job agendado (ver app.py) algumas horas depois do
    pagamento confirmado -- empurrao pra proxima faixa de desconto de
    atacado no PROXIMO pedido. `oportunidades` vem de
    app.py:_oportunidades_upsell_do_pedido (lista de
    {"label", "faltam", "preco", "economia"}, uma por grupo de atacado
    com item nesse pedido). So chamado quando ja´ existe pelo menos 1
    oportunidade real -- nunca com lista vazia. Devolve {"ok": True} ou
    {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto="Uma oportunidade pro seu próximo pedido — Nove de Julho",
        corpo_html=_corpo_html_oportunidade_upsell(pedido, oportunidades, url_catalogo),
    )


def _corpo_html_pedido_avaliacao(pedido: dict, produto_nome: str, url_produto: str) -> str:
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Já faz um tempinho desde o seu pedido "
        f"#{pedido['codigo']} -- esperamos que as peças estejam alegrando o dia a dia de quem "
        f"recebeu. 🙏</p>"
        f"<p>Poderia contar pra gente como foi sua experiência com a <strong>{produto_nome}</strong>? "
        f"Leva menos de 1 minuto -- nome, uma nota de 1 a 5 estrelas, uma foto (se quiser) e um "
        f"comentário (opcional).</p>"
        f"{_botao(url_produto, f'👉 Avaliar {produto_nome}')}"
        f"<p>Sua avaliação ajuda outras pessoas a comprar com mais confiança. Muito obrigado!</p>"
    )


def enviar_pedido_avaliacao(pedido: dict, produto_nome: str, url_produto: str) -> dict:
    """Disparado pelo job agendado (ver app.py) AVALIACAO_DIAS_APOS_PAGAMENTO
    dias depois do pagamento confirmado -- pede avaliacao de um dos
    produtos do pedido (ver app.py:_produto_para_avaliacao_do_pedido),
    linkando direto pra secao de avaliacoes desse produto
    (templates/produto.html#avaliacoes). Devolve {"ok": True} ou
    {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=f"O que você achou da sua {produto_nome}?",
        corpo_html=_corpo_html_pedido_avaliacao(pedido, produto_nome, url_produto),
    )


def enviar_pedido_cancelado(pedido: dict, url_catalogo: str) -> dict:
    """Disparado pelo job agendado (ver app.py) quando um pedido "pendente"
    e´ cancelado automaticamente por falta de pagamento apos o lembrete
    -- e-mail motivacional de recuperacao, linkando de volta pro
    catalogo. Devolve {"ok": True} ou {"erro": "..."}."""
    return _enviar(
        email_cliente=pedido.get("cliente_email", ""),
        nome_cliente=pedido.get("cliente_nome", ""),
        assunto=f"Seu pedido #{pedido['codigo']} foi cancelado -- mas ainda dá tempo",
        corpo_html=_corpo_html_pedido_cancelado(pedido, url_catalogo),
    )


def _corpo_html_pedido_excluido(pedido: dict, motivo: str, url_catalogo: str) -> str:
    return (
        f"<p>Olá, {_esc(pedido.get('cliente_nome', ''))}! Precisamos te avisar que seu pedido "
        f"#{pedido['codigo']} foi cancelado pela nossa equipe.</p>"
        f"<p><strong>Motivo:</strong> {_esc(motivo)}</p>"
        f"<p>Se você já tinha pago e ainda não recebeu o reembolso, ou tiver qualquer dúvida "
        f"sobre isso, é só chamar no WhatsApp que a gente resolve.</p>"
        f"{_botao(url_catalogo, '👉 Ver o catálogo e fazer um novo pedido')}"
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
    )


def _corpo_html_notificacao_venda(pedido: dict, url_admin: str) -> str:
    return (
        f"<p>🎉 Nova venda confirmada!</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong> -- {_preco(pedido['total'])} "
        f"({pedido.get('forma_pagamento', '')})</p>"
        f"<p>Cliente: {_esc(pedido.get('cliente_nome', ''))} -- {_esc(pedido.get('cliente_telefone', ''))}</p>"
        f"<ul>{_itens_html(pedido)}</ul>"
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
    )
