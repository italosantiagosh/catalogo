"""
Captura de carrinho abandonado ANTES do pedido existir -- ver conversa
"recuperacao de carrinho".

Diferenca importante do lembrete de pedido "pendente" que ja existia
(services/pedidos.py:listar_pedidos_pendentes_para_lembrete): aquele so
cobre quem ja clicou em "Pagar agora"/"Gerar boleto" e o servidor ja
criou um pedido de verdade. O funil medido em 2026-09-14 mostrou que
esse e´ so uma fatia pequena de quem desiste -- a maior parte sai ANTES
disso, ainda preenchendo nome/telefone/e-mail no formulario, sem deixar
rastro nenhum ate agora. Essa tabela guarda esse rastro assim que a
pessoa digita nome + pelo menos um contato (e-mail ou telefone), mesmo
sem completar o resto do cadastro nem clicar em nada (ver
static/js/carrinho_pagina.js -- captura no blur do campo de e-mail/
telefone, via navigator.sendBeacon).

`token` identifica a MESMA visita (gerado e guardado no localStorage do
navegador, ver frete_estimativa.js pro mesmo padrao) -- salvar de novo
com o mesmo token so atualiza a linha (nome/itens podem mudar entre um
blur e outro), nunca duplica.

Mesmo padrao de SQLite usado em services/pedidos.py e services/
avaliacoes.py -- mesmo aviso sobre Persistent Disk no Render.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
            CREATE TABLE IF NOT EXISTS carrinhos_abandonados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                nome TEXT NOT NULL,
                email TEXT,
                telefone TEXT,
                itens TEXT NOT NULL,
                subtotal REAL NOT NULL,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                lembrete_enviado INTEGER NOT NULL DEFAULT 0,
                lembrete_enviado_em TEXT,
                lembrete_erro TEXT,
                recuperado INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conexao.execute(
            "CREATE INDEX IF NOT EXISTS idx_carrinhos_abandonados_lembrete "
            "ON carrinhos_abandonados (lembrete_enviado, recuperado, criado_em)"
        )


def _linha_para_dict(linha: sqlite3.Row) -> dict:
    dado = dict(linha)
    dado["itens"] = json.loads(dado["itens"]) if dado["itens"] else []
    return dado


def salvar_ou_atualizar(
    *, token: str, nome: str, email: str, telefone: str, itens: list[dict], subtotal: float
) -> dict:
    """Cria a linha na 1a chamada desse token, so atualiza dado/hora nas
    seguintes (nunca duplica, nunca reseta lembrete_enviado/recuperado
    ja marcados -- ver conversa: se a pessoa mexer no carrinho DEPOIS
    de ja ter recebido o lembrete, nao faz sentido mandar de novo nem
    reabrir algo ja recuperado)."""
    inicializar_db()
    agora = datetime.now(timezone.utc).isoformat()
    itens_json = json.dumps(itens, ensure_ascii=False)
    with _conexao() as conexao:
        existente = conexao.execute(
            "SELECT id FROM carrinhos_abandonados WHERE token = ?", (token,)
        ).fetchone()
        if existente:
            conexao.execute(
                """
                UPDATE carrinhos_abandonados
                SET nome = ?, email = ?, telefone = ?, itens = ?, subtotal = ?, atualizado_em = ?
                WHERE token = ?
                """,
                (nome, email, telefone, itens_json, subtotal, agora, token),
            )
        else:
            conexao.execute(
                """
                INSERT INTO carrinhos_abandonados
                    (token, nome, email, telefone, itens, subtotal, criado_em, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (token, nome, email, telefone, itens_json, subtotal, agora, agora),
            )
    return obter_por_token(token)


def obter_por_token(token: str) -> dict | None:
    inicializar_db()
    with _conexao() as conexao:
        linha = conexao.execute(
            "SELECT * FROM carrinhos_abandonados WHERE token = ?", (token,)
        ).fetchone()
    return _linha_para_dict(linha) if linha else None


