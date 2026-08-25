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


def _corpo_html(pedido: dict, url_pedido: str) -> str:
    itens_html = "".join(
        f"<li>{item.get('descricao') or item.get('chave_preco', '')} — {item['quantidade']}x</li>"
        for item in pedido["itens"]
    )
    return (
        f"<p>Olá, {pedido.get('cliente_nome', '')}! Recebemos seu pagamento. 🎉</p>"
        f"<p><strong>Pedido #{pedido['codigo']}</strong></p>"
        f"<ul>{itens_html}</ul>"
        f"<p>Frete ({pedido.get('frete_descricao', '')}): {_preco(pedido.get('frete_preco', 0))}</p>"
        f"<p><strong>Total: {_preco(pedido['total'])}</strong></p>"
        f"<p>Acompanhe seu pedido a qualquer momento por este link:<br>"
        f'<a href="{url_pedido}">{url_pedido}</a></p>'
        f"<p>Qualquer dúvida, é só chamar no WhatsApp.</p>"
    )


def enviar_confirmacao_pedido(pedido: dict, url_pedido: str) -> dict:
    """Devolve {"ok": True} ou {"erro": "..."}."""
    if not BREVO_API_KEY:
        return {"erro": "Envio de e-mail não configurado (falta BREVO_API_KEY)."}
    email_cliente = pedido.get("cliente_email")
    if not email_cliente:
        return {"erro": "Pedido sem e-mail do cliente."}

    payload = {
        "sender": {"name": EMAIL_REMETENTE_NOME, "email": EMAIL_REMETENTE},
        "to": [{"email": email_cliente, "name": pedido.get("cliente_nome", "")}],
        "subject": f"Pagamento confirmado — Pedido #{pedido['codigo']}",
        "htmlContent": _corpo_html(pedido, url_pedido),
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
