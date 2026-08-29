"""
Guarda de forma DURAVEL (SQLite, sobrevive a reinicio/varios dias) a
previa com moldura e o recorte 1:1 gerados em /api/personalizada/preview
(ver app.py) -- referenciados por um token curto em vez do data URI
inteiro.

Por que isso existe: ate essa mudanca, o carrinho (localStorage, sem
backend) guardava o proprio data URI em base64 de CADA imagem
personalizada (previa + recorte, os dois em resolucao real de producao)
-- estourava a cota do localStorage (tipicamente 5-10MB por origem) ja
na 3a medalha personalizada com foto, travando o "adicionar ao
carrinho" sem nenhum aviso (ver conversa, bug real reportado). Agora o
carrinho guarda so a URL curta (/imagem-personalizada/<token>, ver
app.py) -- a imagem de verdade fica aqui, e o navegador so precisa dela
de novo quando renderiza o <img> ou quando o admin baixa.

Diferente do `_downloads` em memoria de app.py (usado pelos botoes
"baixar previa/recorte" DENTRO da propria pagina /personalizada): este
aqui e MULTI-leitura (nao apaga depois de servido, precisa continuar
existindo pro carrinho/pedido por dias) e DURAVEL (sobrevive restart,
carrinho pode ficar dias no localStorage do cliente antes de finalizar
a compra).

Mesmo banco/mesma variavel de ambiente de services/pedidos.py -- nao
faz sentido um Persistent Disk separado so pra essa tabela nova (mesmo
raciocinio ja usado em services/push.py).
"""

from __future__ import annotations

import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = os.environ.get(
    "PEDIDOS_DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "pedidos.db")
)


@contextmanager
def _conexao():
    # timeout=30 + WAL -- ver mesmo comentario em services/pedidos.py
    # (mesmo banco, mesmo risco de "database is locked" com escrita
    # concorrente).
    conexao = sqlite3.connect(DB_PATH, timeout=30)
    conexao.execute("PRAGMA journal_mode=WAL")
    conexao.row_factory = sqlite3.Row
    try:
        yield conexao
        conexao.commit()
    finally:
        conexao.close()


def inicializar_db() -> None:
    with _conexao() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS imagens_personalizadas (
                token TEXT PRIMARY KEY,
                dados BLOB NOT NULL,
                mimetype TEXT NOT NULL,
                nome_arquivo TEXT NOT NULL,
                criado_em TEXT NOT NULL,
                usada_em_pedido INTEGER NOT NULL DEFAULT 0
            )
            """
        )


def salvar_imagem(dados: bytes, mimetype: str, nome_arquivo: str) -> str:
    inicializar_db()
    token = secrets.token_urlsafe(16)
    with _conexao() as conexao:
        conexao.execute(
            "INSERT INTO imagens_personalizadas (token, dados, mimetype, nome_arquivo, criado_em) "
            "VALUES (?, ?, ?, ?, ?)",
            (token, dados, mimetype, nome_arquivo, datetime.now(timezone.utc).isoformat()),
        )
    return token


def obter_imagem(token: str) -> tuple[bytes, str, str] | None:
    inicializar_db()
    with _conexao() as conexao:
        linha = conexao.execute(
            "SELECT dados, mimetype, nome_arquivo FROM imagens_personalizadas WHERE token = ?", (token,)
        ).fetchone()
    return (linha["dados"], linha["mimetype"], linha["nome_arquivo"]) if linha else None


def marcar_imagem_usada(token: str) -> None:
    """Chamado quando um pedido de verdade referencia esse token (ver
    app.py:criar_pedido/_marcar_imagens_personalizadas_usadas) -- protege
    a imagem de ser apagada por purgar_imagens_antigas, mesmo que fique
    muito tempo parada ate o pedido ser pago/cancelado."""
    inicializar_db()
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE imagens_personalizadas SET usada_em_pedido = 1 WHERE token = ?", (token,)
        )


def purgar_imagens_antigas(dias: int = 7) -> int:
    """Remove simulacoes geradas mas nunca adicionadas a um pedido de
    verdade (usada_em_pedido = 0) depois de `dias` dias -- evita o banco
    crescer sem limite com fotos de gente que so testou a simulacao e
    nunca comprou. Devolve quantas linhas foram removidas."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with _conexao() as conexao:
        cursor = conexao.execute(
            "DELETE FROM imagens_personalizadas WHERE usada_em_pedido = 0 AND criado_em < ?", (limite,)
        )
        return cursor.rowcount
