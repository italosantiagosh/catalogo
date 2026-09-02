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
NAO confirmado ainda:
  - `forma_pagamento="cartao_credito"` (mapeamento pra pagamento via
    cartao na InfinitePay) -- so testamos Pix ate agora;
  - o bloco `endereco_entrega` (nome dos campos), usado quando o
    cliente pede entrega num endereco diferente do proprio (ver
    criar_pedido_tiny) -- ainda sem pedido de teste real com isso
    preenchido;
  - `buscar_contatos_tiny` (contatos.pesquisa.php, usado no painel pra
    puxar endereco de contato ja salvo -- ver app.py:admin_tiny_buscar_contato)
    -- nomes de campo seguindo so a documentacao publica, sem busca
    real feita ainda.
Se a Tiny rejeitar algum desses valores, ainda assim preferimos deixar
o pedido salvo no site (ver chamada em app.py) a travar o webhook por
causa disso.
"""

from __future__ import annotations

import json

import requests

from config import TINY_API_TOKEN

API_URL = "https://api.tiny.com.br/api2/pedido.incluir.php"
BUSCA_CONTATOS_URL = "https://api.tiny.com.br/api2/contatos.pesquisa.php"

_TIPO_PESSOA_TINY_PARA_SITE = {"F": "fisica", "J": "juridica"}

_TIPO_PESSOA = {"fisica": "F", "juridica": "J"}

# capture_method (InfinitePay) -> forma_pagamento (Tiny) -- "pix"
# confirmado com pedido de teste real, "cartao_credito" ainda nao (ver
# aviso no topo do arquivo).
_FORMA_PAGAMENTO = {"pix": "pix", "credit_card": "cartao_credito"}


# Inscricao Estadual so faz sentido pra pessoa juridica (isento nunca
# guarda numero -- ver services.pedidos/_cliente_valido em app.py).
# "contribuinte" segue os valores documentados na API 2.0 da Tiny: 1 =
# Contribuinte ICMS, 2 = Contribuinte isento de Inscricao Estadual, 9 =
# Nao Contribuinte. AINDA NAO confirmado com pedido de teste real (o
# campo nunca tinha sido mandado ate agora -- usuario reportou que a IE
# nao estava chegando na Tiny, ver conversa. Ate esse ponto so ficava
# guardada no banco do site, nunca ia pro corpo do pedido.incluir.php).
def _contribuinte_tiny(pedido: dict) -> str | None:
    if pedido.get("cliente_tipo_pessoa") != "juridica":
        return None
    if pedido.get("cliente_ie_isento"):
        return "2"
    if pedido.get("cliente_ie_nao_contribuinte"):
        return "9"
    if pedido.get("cliente_inscricao_estadual"):
        return "1"
    return None


def _cliente_para_tiny(pedido: dict) -> dict:
    documento = pedido.get("cliente_documento", "")
    telefone = pedido.get("cliente_telefone", "")
    cliente = {
        "nome": pedido.get("cliente_nome", ""),
        "tipo_pessoa": _TIPO_PESSOA.get(pedido.get("cliente_tipo_pessoa"), "F"),
        "cpf_cnpj": documento,
        "cpfConsumidorFinal": documento,
        # e-mail nunca era mandado (usuario reportou que o campo ficava
        # vazio na Tiny, ver conversa) -- "fone" e´ CONFIRMADO (pedido de
        # teste real), "celular" e "email" seguem o mesmo padrao de nome
        # de campo em portugues ja usado no resto do bloco, mas AINDA
        # NAO confirmados com pedido de teste real.
        "fone": telefone,
        "celular": telefone,
        "email": pedido.get("cliente_email", ""),
        "endereco": pedido.get("endereco_logradouro", ""),
        "numero": pedido.get("endereco_numero", ""),
        "complemento": pedido.get("endereco_complemento", ""),
        "bairro": pedido.get("endereco_bairro", ""),
        "cep": pedido.get("endereco_cep", ""),
        "cidade": pedido.get("endereco_cidade", ""),
        "uf": pedido.get("endereco_uf", ""),
    }
    if pedido.get("cliente_inscricao_estadual"):
        cliente["ie"] = pedido["cliente_inscricao_estadual"]
    contribuinte = _contribuinte_tiny(pedido)
    if contribuinte:
        cliente["contribuinte"] = contribuinte
    return cliente


# Codigo/descricao mandados pra Tiny -- ja foi por santo+modelo+variacao
# (ex: "MED-ANUNCIACAO-M1-16mm", descricao "São José — Modelo 1 —
# Medalha · 16mm"), mas isso quebrava a EMISSAO da nota fiscal ("A
# descrição do produto está em branco, incompleta ou contém caracteres
# inválidos" -- o travessão "—" nao e´ um caractere valido pro XML da
# NF-e) e deixava a nota gigante (uma linha por santo+modelo+tamanho em
# vez de uma por formato). Revertido a pedido da usuaria (ver conversa)
# pro codigo/descricao AGREGADOS por materia-prima -- santo/modelo
# continuam especificos so no painel admin e na pagina do pedido pro
# cliente (ver app.py:_itens_com_descricao_do_corpo), nunca mandados
# pra Tiny. Efeito aceito pela usuaria: a Tiny nao separa mais
# estoque/relatorio de vendas por santo, so por formato+tamanho.
#
# IMPORTANTE: os codigos abaixo NAO sao inventados aqui -- sao os SKUs
# reais das VARIACOES dos produtos "pai" que a usuaria ja usa ha anos
# na Tiny ("Medalha Personalizada", variacao Tamanho; "Entremeio
# Personalizado de 1 lado", variacao Cor; ver conversa, print de
# erp.olist.com/produtos#edit/.../variacoes). Nao precisa importar
# nada nem cadastrar produto novo -- so mandar o codigo certo. Chaveiro
# ja e´ um produto simples (sem variacao), codigo "Chaveiro" mesmo,
# confirmado num pedido real que sincronizou certo.
#
# "Medalha Personalizada de 2 lados" (produto proprio, variacao
# Tamanho x Cor -- 1,8cm/1,4cm × Prata/Ouro velho) e "Entremeio
# Personalizado de 2 lados" (produto proprio, variacao so Cor) --
# SKUs mandados pela usuaria em 2026-09-02 (print da tela de variacoes
# do Tiny). O Tiny tambem tem um SKU cadastrado pra "Dourado" no
# entremeio de 2 lados (V9SBJB3M3), mas o SITE ainda so oferece
# prata/ouro velho pra esse formato -- guardado aqui mesmo assim
# (nao atrapalha, so fica sem uso ate o site ganhar essa cor).
_CODIGO_MATERIAL_TINY = {
    "12mm": "WSL5RSRKA",
    "16mm": "LCEHXXXNP",
    "entremeio_prata": "XQWBRR2FK",
    "entremeio_ouro_velho": "KY5EZHCF5",
    "chaveiro": "Chaveiro",
    "medalha_2lados_18mm_prata": "2A6RZ54SH",
    "medalha_2lados_14mm_prata": "SLEK863TR",
    "medalha_2lados_18mm_ouro_velho": "8SSCLZ3UK",
    "medalha_2lados_14mm_ouro_velho": "8CDKFLKH2",
    "entremeio_2lados_prata": "62LWPVMNR",
    "entremeio_2lados_ouro_velho": "5TQHLBKE2",
    "entremeio_2lados_dourado": "V9SBJB3M3",
}

_DESCRICAO_MATERIAL_TINY = {
    "12mm": "Medalha Personalizada - 1,2cm",
    "16mm": "Medalha Personalizada - 1,6cm",
    "entremeio_prata": "Entremeio Personalizado de 1 lado - Prata",
    "entremeio_ouro_velho": "Entremeio Personalizado de 1 lado - Ouro velho",
    "chaveiro": "Chaveiro Personalizado",
    "medalha_2lados_18mm_prata": "Medalha Personalizada de 2 lados - 1,8cm - Prata",
    "medalha_2lados_14mm_prata": "Medalha Personalizada de 2 lados - 1,4cm - Prata",
    "medalha_2lados_18mm_ouro_velho": "Medalha Personalizada de 2 lados - 1,8cm - Ouro velho",
    "medalha_2lados_14mm_ouro_velho": "Medalha Personalizada de 2 lados - 1,4cm - Ouro velho",
    "entremeio_2lados_prata": "Entremeio Personalizado de 2 lados - Prata",
    "entremeio_2lados_ouro_velho": "Entremeio Personalizado de 2 lados - Ouro velho",
    "entremeio_2lados_dourado": "Entremeio Personalizado de 2 lados - Dourado",
}


def _chave_material(item: dict) -> str:
    chave_preco = item.get("chave_preco", "")
    cor = str(item.get("cor", ""))
    if chave_preco == "entremeio":
        return f"entremeio_{cor}" if cor else chave_preco
    if chave_preco == "entremeio_2lados":
        return f"entremeio_2lados_{cor}" if cor else chave_preco
    if chave_preco == "medalha_2lados":
        tamanho = str(item.get("tamanho", ""))
        return f"medalha_2lados_{tamanho}_{cor}" if tamanho and cor else chave_preco
    return chave_preco


def _codigo_estoque_tiny(item: dict) -> str:
    chave = _chave_material(item)
    return _CODIGO_MATERIAL_TINY.get(chave, chave)


def _descricao_estoque_tiny(item: dict) -> str:
    chave = _chave_material(item)
    return _DESCRICAO_MATERIAL_TINY.get(chave, chave)


def _primeiro_registro(registros_bruto) -> dict:
    """`retorno.registros` da Tiny vem ora como lista (`[{"registro": {...}}]`),
    ora como um unico objeto (`{"registro": {...}}`) -- confirmado na
    pratica com pedido de teste real, tanto em resposta de sucesso
    quanto de erro (duplicidade). Sem tratar os dois formatos,
    `registros[0]` quebra com KeyError quando vem objeto, derrubando o
    endpoint que chamou isso (ver app.py:admin_pedido_reenviar_tiny --
    foi exatamente esse crash que apareceu como Internal Server Error
    pro usuario, mesmo com a Tiny tendo processado o pedido certinho)."""
    if isinstance(registros_bruto, dict):
        primeiro = registros_bruto
    elif isinstance(registros_bruto, list) and registros_bruto and isinstance(registros_bruto[0], dict):
        primeiro = registros_bruto[0]
    else:
        primeiro = {}
    registro = primeiro.get("registro")
    return registro if isinstance(registro, dict) else {}


def _itens_para_tiny(itens: list[dict]) -> list[dict]:
    return [
        {
            "item": {
                "codigo": _codigo_estoque_tiny(item),
                "descricao": _descricao_estoque_tiny(item),
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

    # Endereco de entrega DIFERENTE do endereco do cliente (ver
    # conversa/services.pedidos._COLUNAS_ADICIONAIS) -- so manda esse
    # bloco quando o cliente realmente preencheu um endereco de entrega
    # separado no checkout (ver app.py:_endereco_valido). NAO
    # CONFIRMADO ainda com pedido de teste real (diferente de
    # forma_pagamento/frete_por_conta, ja confirmados -- ver topo do
    # arquivo): nome_destinatario/endereco/numero/complemento/bairro/
    # cep/cidade/uf ja CONFIRMADOS com pedido de teste real -- a Tiny
    # mostrou o destinatario certinho na nota (ver conversa). "cpf_cnpj"
    # foi adicionado depois, seguindo o mesmo padrao ja confirmado no
    # bloco `cliente` (_cliente_para_tiny) -- AINDA NAO confirmado com
    # pedido de teste real especificamente esse campo (antes disso o
    # documento do destinatario so ia pro texto livre da observacao
    # "Entregar aos cuidados de" acima, nunca campo estruturado -- por
    # isso aparecia so nas observacoes/nota, nunca no campo de CPF
    # proprio da Tiny, ver conversa). "fone" aqui e´ o telefone de quem
    # RECEBE (destinatario), quando preenchido no checkout -- opcional,
    # so pra transportadora/Tiny conseguirem contato se precisar (ver
    # endereco_destinatario_telefone em services.pedidos). Tambem AINDA
    # NAO confirmado com pedido de teste real, mesmo criterio acima.
    if pedido.get("endereco_destinatario_logradouro"):
        corpo_pedido["endereco_entrega"] = {
            "nome_destinatario": pedido.get("endereco_destinatario_nome", ""),
            "cpf_cnpj": pedido.get("endereco_destinatario_documento", ""),
            "endereco": pedido.get("endereco_destinatario_logradouro", ""),
            "numero": pedido.get("endereco_destinatario_numero", ""),
            "complemento": pedido.get("endereco_destinatario_complemento", ""),
            "bairro": pedido.get("endereco_destinatario_bairro", ""),
            "cep": pedido.get("endereco_destinatario_cep", ""),
            "cidade": pedido.get("endereco_destinatario_cidade", ""),
            "uf": pedido.get("endereco_destinatario_uf", ""),
        }
        if pedido.get("endereco_destinatario_telefone"):
            corpo_pedido["endereco_entrega"]["fone"] = pedido["endereco_destinatario_telefone"]

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
    primeiro_registro = _primeiro_registro(retorno.get("registros"))
    if retorno.get("status") != "OK":
        erros = retorno.get("erros") or primeiro_registro.get("erros", [])
        mensagens = [e.get("erro", "") for e in erros] if erros else ["erro desconhecido"]
        return {"erro": "; ".join(m for m in mensagens if m) or "erro desconhecido"}

    return {"ok": True, "numero": primeiro_registro.get("numero"), "id": primeiro_registro.get("id")}


def buscar_contatos_tiny(termo: str) -> dict:
    """Busca contatos ja cadastrados na Tiny por nome/razao social/CPF-
    CNPJ (ver app.py:admin_tiny_buscar_contato) -- usado no painel pra
    aproveitar o endereco de uma livraria que ja fecha pedido com
    regularidade, sem redigitar tudo na mao toda vez (ver conversa).

    NAO CONFIRMADO ainda com busca real (mesmo aviso do topo do
    arquivo sobre o ambiente de desenvolvimento nao alcancar
    tiny.com.br direto) -- nomes de campo seguindo a documentacao
    publica da API 2.0 (contatos.pesquisa.php). Se a Tiny devolver algo
    fora desse formato, cai no `except`/campos vazios abaixo em vez de
    quebrar a busca.

    Devolve {"ok": True, "contatos": [...]} (lista pode vir vazia) ou
    {"erro": "..."}."""
    if not TINY_API_TOKEN:
        return {"erro": "Sincronização com a Tiny não configurada (falta TINY_API_TOKEN)."}
    termo = termo.strip()
    if not termo:
        return {"ok": True, "contatos": []}

    try:
        resposta = requests.get(
            BUSCA_CONTATOS_URL,
            params={"token": TINY_API_TOKEN, "formato": "json", "pesquisa": termo},
            timeout=15,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except requests.RequestException as exc:
        return {"erro": f"Não foi possível buscar na Tiny agora ({exc})."}
    except ValueError:
        return {"erro": "Resposta inválida da Tiny."}

    retorno = dados.get("retorno", {})
    if retorno.get("status") != "OK":
        # Tiny devolve status "Erro" tambem pra "nenhum contato encontrado"
        # (nao e´ so falha de verdade) -- trata como lista vazia em vez
        # de mostrar erro pro operador numa busca que so nao achou nada.
        erros = retorno.get("erros") or []
        mensagens = " ".join(str(e.get("erro", "")) for e in erros).lower()
        if "nenhum registro" in mensagens or not erros:
            return {"ok": True, "contatos": []}
        mensagens_lista = [e.get("erro", "") for e in erros]
        return {"erro": "; ".join(m for m in mensagens_lista if m) or "erro desconhecido"}

    contatos_brutos = retorno.get("contatos") or []
    if not isinstance(contatos_brutos, list):
        contatos_brutos = [contatos_brutos]
    contatos = []
    for item in contatos_brutos:
        contato = item.get("contato") if isinstance(item, dict) else None
        if not isinstance(contato, dict):
            continue
        contatos.append(
            {
                "nome": contato.get("nome", ""),
                "tipo_pessoa": _TIPO_PESSOA_TINY_PARA_SITE.get(contato.get("tipo_pessoa"), "fisica"),
                "documento": contato.get("cpf_cnpj", ""),
                "telefone": contato.get("fone", ""),
                "email": contato.get("email", ""),
                "cep": contato.get("cep", ""),
                "logradouro": contato.get("endereco", ""),
                "numero": contato.get("numero", ""),
                "complemento": contato.get("complemento", ""),
                "bairro": contato.get("bairro", ""),
                "cidade": contato.get("cidade", ""),
                "uf": contato.get("uf", ""),
            }
        )
    return {"ok": True, "contatos": contatos}
