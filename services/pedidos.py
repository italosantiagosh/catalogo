"""
Persistencia de pedidos pagos via InfinitePay -- ver services/infinitepay.py
e app.py (/api/pedido/criar, /webhook/infinitepay, /pedido/<token>).

Usa SQLite (biblioteca padrao, sem dependencia nova) -- guarda o pedido
assim que o cliente clica em "Pagar agora" (status "pendente") e marca
como "pago" quando o webhook da InfinitePay confirma o pagamento.

IMPORTANTE (producao/Render): por padrao o arquivo fica em
data/pedidos.db, no mesmo disco da aplicacao -- se esse disco NAO for
persistente (padrao do Render pra web services), o banco e apagado a
cada redeploy/restart e os pedidos "somem", quebrando a pagina de
acompanhamento de pedidos ja pagos. Configure um Persistent Disk no
Render e aponte PEDIDOS_DB_PATH pra um caminho dentro dele antes de
depender disso pra pedidos de verdade.

O token usado na URL de acompanhamento (/pedido/<token>) e´ longo e
aleatorio (secrets.token_urlsafe) de proposito -- e´ diferente do codigo
curto de 6 caracteres (so pra referencia humana, ja usado no WhatsApp
via carrinho.js) porque esse token vira uma URL que mostra dados
pessoais do cliente: um codigo curto seria adivinhavel por forca bruta.
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = os.environ.get(
    "PEDIDOS_DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "pedidos.db")
)

# Mesmo criterio do codigo curto gerado no navegador (carrinho.js:
# PEDIDO_ID_CHARSET) -- sem O/0, I/1, evita confusao ao ler em voz alta.
_CODIGO_CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _gerar_codigo() -> str:
    return "".join(secrets.choice(_CODIGO_CHARSET) for _ in range(6))


@contextmanager
def _conexao():
    conexao = sqlite3.connect(DB_PATH)
    conexao.row_factory = sqlite3.Row
    try:
        yield conexao
        conexao.commit()
    finally:
        conexao.close()


# Colunas adicionadas depois da criacao original da tabela -- "CREATE
# TABLE IF NOT EXISTS" sozinho NAO adiciona coluna nova a um banco que
# ja existe em disco (so cria do zero se o arquivo nao existir ainda).
# Qualquer coluna nova a partir de agora entra aqui, nunca direto no
# CREATE TABLE abaixo, senao quebra (sqlite3.OperationalError: no such
# column) pra quem ja tem o pedidos.db criado em producao.
_COLUNAS_ADICIONAIS: list[tuple[str, str]] = [
    ("tiny_sincronizado", "INTEGER NOT NULL DEFAULT 0"),
    ("tiny_numero_pedido", "TEXT"),
    ("tiny_erro", "TEXT"),
    ("email_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_erro", "TEXT"),
    ("endereco_destinatario_nome", "TEXT"),
    ("endereco_destinatario_tipo_pessoa", "TEXT"),
    ("endereco_destinatario_documento", "TEXT"),
    ("email_pedido_criado_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_pedido_criado_erro", "TEXT"),
    ("email_lembrete_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_lembrete_erro", "TEXT"),
    ("codigo_rastreio", "TEXT"),
    ("link_rastreio", "TEXT"),
    ("faturado_em", "TEXT"),
    ("enviado_em", "TEXT"),
    ("entregue_em", "TEXT"),
    ("transportadora", "TEXT"),
    ("email_lembrete_enviado_em", "TEXT"),
    ("cancelado_em", "TEXT"),
    ("email_cancelado_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_cancelado_erro", "TEXT"),
]

# Fluxo de status depois de "pago" -- alteravel manualmente pelo painel
# (/admin/pedidos/<token>, ver app.py) e pensado pra tambem poder ser
# disparado automaticamente pela Tiny mais pra frente (webhook de
# situacao/rastreio/NF-e, deixado pra depois -- ver conversa). Os dois
# caminhos (manual e futuro automatico) devem chamar a MESMA
# atualizar_status abaixo, nunca duplicar essa logica em outro lugar.
STATUS_VALIDOS = ("pago", "faturado", "enviado", "entregue")


def inicializar_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _conexao() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos (
                token TEXT PRIMARY KEY,
                codigo TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                itens TEXT NOT NULL,
                subtotal REAL NOT NULL,
                frete_descricao TEXT,
                frete_preco REAL NOT NULL DEFAULT 0,
                total REAL NOT NULL,
                cliente_nome TEXT,
                cliente_tipo_pessoa TEXT,
                cliente_documento TEXT,
                cliente_telefone TEXT,
                cliente_email TEXT,
                endereco_cep TEXT,
                endereco_logradouro TEXT,
                endereco_numero TEXT,
                endereco_complemento TEXT,
                endereco_bairro TEXT,
                endereco_cidade TEXT,
                endereco_uf TEXT,
                forma_pagamento TEXT,
                parcelas INTEGER,
                valor_pago REAL,
                transaction_nsu TEXT,
                criado_em TEXT NOT NULL,
                pago_em TEXT
            )
            """
        )
        colunas_existentes = {linha[1] for linha in conexao.execute("PRAGMA table_info(pedidos)").fetchall()}
        for nome, tipo_sql in _COLUNAS_ADICIONAIS:
            if nome not in colunas_existentes:
                conexao.execute(f"ALTER TABLE pedidos ADD COLUMN {nome} {tipo_sql}")


