"""
Carrinho montado na mao pelo dono a partir de um pedido fechado por
fora do site (WhatsApp, telefone etc) -- ver conversa 2026-09-24:
precisava de um jeito de montar um carrinho de atacado grande (varias
dezenas de itens) e mandar um link curto pra abrir ja pronto.

Por que uma tabela separada, e nao reaproveitar carrinhos_abandonados
(que ja tem token + itens + `/carrinho?restaurar=` funcionando): aquela
tabela tem um job agendado que manda lembrete por e-mail pra quem tem
e-mail salvo (ver app.py:_enviar_lembretes_carrinhos_abandonados) -- um
carrinho montado aqui nao tem cliente nenhum, so o dono confirmando um
pedido que ja fechou por fora. Iria precisar forcar email/telefone
vazios pra nao arriscar disparar um lembrete pra contato nenhum/errado,
e ainda assim ia misturar com o painel de carrinhos abandonados (que e´
uma lista de LEADS de cliente de verdade, nao pedidos ja fechados).
Tabela e fluxo proprios evitam os dois problemas de uma vez.

Sem job nenhum olhando essa tabela -- token so serve pra montar o link
uma vez, sem prazo de expiracao.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# Mesmo arquivo/padrao de services/pedidos.py, services/avaliacoes.py
# e services/carrinhos_abandonados.py -- cada modulo define a propria
# constante (em vez de importar de outro) pra nao ficar com uma
# referencia presa no valor de import, o que quebraria monkeypatch nos
# testes.
DB_PATH = os.environ.get(
    "PEDIDOS_DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "pedidos.db")
)


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
            CREATE TABLE IF NOT EXISTS carrinhos_manuais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                itens TEXT NOT NULL,
                subtotal REAL NOT NULL,
                criado_em TEXT NOT NULL
            )
            """
        )


def salvar(*, token: str, itens: list[dict], subtotal: float) -> dict:
    inicializar_db()
    agora = datetime.now(timezone.utc).isoformat()
    itens_json = json.dumps(itens, ensure_ascii=False)
    with _conexao() as conexao:
        conexao.execute(
            "INSERT INTO carrinhos_manuais (token, itens, subtotal, criado_em) VALUES (?, ?, ?, ?)",
            (token, itens_json, subtotal, agora),
        )
    return obter_por_token(token)


def obter_por_token(token: str) -> dict | None:
    inicializar_db()
    with _conexao() as conexao:
        linha = conexao.execute(
            "SELECT * FROM carrinhos_manuais WHERE token = ?", (token,)
        ).fetchone()
    if not linha:
        return None
    dado = dict(linha)
    dado["itens"] = json.loads(dado["itens"]) if dado["itens"] else []
    return dado
