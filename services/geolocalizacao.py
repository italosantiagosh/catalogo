"""Geolocalizacao aproximada por IP -- usada SO pra estimar cidade e um
CEP representativo do visitante na pagina de produto (ver conversa "loja
mensageiros": Mensageiros mostra um prazo de entrega sem a pessoa
digitar nada). Isso e´ diferente de GPS do navegador (que pediria
permissao explicita) -- aqui o servidor so olha o IP de quem esta
acessando, sem pedir nada.

O calculo de frete de verdade (carrinho, services/frete.py) continua
por CEP exato, digitado pela pessoa -- geolocalizacao por IP so acerta
cidade/regiao, nunca o CEP completo (o "zip" que a base deles devolve e´
so uma aproximacao), entao o resultado daqui e´ sempre uma ESTIMATIVA.

ip-api.com: gratis, sem chave, ~45 requisicoes/minuto por IP de origem
(nosso servidor) -- suficiente pro volume de visitas em paginas de
produto. Qualquer falha (timeout, IP fora do Brasil, sem CEP conhecido,
IP local de dev) devolve None, nunca levanta excecao -- o widget da
pagina de produto so some nesse caso."""

from __future__ import annotations

import re

import requests

IP_API_URL = "http://ip-api.com/json/{ip}"
_CAMPOS = "status,countryCode,regionName,city,zip"
_TIMEOUT_SEGUNDOS = 4


def localizar_por_ip(ip: str) -> dict | None:
    """{"cidade", "estado", "cep"} a partir do IP, ou None se nao for
    possivel estimar (IP nao-BR, sem CEP conhecido, servico fora do ar)."""
    if not ip:
        return None
    try:
        resposta = requests.get(
            IP_API_URL.format(ip=ip),
            params={"fields": _CAMPOS},
            timeout=_TIMEOUT_SEGUNDOS,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except (requests.RequestException, ValueError):
        return None

    if dados.get("status") != "success" or dados.get("countryCode") != "BR":
        return None

    cep = re.sub(r"\D", "", dados.get("zip") or "")
    cidade = dados.get("city") or ""
    if len(cep) != 8 or not cidade:
        return None

    return {"cidade": cidade, "estado": dados.get("regionName") or "", "cep": cep}
