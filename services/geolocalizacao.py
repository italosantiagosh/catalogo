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


def _cep_normalizado(postal: str) -> str | None:
    """O `postal` que o ipwho.is devolve e´ inconsistente: as vezes vem o
    CEP completo (8 digitos, ex: "99010-041"), mas na MAIORIA dos IPs
    testados vem so o PREFIXO da regiao (5 digitos, ex: "90020") -- e
    quando esse prefixo comeca com zero (comum: varias faixas de Sao
    Paulo comecam com 0), o zero a esquerda se perde (ex: "01002" volta
    como "1002", 4 digitos), provavelmente porque o provedor trata o
    campo como numero em algum ponto. O codigo original exigia 8 digitos
    exatos e descartava qualquer coisa fora disso como "sem CEP conhecido"
    -- na pratica isso rejeitava a maior parte dos visitantes brasileiros
    (ver conversa: "a barra sumiu"), nao so casos raros.

    Quando so temos o prefixo, completa com "000" -- e´ o sufixo GENERICO
    de verdade que os Correios usam pra faixa de uma regiao sem numero de
    rua especifico (ex: 01310-000 pra Av. Paulista), entao serve como CEP
    de estimativa legitimo pra cotar frete pela regiao."""
    digitos = re.sub(r"\D", "", postal or "")
    if len(digitos) == 8:
        return digitos
    if 1 <= len(digitos) <= 5:
        return digitos.zfill(5) + "000"
    return None


_TENTATIVAS = 2


def _consultar_ipwhois(ip: str) -> dict | None:
    """Uma tentativa crua (sem retry) -- None em qualquer falha de rede ou
    resposta invalida."""
    try:
        resposta = requests.get(IPWHOIS_URL.format(ip=ip), timeout=_TIMEOUT_SEGUNDOS)
        resposta.raise_for_status()
        return resposta.json()
    except (requests.RequestException, ValueError):
        return None


def localizar_por_ip(ip: str) -> dict | None:
    """{"cidade", "estado", "cep"} a partir do IP, ou None se nao for
    possivel estimar (IP nao-BR, sem CEP conhecido, servico fora do ar).

    Chamado em TODA visita a pagina de produto (sem cache aqui -- ver
    app.py:_localizacao_cacheada_por_ip pro cache real), entao um
    timeout/erro de rede pontual do ipwho.is (inevitavel numa API gratis
    sem SLA, ja visto em producao) esconderia a barra sem necessidade --
    tenta de novo uma vez antes de desistir."""
    if not ip:
        return None

    dados = None
    for tentativa in range(_TENTATIVAS):
        dados = _consultar_ipwhois(ip)
        if dados is not None:
            break
    if dados is None:
        return None

    if not dados.get("success") or dados.get("country_code") != "BR":
        return None

    cep = _cep_normalizado(dados.get("postal") or "")
    cidade = dados.get("city") or ""
    if cep is None or not cidade:
        return None

    return {"cidade": cidade, "estado": dados.get("region") or "", "cep": cep}
