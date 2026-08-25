"""
Sincronizacao de pedidos pagos com a Tiny/Olist ERP (API 2.0) -- ver
app.py:webhook_infinitepay, chamado uma unica vez por pedido logo
depois que o pagamento e´ confirmado (services.pedidos.marcar_tiny_sincronizado
evita reenviar em webhook duplicado).

Endpoint e layout do parametro `pedido` conferidos no exemplo oficial
da documentacao (colado pelo usuario -- o ambiente onde isso foi
desenvolvido nao alcanca tiny.com.br pra acessar direto). Dois pontos
NAO totalmente confirmados, sinalizados abaixo:
  - os valores aceitos pelo campo `forma_pagamento` (o exemplo oficial
    so mostrava "boleto"/"dinheiro"/"multiplas" -- "pix" e
    "cartao_credito" sao a suposicao mais razoavel, nao confirmada);
  - o significado exato de `frete_por_conta` ("E" assumido como "loja
    contrata o frete", que e´ o caso daqui).
Conferir os dois no primeiro pedido de teste real antes de confiar
cegamente -- se a Tiny rejeitar algum valor, ainda assim preferimos
deixar o pedido salvo no site (ver chamada em app.py) a travar o
webhook por causa disso.
"""

from __future__ import annotations

import json

import requests

from config import TINY_API_TOKEN

API_URL = "https://api.tiny.com.br/api2/pedido.incluir.php"

_TIPO_PESSOA = {"fisica": "F", "juridica": "J"}

# capture_method (InfinitePay) -> forma_pagamento (Tiny) -- ver aviso
# no topo do arquivo sobre essa suposicao nao estar 100% confirmada.
_FORMA_PAGAMENTO = {"pix": "pix", "credit_card": "cartao_credito"}


def _cliente_para_tiny(pedido: dict) -> dict:
    documento = pedido.get("cliente_documento", "")
    return {
        "nome": pedido.get("cliente_nome", ""),
        "tipo_pessoa": _TIPO_PESSOA.get(pedido.get("cliente_tipo_pessoa"), "F"),
        "cpf_cnpj": documento,
        "cpfConsumidorFinal": documento,
        "fone": pedido.get("cliente_telefone", ""),
        "endereco": pedido.get("endereco_logradouro", ""),
        "numero": pedido.get("endereco_numero", ""),
        "complemento": pedido.get("endereco_complemento", ""),
        "bairro": pedido.get("endereco_bairro", ""),
        "cep": pedido.get("endereco_cep", ""),
        "cidade": pedido.get("endereco_cidade", ""),
        "uf": pedido.get("endereco_uf", ""),
    }


def _itens_para_tiny(itens: list[dict]) -> list[dict]:
    return [
        {
            "item": {
                "codigo": item.get("chave_preco", ""),
                "descricao": item.get("descricao") or item.get("chave_preco", ""),
                "unidade": "UN",
                "quantidade": str(item.get("quantidade", 1)),
                "valor_unitario": f"{item.get('valor_unitario', 0):.2f}",
            }
        }
        for item in itens
    ]


def criar_pedido_tiny(pedido: dict) -> dict:
    """`pedido` no formato devolvido por services.pedidos.obter_pedido
    (ja precisa estar com status 'pago'). Devolve {"ok": True, "numero": ...}
    ou {"erro": "..."}."""
    if not TINY_API_TOKEN:
        return {"erro": "Sincronização com a Tiny não configurada (falta TINY_API_TOKEN)."}

    observacoes = [f"Pedido site #{pedido['codigo']}"]
    if pedido.get("endereco_destinatario"):
        observacoes.append(f"Destinatário: {pedido['endereco_destinatario']}")
    if pedido.get("transaction_nsu"):
        observacoes.append(f"Pagamento InfinitePay: {pedido['transaction_nsu']}")

    corpo_pedido = {
        "cliente": _cliente_para_tiny(pedido),
        "itens": _itens_para_tiny(pedido["itens"]),
        "numero_pedido_ecommerce": pedido["codigo"],
        "situacao": "Aberto",
        "obs": " | ".join(observacoes),
        "valor_frete": f"{pedido.get('frete_preco', 0):.2f}",
        "forma_frete": (pedido.get("frete_descricao") or "").split(" — ")[0],
        "frete_por_conta": "E",  # loja contrata o frete -- ver aviso no topo do arquivo
    }
    forma_pagamento = _FORMA_PAGAMENTO.get(pedido.get("forma_pagamento"))
    if forma_pagamento:
        corpo_pedido["forma_pagamento"] = forma_pagamento

    try:
        resposta = requests.post(
            API_URL,
            data={
                "token": TINY_API_TOKEN,
                "formato": "json",
                "pedido": json.dumps({"pedido": corpo_pedido}, ensure_ascii=False),
            },
            timeout=15,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except requests.RequestException as exc:
        return {"erro": f"Não foi possível sincronizar com a Tiny agora ({exc})."}
    except ValueError:
        return {"erro": "Resposta inválida da Tiny."}

    retorno = dados.get("retorno", {})
    if retorno.get("status") != "OK":
        registros = retorno.get("registros") or [{}]
        erros = retorno.get("erros") or registros[0].get("registro", {}).get("erros", [])
        mensagens = [e.get("erro", "") for e in erros] if erros else ["erro desconhecido"]
        return {"erro": "; ".join(m for m in mensagens if m) or "erro desconhecido"}

    registro = (retorno.get("registros") or [{}])[0].get("registro", {})
    return {"ok": True, "numero": registro.get("numero"), "id": registro.get("id")}
