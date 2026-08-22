"""
Calculadora de frete do carrinho, via API da Frenet.

So cobre a Frenet por enquanto -- Azul Express (Melhor Envio) fica pra
depois, quando o token estiver em maos. O contrato proprio dos Correios
nao precisa de integracao separada: o preco bate com a tabela publica
que a propria Frenet ja retorna.

Regras de negocio (pedidas pelo usuario):
    - Peso por peca (services/frete.py:PESO_GRAMAS_POR_CHAVE) e uma
      unica caixa fixa (CAIXA_CM) pro pedido inteiro -- nao calculamos
      caixas multiplas por quantidade.
    - Servicos "mini envios" nunca aparecem como opcao (nem fora da
      faixa de frete gratis).
    - Quando o carrinho ja atinge frete gratis (calcular_carrinho ->
      frete_gratis_atingido), NAO mostramos as cotacoes calculadas --
      so o aviso de frete gratis e uma nota convidando a consultar um
      envio mais rapido com desconto pelo WhatsApp.
"""

from __future__ import annotations

import re

import requests

from config import CEP_ORIGEM, FRENET_TOKEN

FRENET_URL = "https://api.frenet.com.br/shipping/quote"

# Peso de cada peca, em gramas -- ver services/pricing.py pras mesmas chaves.
PESO_GRAMAS_POR_CHAVE = {
    "12mm": 1.5,
    "16mm": 2.0,
    "entremeio": 2.0,
    "chaveiro": 15.0,
}

# Caixa padrao usada pro pedido inteiro (altura x largura x comprimento, cm).
CAIXA_CM = {"altura": 4, "largura": 11, "comprimento": 17}

# Peso minimo (kg) mandado pra Frenet mesmo em pedidos muito leves --
# evita erro/cotacao invalida de transportadora com peso minimo de
# cubagem. Nao altera a cobranca real (isso e definido pela
# transportadora), so evita mandar um peso irrealisticamente baixo.
PESO_MINIMO_KG = 0.05


def _limpar_cep(cep: str) -> str:
    return re.sub(r"\D", "", cep or "")


def peso_total_gramas(itens: list[dict]) -> float:
    """`itens` no mesmo formato do carrinho: [{"chave_preco": ..., "quantidade": ...}]."""
    total = 0.0
    for item in itens:
        peso_unitario = PESO_GRAMAS_POR_CHAVE.get(item.get("chave_preco"), 0.0)
        total += peso_unitario * int(item.get("quantidade", 0))
    return total


def _preco_str_para_float(valor: str) -> float:
    """Frenet manda o preco como string em formato BR ("25,90")."""
    try:
        return float(str(valor).replace(".", "").replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _e_mini_envio(descricao: str) -> bool:
    return "mini" in (descricao or "").lower()


def consultar_frenet(cep_destino: str, peso_gramas: float, valor_declarado: float) -> dict:
    """Consulta a Frenet e devolve {"opcoes": [...]} ou {"erro": "..."}."""
    if not FRENET_TOKEN:
        return {"erro": "Calculadora de frete nao configurada (falta FRENET_TOKEN)."}
    if not CEP_ORIGEM:
        return {"erro": "Calculadora de frete nao configurada (falta CEP_ORIGEM)."}

    cep_destino = _limpar_cep(cep_destino)
    if len(cep_destino) != 8:
        return {"erro": "CEP invalido."}

    peso_kg = max(peso_gramas / 1000, PESO_MINIMO_KG)

    corpo = {
        "SellerCEP": _limpar_cep(CEP_ORIGEM),
        "RecipientCEP": cep_destino,
        "ShipmentInvoiceValue": round(valor_declarado, 2),
        "ShippingServiceCode": None,
        "RecipientCountry": "BR",
        "ShippingItemArray": [
            {
                "Height": CAIXA_CM["altura"],
                "Length": CAIXA_CM["comprimento"],
                "Width": CAIXA_CM["largura"],
                "Weight": round(peso_kg, 3),
                "Quantity": 1,
            }
        ],
    }

    try:
        resposta = requests.post(
            FRENET_URL,
            json=corpo,
            headers={"Content-Type": "application/json", "token": FRENET_TOKEN},
            timeout=10,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except requests.RequestException as exc:
        return {"erro": f"Nao foi possivel consultar o frete agora ({exc})."}
    except ValueError:
        return {"erro": "Resposta invalida da Frenet."}

    servicos = dados.get("ShippingSevicesArray", [])
    opcoes = []
    for servico in servicos:
        if servico.get("Error"):
            continue
        descricao = servico.get("ServiceDescription", "")
        if _e_mini_envio(descricao):
            continue
        opcoes.append(
            {
                "transportadora": servico.get("Carrier", ""),
                "servico": descricao,
                "preco": _preco_str_para_float(servico.get("ShippingPrice")),
                "prazo_dias": servico.get("DeliveryTime"),
            }
        )

    opcoes.sort(key=lambda o: o["preco"])
    return {"opcoes": opcoes}


def calcular_frete(
    itens: list[dict], cep_destino: str, subtotal: float, frete_gratis_atingido: bool
) -> dict:
    """Combina a regra de frete gratis com a cotacao real da Frenet.

    Quando o pedido ja atinge frete gratis, nao mostra as cotacoes
    calculadas -- so confirma que o frete gratis e a opcao mais barata
    e convida a consultar um envio mais rapido com desconto pelo
    WhatsApp (pedido explicito do usuario)."""
    if frete_gratis_atingido:
        return {
            "frete_gratis": True,
            "opcoes": [],
            "aviso": (
                "Seu pedido já garantiu frete grátis — essa é a opção mais barata. "
                "Quer receber mais rápido? Fale com a gente pelo WhatsApp enviando "
                "seu carrinho para consultar um envio expresso com desconto."
            ),
        }

    peso = peso_total_gramas(itens)
    resultado = consultar_frenet(cep_destino, peso, subtotal)
    if "erro" in resultado:
        return {"frete_gratis": False, "opcoes": [], "erro": resultado["erro"]}

    return {"frete_gratis": False, "opcoes": resultado["opcoes"]}