def criar_pedido(
    *,
    itens: list[dict],
    subtotal: float,
    frete_descricao: str,
    frete_preco: float,
    cliente: dict,
    endereco: dict,
) -> dict:
    inicializar_db()
    token = secrets.token_urlsafe(24)
    codigo = _gerar_codigo()
    total = round(subtotal + frete_preco, 2)
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            """
            INSERT INTO pedidos (
                token, codigo, status, itens, subtotal, frete_descricao, frete_preco, total,
                cliente_nome, cliente_tipo_pessoa, cliente_documento, cliente_telefone, cliente_email,
                endereco_cep, endereco_logradouro, endereco_numero, endereco_complemento,
                endereco_bairro, endereco_cidade, endereco_uf,
                endereco_destinatario_nome, endereco_destinatario_tipo_pessoa, endereco_destinatario_documento,
                criado_em
            ) VALUES (?, ?, 'pendente', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                token,
                codigo,
                json.dumps(itens),
                subtotal,
                frete_descricao,
                frete_preco,
                total,
                cliente.get("nome", ""),
                cliente.get("tipo_pessoa", ""),
                cliente.get("documento", ""),
                cliente.get("telefone", ""),
                cliente.get("email", ""),
                endereco.get("cep", ""),
                endereco.get("logradouro", ""),
                endereco.get("numero", ""),
                endereco.get("complemento", ""),
                endereco.get("bairro", ""),
                endereco.get("cidade", ""),
                endereco.get("uf", ""),
                endereco.get("destinatario_nome", ""),
                endereco.get("destinatario_tipo_pessoa", ""),
                endereco.get("destinatario_documento", ""),
                agora,
            ),
        )
    return obter_pedido(token)


def listar_pedidos(*, status: str | None = None, limite: int = 200) -> list[dict]:
    """Usado pelo painel interno (/admin/pedidos, ver app.py) -- mais
    recentes primeiro."""
    inicializar_db()
    consulta = "SELECT * FROM pedidos"
    parametros: tuple = ()
    if status:
        consulta += " WHERE status = ?"
        parametros = (status,)
    consulta += " ORDER BY criado_em DESC LIMIT ?"
    parametros = parametros + (limite,)
    with _conexao() as conexao:
        linhas = conexao.execute(consulta, parametros).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def listar_pedidos_pendentes_para_lembrete(minutos: int) -> list[dict]:
    """Pedidos "pendente" ha´ pelo menos `minutos`, que ainda nao
    receberam o lembrete de pagamento -- usado pelo job agendado em
    app.py (ver services/email.py:enviar_lembrete_pedido_pendente)."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
    with _conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT * FROM pedidos
            WHERE status = 'pendente' AND email_lembrete_enviado = 0 AND criado_em <= ?
            ORDER BY criado_em ASC
            """,
            (limite,),
        ).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def listar_pedidos_pendentes_para_cancelar(minutos: int) -> list[dict]:
    """Pedidos "pendente" que ja receberam o lembrete (2o link) ha´ pelo
    menos `minutos` e continuam sem pagar -- usado pelo job agendado em
    app.py (ver services.pedidos.cancelar_pedido e
    services/email.py:enviar_pedido_cancelado). O corte usa
    email_lembrete_enviado_em (quando o lembrete foi TENTADO, com ou
    sem sucesso) em vez de exigir entrega confirmada do e-mail --
    assim um pedido nao fica "pendente" pra sempre so porque o envio
    do lembrete falhou."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
    with _conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT * FROM pedidos
            WHERE status = 'pendente' AND email_lembrete_enviado = 1
                AND email_cancelado_enviado = 0 AND email_lembrete_enviado_em <= ?
            ORDER BY email_lembrete_enviado_em ASC
            """,
            (limite,),
        ).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def obter_pedido(token: str) -> dict | None:
    inicializar_db()
    with _conexao() as conexao:
        linha = conexao.execute("SELECT * FROM pedidos WHERE token = ?", (token,)).fetchone()
    if linha is None:
        return None
    pedido = dict(linha)
    pedido["itens"] = json.loads(pedido["itens"])
    return pedido


def marcar_pago(
    token: str, *, forma_pagamento: str, parcelas: int | None, valor_pago: float, transaction_nsu: str
) -> dict | None:
    """Idempotente -- se o pedido ja estiver 'pago' (webhook repetido, comum
    em integracoes de pagamento), so devolve o pedido sem reprocessar."""
    pedido = obter_pedido(token)
    if pedido is None or pedido["status"] == "pago":
        return pedido
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            """
            UPDATE pedidos SET status = 'pago', forma_pagamento = ?, parcelas = ?,
                valor_pago = ?, transaction_nsu = ?, pago_em = ?
            WHERE token = ?
            """,
            (forma_pagamento, parcelas, valor_pago, transaction_nsu, agora, token),
        )
    return obter_pedido(token)


def atualizar_status(
    token: str,
    novo_status: str,
    *,
    codigo_rastreio: str | None = None,
    link_rastreio: str | None = None,
    transportadora: str | None = None,
) -> dict | None:
    """Avanca o status manualmente (painel admin) ou automaticamente
    (futuro webhook da Tiny) -- as duas origens devem usar essa mesma
    funcao, nunca duplicar a logica. `codigo_rastreio`/`link_rastreio`/
    `transportadora` so fazem sentido pra novo_status="enviado" (ver
    app.py, que dispara o e-mail de "pedido enviado" so quando
    codigo_rastreio/link_rastreio vierem preenchidos)."""
    if novo_status not in STATUS_VALIDOS:
        return None
    pedido = obter_pedido(token)
    if pedido is None:
        return None
    agora = datetime.now(timezone.utc).isoformat()
    coluna_data = {"faturado": "faturado_em", "enviado": "enviado_em", "entregue": "entregue_em"}.get(novo_status)
    with _conexao() as conexao:
        if coluna_data:
            conexao.execute(
                f"""
                UPDATE pedidos SET status = ?, {coluna_data} = ?,
                    codigo_rastreio = COALESCE(?, codigo_rastreio), link_rastreio = COALESCE(?, link_rastreio),
                    transportadora = COALESCE(?, transportadora)
                WHERE token = ?
                """,
                (novo_status, agora, codigo_rastreio, link_rastreio, transportadora, token),
            )
        else:
            conexao.execute("UPDATE pedidos SET status = ? WHERE token = ?", (novo_status, token))
    return obter_pedido(token)


def marcar_email_enviado(token: str, *, erro: str | None) -> dict | None:
    """E-mail de PAGAMENTO CONFIRMADO -- mesma logica do
    marcar_tiny_sincronizado (ver abaixo), evita reenviar em webhook
    duplicado. Ver marcar_email_pedido_criado_enviado pro e-mail
    disparado na CRIACAO do pedido (com o link de pagamento)."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_enviado = 1, email_erro = ? WHERE token = ?", (erro, token)
        )
    return obter_pedido(token)


