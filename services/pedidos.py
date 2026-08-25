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
from datetime import datetime, timezone
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
                endereco_destinatario TEXT,
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
                endereco_cep, endereco_destinatario, endereco_logradouro, endereco_numero,
                endereco_complemento, endereco_bairro, endereco_cidade, endereco_uf, criado_em
            ) VALUES (?, ?, 'pendente', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                endereco.get("destinatario", ""),
                endereco.get("logradouro", ""),
                endereco.get("numero", ""),
                endereco.get("complemento", ""),
                endereco.get("bairro", ""),
                endereco.get("cidade", ""),
                endereco.get("uf", ""),
                agora,
            ),
        )
    return obter_pedido(token)


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
