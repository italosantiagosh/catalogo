"""
Sincronizacao de pedidos pagos com a Tiny/Olist ERP (API 2.0) -- ver
app.py:webhook_infinitepay, chamado uma unica vez por pedido logo
depois que o pagamento e´ confirmado (services.pedidos.marcar_tiny_sincronizado
evita reenviar em webhook duplicado).

Endpoint e layout do parametro `pedido` conferidos no exemplo oficial
da documentacao (colado pelo usuario -- o ambiente onde isso foi
desenvolvido nao alcanca tiny.com.br pra acessar direto).

CONFIRMADO com pedido de teste real (pedido Tiny #1113, status "OK"):
  - `forma_pagamento="pix"` aparece na Tiny como "Forma de recebimento:
    Pix";
  - `frete_por_conta="E"` e´ guardado como "Contratação do Frete por
    conta do Remetente (CIF)" -- exatamente "loja contrata o frete",
    como pretendido.
NAO confirmado ainda: `forma_pagamento="cartao_credito"` (mapeamento
pra pagamento via cartao na InfinitePay) -- so testamos Pix ate agora.
Se a Tiny rejeitar esse valor, ainda assim preferimos deixar o pedido
salvo no site (ver chamada em app.py) a travar o webhook por causa
disso.
"""

from __future__ import annotations

import json

import requests

from config import TINY_API_TOKEN

API_URL = "https://api.tiny.com.br/api2/pedido.incluir.php"

_TIPO_PESSOA = {"fisica": "F", "juridica": "J"}

# capture_method (InfinitePay) -> forma_pagamento (Tiny) -- "pix"
# confirmado com pedido de teste real, "cartao_credito" ainda nao (ver
# aviso no topo do arquivo).
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


# O `codigo` mandado pra Tiny controla ESTOQUE (materia-prima comprada),
# nao precisa (nem deve) ter um por santo -- o catalogo inteiro usa so
# 4 chave_preco (12mm/16mm/entremeio/chaveiro, ver services/pricing.py),
# entao cadastrando so esses produtos na Tiny o estoque ja fica agrupado
# do jeito que a compra de material realmente acontece. Excecao:
# entremeio prata e ouro velho sao materia-prima comprada SEPARADA (ver
# conversa), entao viram 2 codigos diferentes aqui mesmo sem existir 2
# chave_preco (chave_preco so afeta PRECO/desconto, que e igual pros
# dois -- nao mexer nisso). O nome do santo continua so na `descricao`
# de cada linha, nunca no `codigo` (ver _itens_com_descricao_do_corpo
# em app.py, que ja monta essa descricao com produto+modelo+detalhe).
def _codigo_estoque_tiny(item: dict) -> str:
    chave_preco = item.get("chave_preco", "")
    if chave_preco == "entremeio" and item.get("cor"):
        return f"entremeio_{item['cor']}"
    return chave_preco


def _itens_para_tiny(itens: list[dict]) -> list[dict]:
    return [
        {
            "item": {
                "codigo": _codigo_estoque_tiny(item),
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
    if pedido.get("endereco_destinatario_nome"):
        doc_dest = pedido.get("endereco_destinatario_documento", "")
        observacoes.append(
            f"Entregar aos cuidados de: {pedido['endereco_destinatario_nome']}"
            + (f" ({doc_dest})" if doc_dest else "")
        )
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
