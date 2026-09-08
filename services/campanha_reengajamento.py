"""
Campanha pontual de reengajamento pra quem comprou no sistema antigo
(planilhas exportadas do Tiny, ver conversa "campanha pra contatos
antigos") -- convida pro site novo e pede avaliacao (ver
services/email.py:enviar_reengajamento_contato_antigo).

Fluxo, tudo pelo painel admin (ver app.py, /admin/campanha-antigos):
1. O admin sobe a(s) planilha(s) uma vez (importar_contatos abaixo) --
   dedupica por e-mail entre elas e ignora quem ja´ tem pedido no site
   novo (pedidos.cliente_email, MESMO banco). O resto entra como
   "pendente".
2. O envio de verdade acontece em lotes manuais (listar_pendentes +
   marcar_enviado, chamados por app.py um e-mail de cada vez), N por
   clique -- pra nao estourar o limite diario da Brevo, que tambem
   atende os e-mails transacionais normais do site (confirmacao de
   pedido, etc). Reimportar a MESMA planilha depois nao duplica nem
   reseta quem ja´ foi processado (INSERT OR IGNORE por e-mail).

Mesmo banco/mesma variavel de ambiente de services/pedidos.py -- nao
faz sentido um Persistent Disk separado so pra essa tabela.
"""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from services.pedidos import inicializar_db as _inicializar_db_pedidos

DB_PATH = os.environ.get(
    "PEDIDOS_DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "pedidos.db")
)

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
            CREATE TABLE IF NOT EXISTS campanha_contatos_antigos (
                email TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendente',
                erro TEXT,
                criado_em TEXT NOT NULL,
                enviado_em TEXT
            )
            """
        )


def email_valido(email: str) -> bool:
    return bool(_EMAIL_REGEX.match((email or "").strip()))


def importar_contatos(contatos: list[dict]) -> dict:
    """Recebe [{"nome", "email"}, ...] ja´ lido da(s) planilha(s) (ver
    app.py:admin_campanha_importar) -- dedupica por e-mail (minusculo,
    ultima ocorrencia ganha), ignora e-mail invalido/vazio, e ignora
    quem ja´ tem pelo menos 1 pedido no site novo (cruza direto com a
    tabela `pedidos`, MESMO arquivo sqlite). O resto vira "pendente".
    Devolve contagem de cada situacao pra mostrar no painel."""
    inicializar_db()
    _inicializar_db_pedidos()  # garante que a tabela `pedidos` existe antes do cruzamento abaixo

    validos: dict[str, str] = {}
    invalidos = 0
    for contato in contatos:
        email = (contato.get("email") or "").strip().lower()
        nome = (contato.get("nome") or "").strip()
        if not email_valido(email):
            invalidos += 1
            continue
        validos[email] = nome

    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        ja_e_cliente_site_novo = {
            (linha[0] or "").strip().lower()
            for linha in conexao.execute("SELECT DISTINCT cliente_email FROM pedidos")
        }
        novos_candidatos = 0
        ja_e_cliente = 0
        for email, nome in validos.items():
            if email in ja_e_cliente_site_novo:
                ja_e_cliente += 1
                continue
            cursor = conexao.execute(
                "INSERT OR IGNORE INTO campanha_contatos_antigos (email, nome, status, criado_em) "
                "VALUES (?, ?, 'pendente', ?)",
                (email, nome, agora),
            )
            if cursor.rowcount:
                novos_candidatos += 1

    return {
        "recebidos": len(contatos),
        "invalidos": invalidos,
        "unicos": len(validos),
        "ja_e_cliente_site_novo": ja_e_cliente,
        "novos_candidatos": novos_candidatos,
    }


def contagem_por_status() -> dict:
    inicializar_db()
    with _conexao() as conexao:
        linhas = conexao.execute(
            "SELECT status, COUNT(*) AS total FROM campanha_contatos_antigos GROUP BY status"
        ).fetchall()
    contagem = {"pendente": 0, "enviado": 0, "erro": 0}
    contagem.update({linha["status"]: linha["total"] for linha in linhas})
    return contagem


def listar_pendentes(limite: int) -> list[dict]:
    inicializar_db()
    with _conexao() as conexao:
        linhas = conexao.execute(
            "SELECT email, nome FROM campanha_contatos_antigos WHERE status = 'pendente' "
            "ORDER BY criado_em LIMIT ?",
            (limite,),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def listar_todos() -> list[dict]:
    """Lista completa (email, nome, status, criado_em, enviado_em, erro)
    -- pra exportar em CSV (ver app.py:admin_campanha_exportar_csv) e o
    admin conseguir conferir pendente/enviado/erro de fora do painel,
    ex: cruzando com outra planilha pra achar duplicata por CPF que o
    sistema (que so compara e-mail) nao teria como enxergar sozinho."""
    inicializar_db()
    with _conexao() as conexao:
        linhas = conexao.execute(
            "SELECT email, nome, status, criado_em, enviado_em, erro FROM campanha_contatos_antigos "
            "ORDER BY criado_em"
        ).fetchall()
    return [dict(linha) for linha in linhas]


def marcar_enviado(email: str, *, erro: str | None) -> None:
    inicializar_db()
    agora = datetime.now(timezone.utc).isoformat()
    status = "erro" if erro else "enviado"
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE campanha_contatos_antigos SET status = ?, erro = ?, enviado_em = ? WHERE email = ?",
            (status, erro, agora, email),
        )
