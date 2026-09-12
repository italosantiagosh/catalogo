"""
Calculadora de frete do carrinho -- Frenet (Correios + demais
transportadoras) + Melhor Envio (Azul Express, LATAM Cargo, J&T
Express e Correios, com a tarifa contratada pelo usuario ali -- ver
TRANSPORTADORAS_MELHOR_ENVIO pra sobretaxas por transportadora).

Correios aparece nas duas fontes (Frenet com o preco do contrato
proprio do usuario, ja confirmado batendo; Melhor Envio tambem, a
pedido do usuario) -- podem aparecer 2 opcoes de Correios com precos
diferentes, isso e esperado dado o pedido, nao e bug.

Regras de negocio (pedidas pelo usuario):
    - Peso por peca (services/frete.py:PESO_KG_POR_CHAVE) e uma unica
      caixa fixa (CAIXA_CM) pro pedido inteiro -- nao calculamos caixas
      multiplas por quantidade.
    - Peso por peca e dimensoes da caixa conferidos com o cadastro real
      dos produtos na Yampi (mesma fonte que a cotacao que funciona
      por la usa) -- ja em kg com ate 3 casas decimais.
    - O peso REAL calculado (que pode ser so alguns gramas) nunca e
      mandado direto pra Frenet -- varias transportadoras simplesmente
      nao cotam ou devolvem lista vazia pra um peso declarado tao baixo
      (visto na pratica: nenhuma cotacao aparecia). Em vez disso o peso
      real e arredondado pra cima pro proximo "peso padrao" de envio
      (PESOS_PADRAO_KG: 300g / 500g / 1kg / 2kg, ou o peso real se
      passar de 2kg) -- imita o que uma transportadora real cobraria
      por uma caixa pequena de qualquer forma.
    - Sem seguro (ShipmentInvoiceValue sempre 0 na cotacao -- nao
      declara valor de mercadoria, entao a transportadora nao cobra
      premio de seguro em cima do frete).
    - "Mini envios" aparece normalmente como opcao, frete gratis ou nao.
    - Quando o carrinho ja atinge frete gratis (calcular_carrinho ->
      frete_gratis_atingido), mostramos TODAS as cotacoes calculadas
      normalmente, mas com um credito de frete gratis aplicado: a mais
      barata sai com preco original riscado e "Gratis"; as demais saem
      com preco original riscado e "Por R$X", onde X = preco original
      menos o preco da mais barata (o credito do frete gratis vale
      pra qualquer transportadora escolhida, nao so a mais barata --
      ver _resultado_frete_gratis).
"""

from __future__ import annotations

import re
import unicodedata

import requests

from config import CEP_ORIGEM, FRENET_TOKEN, MELHOR_ENVIO_TOKEN

FRENET_URL = "https://api.frenet.com.br/shipping/quote"
MELHOR_ENVIO_URL = "https://melhorenvio.com.br/api/v2/me/shipment/calculate"
# Obrigatorio pela API do Melhor Envio -- requisicoes sem User-Agent
# descritivo sao rejeitadas.
MELHOR_ENVIO_USER_AGENT = "Catálogo Nove de Julho (contato@lojanovedejulho.com.br)"

# Peso de cada peca, ja em kg -- confirmado pelo cadastro real dos
# produtos na Yampi (mesma fonte que a cotacao que da certo por la usa).
# Ver services/pricing.py pras mesmas chaves.
PESO_KG_POR_CHAVE = {
    "12mm": 0.001,
    "16mm": 0.002,
    "entremeio": 0.002,
    "chaveiro": 0.015,
    # Cruz para Terco (pedido em 2026-09-11) -- peso conferido pelo
    # usuario direto no cadastro real do material na Tiny (0,002 kg
    # liquido/bruto), mesmo criterio das linhas acima.
    "cruz_terco_prata": 0.002,
    "cruz_terco_ouro_velho": 0.002,
    "cruz_terco_dourado": 0.002,
}

# Caixa padrao usada pro pedido inteiro (altura x largura x comprimento,
# cm) -- confirmada pelo usuario a partir do cadastro real na Yampi.
CAIXA_CM = {"altura": 4, "largura": 12, "comprimento": 17}

