"""
Checkout automatico via InfinitePay -- Pix e cartao (ate 12x) na mesma
API, com Pix a 0% e cartao a vista por volta de 2,12% (bem mais barato
que os ~4,98% de outros gateways, ver conversa que definiu essa
escolha). Gera um link de pagamento hospedado pela InfinitePay -- o
cliente e redirecionado pra pagar e volta pro site depois (redirect_url).

Endpoint e formato do payload conferidos a partir do codigo-fonte de
uma integracao real (plugin WooCommerce open-source), NAO da
documentacao oficial -- o ambiente onde isso foi desenvolvido nao
alcanca infinitepay.io pra testar direto. A primeira chamada de
verdade em producao precisa ser conferida (sobretudo o nome exato do
campo com a URL de pagamento na resposta) antes de confiar cegamente
nesse formato.
"""

from __future__ import annotations

import requests

from config import INFINITEPAY_API_TOKEN, INFINITEPAY_HANDLE

API_URL = "https://api.infinitepay.io/invoices/public/checkout/links"


def criar_link_pagamento(
    *,
    order_nsu: str,
    redirect_url: str,
    webhook_url: str,
    itens_pagamento: list[dict],
    cliente: dict,
    endereco: dict,
) -> dict:
    """`itens_pagamento`: [{"id":..., "description":..., "quantity":..., "price": centavos}, ...]
    (frete ja deve vir incluso como um item separado, ver app.py).
    Devolve {"url": link} ou {"erro": "..."}."""
    if not INFINITEPAY_HANDLE:
        return {"erro": "Pagamento automático não configurado (falta INFINITEPAY_HANDLE)."}

    payload = {
        "handle": INFINITEPAY_HANDLE,
        "order_nsu": order_nsu,
        "redirect_url": redirect_url,
        "webhook_url": webhook_url,
        "items": itens_pagamento,
        "customer": {
            "name": cliente.get("nome", ""),
            "email": cliente.get("email", ""),
            "phone_number": cliente.get("telefone", ""),
            "document": cliente.get("documento", ""),
        },
        "address": {
            "cep": endereco.get("cep", ""),
            "street": endereco.get("logradouro", ""),
            "number": endereco.get("numero", ""),
            "complement": endereco.get("complemento", ""),
            "district": endereco.get("bairro", ""),
            "city": endereco.get("cidade", ""),
            "state": endereco.get("uf", ""),
        },
    }
    headers = {"Content-Type": "application/json"}
    if INFINITEPAY_API_TOKEN:
        headers["Authorization"] = f"Bearer {INFINITEPAY_API_TOKEN}"

    try:
        resposta = requests.post(API_URL, json=payload, headers=headers, timeout=10)
        resposta.raise_for_status()
        dados = resposta.json()
    except requests.RequestException as exc:
        return {"erro": f"Não foi possível gerar o link de pagamento agora ({exc})."}
    except ValueError:
        return {"erro": "Resposta inválida da InfinitePay."}

    url = dados.get("url") or dados.get("payment_url") or dados.get("checkout_url")
    if not url:
        return {"erro": "A InfinitePay não retornou um link de pagamento válido."}
    return {"url": url}