def estatisticas_periodo(dias: int) -> dict:
    """Taxa de recuperacao (ver conversa: cartao no painel admin) --
    quantos carrinhos abandonados nos ultimos `dias` dias viraram venda
    de verdade (marcar_recuperado_por_contato), sem contar quem nao deu
    tempo (ainda esta´ dentro do prazo do lembrete)."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with _conexao() as conexao:
        total = conexao.execute(
            "SELECT COUNT(*) FROM carrinhos_abandonados WHERE criado_em >= ?", (limite,)
        ).fetchone()[0]
        recuperados = conexao.execute(
            "SELECT COUNT(*) FROM carrinhos_abandonados WHERE criado_em >= ? AND recuperado = 1", (limite,)
        ).fetchone()[0]
    taxa_pct = round(recuperados / total * 100, 1) if total else None
    return {"total": total, "recuperados": recuperados, "taxa_pct": taxa_pct}


def listar_todos(*, apenas_pendentes: bool = False, limite: int = 200) -> list[dict]:
    """Pra painel admin (ver app.py:admin_carrinhos_abandonados) -- quem
    vende poder entrar em contato na mao, sem depender so do e-mail
    automatico (nem todo mundo tem e-mail, so telefone por exemplo, ou
    quer mandar mensagem antes de esperar o prazo do lembrete).
    `apenas_pendentes` filtra fora quem ja recuperou (comprou) -- mais
    recente primeiro."""
    inicializar_db()
    filtro = "WHERE recuperado = 0" if apenas_pendentes else ""
    with _conexao() as conexao:
        linhas = conexao.execute(
            f"SELECT * FROM carrinhos_abandonados {filtro} ORDER BY criado_em DESC LIMIT ?",
            (limite,),
        ).fetchall()
    return [_linha_para_dict(linha) for linha in linhas]


def listar_para_lembrete(minutos: int) -> list[dict]:
    """Carrinhos com contato salvo ha´ mais de `minutos`, que ainda nao
    receberam lembrete e nao foram marcados como recuperados (ver
    marcar_recuperado_por_contato) -- so entra quem tem e-mail (o
    telefone sozinho nao tem canal automatico de envio ainda)."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
    with _conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT * FROM carrinhos_abandonados
            WHERE lembrete_enviado = 0 AND recuperado = 0
                AND email IS NOT NULL AND email != ''
                AND criado_em <= ?
            ORDER BY criado_em ASC
            """,
            (limite,),
        ).fetchall()
    return [_linha_para_dict(linha) for linha in linhas]


def marcar_lembrete_enviado(token: str, *, erro: str | None) -> dict | None:
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            """
            UPDATE carrinhos_abandonados
            SET lembrete_enviado = 1, lembrete_enviado_em = ?, lembrete_erro = ?
            WHERE token = ?
            """,
            (agora, erro, token),
        )
    return obter_por_token(token)


def marcar_recuperado_por_contato(*, email: str = "", telefone: str = "") -> None:
    """Chamado assim que um pedido de verdade e´ criado (ver app.py:
    api_pedido_criar/api_pedido_criar_boleto) -- marca qualquer carrinho
    abandonado com o MESMO e-mail ou telefone como recuperado, pra nunca
    mandar um lembrete de "voce esqueceu algo" pra quem ja comprou
    (inclusive se comprou por um caminho diferente do que abandonou,
    ex: abandonou no site e fechou depois pelo WhatsApp com o mesmo
    telefone)."""
    email = (email or "").strip()
    telefone = (telefone or "").strip()
    if not email and not telefone:
        return
    inicializar_db()
    with _conexao() as conexao:
        if email:
            conexao.execute(
                "UPDATE carrinhos_abandonados SET recuperado = 1 WHERE recuperado = 0 AND email = ?",
                (email,),
            )
        if telefone:
            conexao.execute(
                "UPDATE carrinhos_abandonados SET recuperado = 1 WHERE recuperado = 0 AND telefone = ?",
                (telefone,),
            )
