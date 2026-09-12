"""Geolocalizacao aproximada por IP -- usada SO pra estimar cidade e um
CEP representativo do visitante na pagina de produto (ver conversa "loja
mensageiros": Mensageiros mostra um prazo de entrega sem a pessoa
digitar nada). Isso e´ diferente de GPS do navegador (que pediria
permissao explicita) -- aqui o servidor so olha o IP de quem esta
acessando, sem pedir nada.

O calculo de frete de verdade (carrinho, services/frete.py) continua
por CEP exato, digitado pela pessoa -- geolocalizacao por IP so acerta
cidade/regiao, nunca o CEP completo (o "postal" que a base deles devolve
e´ so uma aproximacao), entao o resultado daqui e´ sempre uma ESTIMATIVA.

ipwho.is: gratis, sem chave, HTTPS -- trocado de ip-api.com (ver
conversa: "nao apareceu nem no pc nem no iphone") porque o endpoint
gratis do ip-api.com so funciona em HTTP puro (a versao HTTPS deles
exige plano pago, devolve 403), e va´rios provedores de hospedagem
bloqueiam saida HTTP simples por padrao -- explica a falha em
QUALQUER dispositivo/rede de quem acessa, ja que a chamada e´ sempre
feita pelo SERVIDOR (Render), nunca pelo navegador de quem visita.
Qualquer falha (timeout, IP fora do Brasil, sem CEP conhecido, IP local
de dev) devolve None, nunca levanta excecao -- o widget da pagina de
produto so some nesse caso."""

from __future__ import annotations

import re

import requests

IPWHOIS_URL = "https://ipwho.is/{ip}"
_TIMEOUT_SEGUNDOS = 4


def localizar_por_ip(ip: str) -> dict | None:
    """{"cidade", "estado", "cep"} a partir do IP, ou None se nao for
    possivel estimar (IP nao-BR, sem CEP conhecido, servico fora do ar)."""
    if not ip:
        return None
    try:
        resposta = requests.get(IPWHOIS_URL.format(ip=ip), timeout=_TIMEOUT_SEGUNDOS)
        resposta.raise_for_status()
        dados = resposta.json()
    except (requests.RequestException, ValueError):
        return None

    if not dados.get("success") or dados.get("country_code") != "BR":
        return None

    cep = re.sub(r"\D", "", dados.get("postal") or "")
    cidade = dados.get("city") or ""
    if len(cep) != 8 or not cidade:
        return None

    return {"cidade": cidade, "estado": dados.get("region") or "", "cep": cep}