# Categoria do item mandada pra Frenet -- nosso request original nao
# mandava esse campo (nem "isFragile"), presente em integracoes reais
# que funcionam (ex: Yampi). Suspeita forte de ser a causa das cotacoes
# absurdas: sem categoria, algumas transportadoras de carga parecem
# classificar o item numa faixa de preco erradas.
CATEGORIA_ITEM = "Bijuterias e Acessórios|Medalhas Religiosas"

# Faixas de peso padrao (kg) mandadas pra Frenet no lugar do peso real
# calculado -- pedido do usuario, pra evitar declarar um peso tao baixo
# que as transportadoras nao conseguem/nao querem cotar.
PESOS_PADRAO_KG = [0.3, 0.5, 1.0, 2.0]


def peso_padrao_kg(peso_real_kg: float) -> float:
    """Primeira faixa de PESOS_PADRAO_KG que cobre o peso real -- ou o
    proprio peso real, se passar da maior faixa (2kg)."""
    for faixa in PESOS_PADRAO_KG:
        if peso_real_kg <= faixa:
            return faixa
    return peso_real_kg

# Filtro de sanidade: algumas transportadoras de carga/cubagem (Jadlog,
# Loggi, Total Express) tem peso minimo faturavel alto e devolvem
# cotacoes absurdas pra um pacote de poucos gramas (visto na pratica --
# R$1700+ pra 50g de medalhas). Como isso nunca faz sentido pra um
# pedido de medalhas, descarta qualquer cotacao mais cara que
# LIMITE_MULTIPLICADOR_SUBTOTAL vezes o valor do pedido (com um piso
# minimo, pra nao filtrar frete legitimo em pedidos muito baratos).
LIMITE_MULTIPLICADOR_SUBTOTAL = 3
LIMITE_MINIMO_REAIS = 150.0


def _limpar_cep(cep: str) -> str:
    return re.sub(r"\D", "", cep or "")


def peso_total_kg(itens: list[dict]) -> float:
    """`itens` no mesmo formato do carrinho: [{"chave_preco": ..., "quantidade": ...}]."""
    total = 0.0
    for item in itens:
        peso_unitario = PESO_KG_POR_CHAVE.get(item.get("chave_preco"), 0.0)
        total += peso_unitario * int(item.get("quantidade", 0))
    return round(total, 3)


def _preco_str_para_float(valor) -> float:
    """Frenet manda o preco com ponto decimal (ex: "17.09"), NAO em
    formato BR com virgula. Bug ja corrigido: o codigo tratava "." como
    separador de milhar e removia, inflando o preco por 100x --
    "17.09" virava "1709" (confirmado comparando com o valor real
    mostrado no site oficial: R$1709 aqui vs R$17,09 la)."""
    try:
        return round(float(valor), 2)
    except (TypeError, ValueError):
        return 0.0


def _normalizar_nome(nome: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (nome or "").lower())


# Logo por transportadora (ver conversa: "logo oficial miniatura de cada
# transportadora antes do nome" no simulador de frete e no painel admin)
# -- mesmo criterio de match por trecho do nome ja normalizado usado em
# MARGEM_DIAS_UTEIS_POR_TRANSPORTADORA acima, reaproveitado aqui pra nao
# duplicar a logica de normalizacao. Cobre as transportadoras que
# aparecem na cotacao hoje (Correios, Azul Cargo Express, LATAM Cargo,
# J&T Express, Loggi, Jadlog, Total Express).
LOGO_POR_TRANSPORTADORA = {
    "correios": "correios.svg",
    "azul": "azul-cargo.png",
    "latam": "latam-cargo.svg",
    "jt": "jt-express.svg",
    "loggi": "loggi.png",
    "jadlog": "jadlog.png",
    "total": "total-express.png",
}


def logo_transportadora(nome: str) -> str | None:
    """Nome do arquivo em static/img/transportadoras/ pra essa
    transportadora, ou None se nao tiver logo cadastrada (usado tanto
    no nome cru vindo da cotacao quanto no campo `transportadora`
    digitado a mao no admin, ver app.py:_dados_pedido_admin e
    templates/admin_pedidos.html/admin_pedido_detalhe.html)."""
    nome_normalizado = _normalizar_nome(nome)
    return next(
        (arquivo for chave, arquivo in LOGO_POR_TRANSPORTADORA.items() if chave in nome_normalizado),
        None,
    )