def marcar_email_pedido_criado_enviado(token: str, *, erro: str | None) -> dict | None:
    """E-mail com o link de pagamento, disparado assim que o pedido e´
    criado (ver app.py:api_pedido_criar) -- diferente do
    marcar_email_enviado acima (esse e´ o de pagamento confirmado)."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_pedido_criado_enviado = 1, email_pedido_criado_erro = ? WHERE token = ?",
            (erro, token),
        )
    return obter_pedido(token)


def marcar_email_lembrete_enviado(token: str, *, erro: str | None) -> dict | None:
    """E-mail de lembrete pra pedido pendente ha´ muito tempo sem pagar
    (ver listar_pedidos_pendentes_para_lembrete acima) -- garante que
    o job agendado so manda esse lembrete uma vez por pedido. Tambem
    grava email_lembrete_enviado_em (mesmo quando `erro` vem
    preenchido), usado por listar_pedidos_pendentes_para_cancelar pra
    contar os minutos ate´ o cancelamento automatico."""
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            """
            UPDATE pedidos SET email_lembrete_enviado = 1, email_lembrete_erro = ?,
                email_lembrete_enviado_em = ?
            WHERE token = ?
            """,
            (erro, agora, token),
        )
    return obter_pedido(token)


def cancelar_pedido(token: str) -> dict | None:
    """Cancela um pedido ainda "pendente" (abandonado apos o lembrete --
    ver listar_pedidos_pendentes_para_cancelar e app.py). Idempotente:
    se o pedido ja nao estiver mais "pendente" (por exemplo, o cliente
    pagou entre o job rodar e o cancelamento ser processado), nao faz
    nada e devolve o pedido como esta´."""
    pedido = obter_pedido(token)
    if pedido is None or pedido["status"] != "pendente":
        return pedido
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET status = 'cancelado', cancelado_em = ? WHERE token = ?",
            (agora, token),
        )
    return obter_pedido(token)


def marcar_email_cancelado_enviado(token: str, *, erro: str | None) -> dict | None:
    """E-mail motivacional de recuperacao, disparado quando o pedido e´
    cancelado automaticamente (ver cancelar_pedido acima) -- garante
    que o job agendado so manda esse e-mail uma vez por pedido."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_cancelado_enviado = 1, email_cancelado_erro = ? WHERE token = ?",
            (erro, token),
        )
    return obter_pedido(token)


def marcar_tiny_sincronizado(token: str, *, numero_pedido: str | None, erro: str | None) -> dict | None:
    """Registra o resultado da tentativa de sincronizar com a Tiny (ver
    services/tiny.py) -- so pra evitar reenviar o mesmo pedido pra Tiny
    a cada webhook repetido (a InfinitePay pode reenviar). `erro` fica
    guardado pra dar pra conferir manualmente quais pedidos falharam
    a sincronizacao, mesmo sem reprocessar automaticamente."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET tiny_sincronizado = 1, tiny_numero_pedido = ?, tiny_erro = ? WHERE token = ?",
            (numero_pedido, erro, token),
        )
    return obter_pedido(token)
