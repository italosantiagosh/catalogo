"""
Avaliacoes de clientes por produto (santo/devocao) -- ver app.py
(/api/avaliacoes, /admin/avaliacoes, templates/produto.html).

Guardadas por PRODUTO (santo), nao por formato -- medalha, entremeio e
chaveiro do mesmo santo aparecem todos na mesma pagina de produto (ver
conversa), entao a avaliacao tambem fica junto; o formato comprado vira
so uma etiqueta na propria avaliacao ("comprou: Chaveiro"), sem
duplicar estrutura. Se no futuro entrar um tipo de produto novo
(fora do catalogo atual de santos), essas avaliacoes passam a ser
naturalmente separadas, ja que tem produto_id proprio.

Moderacao: toda avaliacao enviada pelo site nasce "pendente" -- so
aparece pro publico (e entra no schema.org Review/AggregateRating,
ver app.py:produto) depois de aprovada manualmente no painel admin.
Evita spam, foto errada ou review falsa exposta sem revisao.

Mesmo padrao de SQLite usado em services/pedidos.py -- ver o aviso la´
sobre Persistent Disk no Render (essa tabela tem o mesmo risco de ser
apagada num redeploy se o disco nao for persistente).
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# Mesmo banco/mesma variavel de ambiente de services/pedidos.py -- nao
# faz sentido um Persistent Disk separado so pra essa tabela nova.
DB_PATH = os.environ.get(
    "PEDIDOS_DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "pedidos.db")
)

STATUS_VALIDOS = ("pendente", "aprovada", "recusada")


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
            CREATE TABLE IF NOT EXISTS avaliacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id TEXT NOT NULL,
                formato TEXT,
                nome_cliente TEXT NOT NULL,
                nota INTEGER NOT NULL,
                texto TEXT,
                foto TEXT,
                status TEXT NOT NULL DEFAULT 'pendente',
                criado_em TEXT NOT NULL
            )
            """
        )
        conexao.execute("CREATE INDEX IF NOT EXISTS idx_avaliacoes_produto ON avaliacoes (produto_id, status)")


def criar_avaliacao(
    *, produto_id: str, formato: str, nome_cliente: str, nota: int, texto: str, foto: str
) -> dict:
    inicializar_db()
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO avaliacoes (produto_id, formato, nome_cliente, nota, texto, foto, status, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, 'pendente', ?)
            """,
            (produto_id, formato, nome_cliente, nota, texto, foto, agora),
        )
        novo_id = cursor.lastrowid
    return obter_avaliacao(novo_id)


def obter_avaliacao(id_: int) -> dict | None:
    inicializar_db()
    with _conexao() as conexao:
        linha = conexao.execute("SELECT * FROM avaliacoes WHERE id = ?", (id_,)).fetchone()
    return dict(linha) if linha else None


def listar_avaliacoes(*, status: str | None = None, limite: int = 200) -> list[dict]:
    """Usado pelo painel admin -- mais recentes primeiro."""
    inicializar_db()
    consulta = "SELECT * FROM avaliacoes"
    parametros: tuple = ()
    if status:
        consulta += " WHERE status = ?"
        parametros = (status,)
    consulta += " ORDER BY criado_em DESC LIMIT ?"
    parametros = parametros + (limite,)
    with _conexao() as conexao:
        linhas = conexao.execute(consulta, parametros).fetchall()
    return [dict(linha) for linha in linhas]


def listar_avaliacoes_aprovadas(produto_id: str) -> list[dict]:
    """Usado na pagina publica do produto -- so o que ja passou por
    aprovacao manual, mais recentes primeiro."""
    inicializar_db()
    with _conexao() as conexao:
        linhas = conexao.execute(
            "SELECT * FROM avaliacoes WHERE produto_id = ? AND status = 'aprovada' ORDER BY criado_em DESC",
            (produto_id,),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def media_e_total_aprovadas(produto_id: str) -> tuple[float | None, int]:
    """(media, total) das avaliacoes aprovadas desse produto -- usado pro
    resumo na pagina e pro AggregateRating (ver app.py:produto).
    Devolve (None, 0) se ainda nao ha´ nenhuma aprovada."""
    inicializar_db()
    with _conexao() as conexao:
        linha = conexao.execute(
            "SELECT AVG(nota) AS media, COUNT(*) AS total FROM avaliacoes WHERE produto_id = ? AND status = 'aprovada'",
            (produto_id,),
        ).fetchone()
    total = linha["total"] or 0
    media = round(linha["media"], 1) if linha["media"] is not None else None
    return media, total


def atualizar_status(id_: int, novo_status: str) -> dict | None:
    if novo_status not in ("aprovada", "recusada"):
        return None
    if obter_avaliacao(id_) is None:
        return None
    with _conexao() as conexao:
        conexao.execute("UPDATE avaliacoes SET status = ? WHERE id = ?", (novo_status, id_))
    return obter_avaliacao(id_)