# Nomes EXATOS que a cotacao (Frenet/Melhor Envio) realmente devolve pra
# cada transportadora -- usado so por descricao_sem_nome_transportadora
# abaixo, pra saber removedor o nome do INICIO de frete_descricao com
# seguranca (esse campo e´ salvo pronto desde a criacao do pedido, no
# formato "{transportadora} {servico} — {preco}", sempre o mesmo jeito,
# ver static/js/carrinho_pagina.js). Mais especifico primeiro (ex: "Azul
# Cargo Express" antes de so "Azul") nao importa aqui porque quem chama
# ja ordena por tamanho.
_NOMES_TRANSPORTADORA_CONHECIDOS = [
    "Correios", "Azul Cargo Express", "Azul Express", "LATAM Cargo",
    "J&T Express", "Loggi", "Jadlog", "Total Express",
]


# Deteccao dos Correios pro aviso da greve + logo oficial no link de
# acompanhamento do cliente (templates/pedido.html, pedido do usuario
# 2026-09-12) -- cobre tanto o nome escrito por extenso ("Correios")
# quanto uma modalidade digitada sozinha A MAO no admin, sem a palavra
# "Correios" no meio (Mini Envios, PAC, Sedex). Usa \b (limite de
# palavra) em vez do mesmo criterio de substring de logo_transportadora
# acima porque "pac" e curto demais pra isso -- bateria por engano
# dentro de palavras como "espaco" (sem acento).
_PADRAO_CORREIOS = re.compile(r"\b(correios|mini\s*envios|pac|sedex)\b", re.IGNORECASE)


def _sem_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def eh_correios(*textos: str | None) -> bool:
    """True se qualquer um dos textos passados (transportadora,
    frete_descricao, ...) mencionar os Correios -- pelo nome ou por uma
    das modalidades deles (Mini Envios/PAC/Sedex), mesmo digitado a mao
    no admin sem a palavra "Correios" junto."""
    return any(texto and _PADRAO_CORREIOS.search(_sem_acentos(texto)) for texto in textos)


def descricao_sem_nome_transportadora(frete_descricao: str) -> str | None:
    """Remove o nome da transportadora do INICIO de `frete_descricao`
    (ex.: "Correios SEDEX — R$25,90" -> "SEDEX — R$25,90") -- pra usar
    do lado da logo sem repetir o nome (ver conversa: "realmente me
    incomoda a repeticao"). So mexe quando reconhece um nome EXATO
    conhecido bem no comeco da string; qualquer formato que nao bata
    (retirada no local, texto editado a mao, transportadora nova ainda
    nao mapeada aqui) devolve None -- quem chama mostra o texto
    original completo nesse caso, nunca corta errado."""
    texto = (frete_descricao or "").strip()
    for nome in sorted(_NOMES_TRANSPORTADORA_CONHECIDOS, key=len, reverse=True):
        if texto.startswith(nome + " "):
            return texto[len(nome):].strip()
    return None


# Margem de dias uteis somada em CIMA do prazo que a Frenet/Melhor Envio
# cotam -- pedido do usuario 2026-09: na pratica a encomenda as vezes so
# e´ efetivamente encaminhada pela transportadora no dia UTIL SEGUINTE
# ao da postagem (nao no mesmo dia), entao o prazo cotado pela API
# ficava sistematicamente mais otimista do que a entrega real. Ajuste
# por transportadora (pedido do usuario 2026-09-10, depois de acompanhar
# a entrega real de cada uma por um tempo): Azul Express e LATAM Cargo
# mantem a margem original de 1 dia; Correios ganha mais 1 (fica em 2,
# o mais atrasado na pratica); as demais (J&T Express, Jadlog, etc. --
# "o restante") voltam a usar o prazo cru da API, sem margem nenhuma.
# Chave e um trecho do nome ja normalizado, mesmo criterio de
# TRANSPORTADORAS_MELHOR_ENVIO abaixo -- serve tanto pro nome cru da
# Frenet ("Carrier") quanto da Melhor Envio ("company.name").
MARGEM_DIAS_UTEIS_POR_TRANSPORTADORA = {
    "azul": 1,
    "latam": 1,
    "correios": 2,
}
MARGEM_DIAS_UTEIS_PADRAO = 0


def _margem_dias_uteis(nome_transportadora: str) -> int:
    nome_normalizado = _normalizar_nome(nome_transportadora)
    return next(
        (
            margem
            for chave, margem in MARGEM_DIAS_UTEIS_POR_TRANSPORTADORA.items()
            if chave in nome_normalizado
        ),
        MARGEM_DIAS_UTEIS_PADRAO,
    )


