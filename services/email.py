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

import requests

from config import BREVO_API_KEY, EMAIL_REMETENTE, EMAIL_REMETENTE_NOME

API_URL = "https://api.brevo.com/v3/smtp/email"


def _preco(valor: float) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


def _itens_html(pedido: dict) -> str:
    return "".join(
        f"<li>{item.get('descricao') or item.get('chave_preco', '')} — {item['quantidade']}x</li>"
        for item in pedido["itens"]
    )


def _corpo_html_confirmacao(pedido: dict, url_pedido: str) -> str:
    return (
        f"<p>Olá, {pedido.get('cliente_nome', '')}! Recebemos seu pagamento. 🎉</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"<ul>{_itens_html(pedido)}</ul>"
        f"<p>Frete ({pedido.get('frete_descricao', '')}): {_preco(pedido.get('frete_preco', 0))}</p>"
        f"<p><strong>Total: {_preco(pedido['total'])}</strong></p>"
        f"<p>🛠️ Seu pedido já está em produção -- prazo de até <strong>5 dias úteis</strong> antes do envio.</p>"
        f"<p>Acompanhe seu pedido a qualquer momento por este link:<br>"
        f'<a href="{url_pedido}">{url_pedido}</a></p>'
        f"<p>Qualquer dúvida, é só chamar no WhatsApp.</p>"
    )


def _corpo_html_link_pagamento(pedido: dict, url_pagamento: str, url_acompanhamento: str) -> str:
    return (
        f"<p>Olá, {pedido.get('cliente_nome', '')}! Recebemos seu pedido, falta só o pagamento pra confirmar.</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"<ul>{_itens_html(pedido)}</ul>"
        f"<p>Frete ({pedido.get('frete_descricao', '')}): {_preco(pedido.get('frete_preco', 0))}</p>"
        f"<p><strong>Total: {_preco(pedido['total'])}</strong></p>"
        f'<p><a href="{url_pagamento}">👉 Clique aqui pra pagar (Pix ou cartão)</a></p>'
        f"<p>Se esse link não abrir mais (expirou), é só acompanhar seu pedido "
        f"por aqui e gerar um novo:<br>"
        f'<a href="{url_acompanhamento}">{url_acompanhamento}</a></p>'
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
        f"<p>Olá, {pedido.get('cliente_nome', '')}! Notamos que seu pedido ainda não foi pago.</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"<ul>{_itens_html(pedido)}</ul>"
        f"<p><strong>Total: {_preco(pedido['total'])}</strong></p>"
        f'<p><a href="{url_pagamento}">👉 Clique aqui pra pagar (Pix ou cartão)</a></p>'
        f"<p>Alguma dúvida ou dificuldade pra pagar? É só chamar no WhatsApp que a gente ajuda.</p>"
        f"<p>Acompanhe seu pedido por aqui:<br>"
        f'<a href="{url_acompanhamento}">{url_acompanhamento}</a></p>'
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