def _prazo_dias_com_margem(bruto, nome_transportadora: str) -> int | None:
    try:
        return int(bruto) + _margem_dias_uteis(nome_transportadora)
    except (TypeError, ValueError):
        return None


def consultar_frenet(cep_destino: str, peso_kg: float, subtotal: float) -> dict:
    """Consulta a Frenet e devolve {"opcoes": [...]} ou {"erro": "..."}."""
    if not FRENET_TOKEN:
        return {"erro": "Calculadora de frete nao configurada (falta FRENET_TOKEN)."}
    if not CEP_ORIGEM:
        return {"erro": "Calculadora de frete nao configurada (falta CEP_ORIGEM)."}

    cep_destino = _limpar_cep(cep_destino)
    if len(cep_destino) != 8:
        return {"erro": "CEP invalido."}

    corpo = {
        "SellerCEP": _limpar_cep(CEP_ORIGEM),
        "RecipientCEP": cep_destino,
        "ShipmentInvoiceValue": 0,  # sem seguro -- nao declara valor de mercadoria
        "ShippingServiceCode": None,
        "RecipientCountry": "BR",
        "ShippingItemArray": [
            {
                "Height": CAIXA_CM["altura"],
                "Length": CAIXA_CM["comprimento"],
                "Width": CAIXA_CM["largura"],
                "Weight": round(peso_kg, 3),
                "Quantity": 1,
                "Category": CATEGORIA_ITEM,
                "isFragile": False,
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

    limite_preco = max(subtotal * LIMITE_MULTIPLICADOR_SUBTOTAL, LIMITE_MINIMO_REAIS)

    servicos = dados.get("ShippingSevicesArray", [])
    opcoes = []
    descartadas_por_preco_absurdo = 0
    for servico in servicos:
        if servico.get("Error"):
            continue
        # Azul Express vem do Melhor Envio (tarifa contratada pelo
        # usuario ali, ver consultar_melhor_envio) -- ignora a versao
        # generica da Frenet aqui pra nao duplicar/confundir com 2
        # precos diferentes pra "Azul".
        if "azul" in servico.get("Carrier", "").lower():
            continue
        preco = _preco_str_para_float(servico.get("ShippingPrice"))
        if preco > limite_preco:
            descartadas_por_preco_absurdo += 1
            continue
        opcoes.append(
            {
                "transportadora": servico.get("Carrier", ""),
                "servico": servico.get("ServiceDescription", ""),
                "preco": preco,
                "prazo_dias": _prazo_dias_com_margem(servico.get("DeliveryTime"), servico.get("Carrier", "")),
            }
        )

    opcoes.sort(key=lambda o: o["preco"])
    resultado = {"opcoes": opcoes}
    if not opcoes and descartadas_por_preco_absurdo:
        resultado["erro"] = (
            "Não conseguimos calcular um frete confiável para esse CEP agora. "
            "Fale com a gente pelo WhatsApp enviando seu carrinho para consultar o valor."
        )
    return resultado


# Transportadoras cotadas no Melhor Envio -- chave e um trecho do nome
# ja normalizado (sem espaco/acento/pontuacao) pra casar com o nome que
# a API devolve (ex: "J&T Express" -> "jtexpress", contem "jt").
# Valor e uma sobretaxa fixa em R$ somada ao preco de cada cotacao
# dessa transportadora (pedido do usuario) -- 0 quando nao ha sobretaxa.
TRANSPORTADORAS_MELHOR_ENVIO = {
    "azul": 5.0,
    "latam": 50.0,
    "jt": 20.0,  # J&T Express
    "correios": 0.0,
}


def consultar_melhor_envio(cep_destino: str, peso_kg: float, subtotal: float) -> list[dict]:
    """Cota Azul Express, LATAM Cargo, J&T Express e Correios no Melhor
    Envio (tarifas contratadas pelo usuario ali -- ver
    TRANSPORTADORAS_MELHOR_ENVIO pra sobretaxas). Ao contrario da
    Frenet, a ausencia de token aqui NAO e um erro -- essa fonte e
    complementar, o carrinho continua funcionando so com a Frenet se
    nao estiver configurada. Retorna uma lista de opcoes (pode ser
    vazia), nunca um erro visivel."""
    if not MELHOR_ENVIO_TOKEN:
        return []

    cep_destino = _limpar_cep(cep_destino)
    if len(cep_destino) != 8:
        return []

    corpo = {
        "from": {"postal_code": _limpar_cep(CEP_ORIGEM)},
        "to": {"postal_code": cep_destino},
        "package": {
            "height": CAIXA_CM["altura"],
            "width": CAIXA_CM["largura"],
            "length": CAIXA_CM["comprimento"],
            "weight": round(peso_kg, 3),
        },
        "options": {"insurance_value": 0, "receipt": False, "own_hand": False},
    }

    try:
        resposta = requests.post(
            MELHOR_ENVIO_URL,
            json=corpo,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {MELHOR_ENVIO_TOKEN}",
                "User-Agent": MELHOR_ENVIO_USER_AGENT,
            },
            timeout=10,
        )
        resposta.raise_for_status()
        servicos = resposta.json()
    except (requests.RequestException, ValueError):
        return []

    if not isinstance(servicos, list):
        return []

    limite_preco = max(subtotal * LIMITE_MULTIPLICADOR_SUBTOTAL, LIMITE_MINIMO_REAIS)

    opcoes = []
    for servico in servicos:
        if servico.get("error"):
            continue
        nome_transportadora = (servico.get("company") or {}).get("name", "")
        nome_normalizado = _normalizar_nome(nome_transportadora)
        sobretaxa = next(
            (
                valor
                for chave, valor in TRANSPORTADORAS_MELHOR_ENVIO.items()
                if chave in nome_normalizado
            ),
            None,
        )
        if sobretaxa is None:
            continue
        preco = _preco_str_para_float(servico.get("price")) + sobretaxa
        if preco <= 0 or preco > limite_preco:
            continue
        opcoes.append(
            {
                "transportadora": nome_transportadora,
                "servico": servico.get("name", ""),
                "preco": round(preco, 2),
                "prazo_dias": _prazo_dias_com_margem(servico.get("delivery_time"), nome_transportadora),
            }
        )
    return opcoes


AVISO_FRETE_GRATIS = (
    "Frete grátis garantido, em qualquer transportadora escolhida. Quer mais "
    "rápido? Chama no WhatsApp pra consultar um envio expresso."
)


def _resultado_frete_gratis(opcoes: list[dict]) -> dict:
    """Aplica o credito de frete gratis (pedido do usuario) em cima das
    cotacoes reais ja calculadas: a mais barata sai com preco original
    riscado e "Gratis"; as demais saem com preco original riscado e
    "Por R$X", onde X = preco original menos o preco da mais barata --
    o credito vale pra qualquer transportadora, nao so a mais barata.
    Sem cotacoes (nenhuma fonte respondeu), cai no aviso antigo."""
    if not opcoes:
        return {"frete_gratis": True, "opcoes": [], "aviso": AVISO_FRETE_GRATIS}

    credito = opcoes[0]["preco"]
    opcoes_com_credito = [
        {
            "transportadora": opcao["transportadora"],
            "servico": opcao["servico"],
            "prazo_dias": opcao["prazo_dias"],
            "preco_original": opcao["preco"],
            "preco_final": (preco_final := round(max(opcao["preco"] - credito, 0.0), 2)),
            "gratis": preco_final == 0.0,
        }
        for opcao in opcoes
    ]
    return {"frete_gratis": True, "opcoes": opcoes_com_credito, "aviso": AVISO_FRETE_GRATIS}


def _preco_final_desconto_atacado(preco_original: float, desconto: float) -> float:
    """Abate o desconto fixo em R$ do preco original -- se sobrar menos
    de R$1 (mas mais que zero), arredonda logo pra gratis (pedido do
    usuario: nao faz sentido cobrar centavos de frete)."""
    valor = round(max(preco_original - desconto, 0.0), 2)
    return 0.0 if 0 < valor < 1.0 else valor


def _resultado_desconto_atacado(opcoes: list[dict], desconto: float) -> dict:
    """Aplica o desconto de frete por atacado (8% do subtotal do grupo
    que ja atingiu a primeira faixa de atacado, ver
    services.pricing.DESCONTO_FRETE_ATACADO_PCT -- pedido do usuario,
    regra separada e ANTERIOR ao credito de frete gratis) em cima das
    cotacoes reais: mesmo layout visual do credito de frete gratis
    (preco original riscado + preco final), so que aqui o credito e um
    valor FIXO em R$ (o desconto calculado), nao o preco da opcao mais
    barata -- entao raramente zera o frete inteiro, so abate uma parte
    (ver _preco_final_desconto_atacado pro arredondamento pra gratis
    quando sobra menos de R$1)."""
    return {
        "frete_gratis": False,
        "desconto_atacado_reais": desconto,
        "opcoes": [
            {
                "transportadora": opcao["transportadora"],
                "servico": opcao["servico"],
                "prazo_dias": opcao["prazo_dias"],
                "preco_original": opcao["preco"],
                "preco_final": (preco_final := _preco_final_desconto_atacado(opcao["preco"], desconto)),
                "gratis": preco_final == 0.0,
            }
            for opcao in opcoes
        ],
    }


def calcular_frete(
    itens: list[dict],
    cep_destino: str,
    subtotal: float,
    frete_gratis_atingido: bool,
    desconto_frete_atacado: float = 0.0,
) -> dict:
    """Combina a regra de frete gratis com a cotacao real da Frenet +
    Melhor Envio. Quando o pedido ja atinge frete gratis, ainda cotamos
    tudo normalmente e aplicamos o credito de frete gratis em cima
    (ver _resultado_frete_gratis) -- pedido do usuario, pra mostrar
    todas as opcoes mesmo com frete gratis. Antes de chegar la, se
    algum grupo do carrinho ja atingiu a primeira faixa de atacado
    (ver services.pricing.calcular_carrinho -> desconto_frete_atacado),
    aplica um desconto parcial em cima da cotacao real (ver
    _resultado_desconto_atacado) -- as duas regras nunca se somam, o
    frete gratis (mais vantajoso) sempre tem prioridade quando atingido."""
    peso_real_kg = peso_total_kg(itens)
    peso_kg = peso_padrao_kg(peso_real_kg)

    resultado = consultar_frenet(cep_destino, peso_kg, subtotal)
    opcoes = list(resultado.get("opcoes", []))
    opcoes += consultar_melhor_envio(cep_destino, peso_kg, subtotal)
    opcoes.sort(key=lambda o: o["preco"])

    if frete_gratis_atingido:
        return _resultado_frete_gratis(opcoes)

    if not opcoes and "erro" in resultado:
        return {"frete_gratis": False, "opcoes": [], "erro": resultado["erro"]}

    if desconto_frete_atacado > 0 and opcoes:
        return _resultado_desconto_atacado(opcoes, desconto_frete_atacado)

    return {"frete_gratis": False, "opcoes": opcoes}


# Peso/subtotal genericos usados SO na estimativa por localizacao da
# pagina de produto (services/geolocalizacao.py + app.py) -- antes da
# pessoa escolher formato/quantidade nao ha carrinho de verdade pra
# calcular o peso real, entao usa a menor caixa padrao (PESOS_PADRAO_KG)
# como representativa de um pedido tipico de 1 produto. Nunca usado pro
# calculo de verdade do carrinho (calcular_frete acima, que sempre usa o
# peso real dos itens).
PESO_KG_ESTIMATIVA_GENERICA = PESOS_PADRAO_KG[0]
SUBTOTAL_ESTIMATIVA_GENERICA = 100.0


def opcoes_frete_estimativa(cep_destino: str) -> list[dict]:
    """Mesmas fontes (Frenet + Melhor Envio) do calculo exato do
    carrinho, com peso/subtotal genericos -- sem frete gratis nem
    desconto de atacado (nao fazem sentido fora de um carrinho de
    verdade). Lista vazia em qualquer falha (CEP invalido, APIs fora do
    ar, nenhuma cotacao) -- quem chama decide o que mostrar nesse caso."""
    resultado = consultar_frenet(cep_destino, PESO_KG_ESTIMATIVA_GENERICA, SUBTOTAL_ESTIMATIVA_GENERICA)
    opcoes = list(resultado.get("opcoes", []))
    opcoes += consultar_melhor_envio(cep_destino, PESO_KG_ESTIMATIVA_GENERICA, SUBTOTAL_ESTIMATIVA_GENERICA)
    opcoes.sort(key=lambda o: o["preco"])
    return opcoes
