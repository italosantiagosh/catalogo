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

Os BYTES da imagem (`dados`) vao pro Cloudflare R2 quando configurado
(ver services/armazenamento_r2.py) -- so a metadata (token, mimetype,
nome_arquivo, criado_em, usada_em_pedido, tipo) fica no SQLite. Sem R2
configurado, cai de volta pro BLOB local de sempre (dev/teste). Uma
linha migrada pro R2 fica com `dados = b""` no SQLite -- obter_imagem
busca no R2 quando encontra isso vazio.
"""

from __future__ import annotations

import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import services.armazenamento_r2 as armazenamento_r2

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
        colunas_existentes = {
            linha[1] for linha in conexao.execute("PRAGMA table_info(imagens_personalizadas)").fetchall()
        }
        # "recorte" (1:1, resolucao real de producao -- o pesado dos
        # dois) ou "preview" (com moldura, tamanho fixo -- o que fica
        # visivel na pagina do pedido). So separa os dois pra dar pra
        # apagar so o recorte SOB PEDIDO do usuario (ver
        # purgar_recortes_usados_antigos abaixo -- chamado manualmente,
        # nunca em job agendado, mesmo espirito de
        # resetar_numeracao_modelo_personalizada em services/pedidos.py)
        # sem mexer na preview, que continua servindo o "imagem"/
        # imagemLado1/imagemLado2 do pedido pra sempre.
        if "tipo" not in colunas_existentes:
            conexao.execute("ALTER TABLE imagens_personalizadas ADD COLUMN tipo TEXT NOT NULL DEFAULT 'preview'")


def salvar_imagem(dados: bytes, mimetype: str, nome_arquivo: str, tipo: str = "preview") -> str:
    inicializar_db()
    token = secrets.token_urlsafe(16)
    dados_sqlite = dados
    if armazenamento_r2.configurado():
        armazenamento_r2.subir(token, dados, mimetype)
        dados_sqlite = b""
    with _conexao() as conexao:
        conexao.execute(
            "INSERT INTO imagens_personalizadas (token, dados, mimetype, nome_arquivo, criado_em, tipo) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (token, dados_sqlite, mimetype, nome_arquivo, datetime.now(timezone.utc).isoformat(), tipo),
        )
    return token


def obter_imagem(token: str) -> tuple[bytes, str, str] | None:
    inicializar_db()
    with _conexao() as conexao:
        linha = conexao.execute(
            "SELECT dados, mimetype, nome_arquivo FROM imagens_personalizadas WHERE token = ?", (token,)
        ).fetchone()
    if not linha:
        return None
    dados = linha["dados"]
    if not dados and armazenamento_r2.configurado():
        dados = armazenamento_r2.baixar(token)
    return (dados, linha["mimetype"], linha["nome_arquivo"])


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
        tokens = [
            linha["token"] for linha in conexao.execute(
                "SELECT token FROM imagens_personalizadas WHERE usada_em_pedido = 0 AND criado_em < ?", (limite,)
            ).fetchall()
        ]
        if tokens and armazenamento_r2.configurado():
            armazenamento_r2.apagar(tokens)
        cursor = conexao.execute(
            "DELETE FROM imagens_personalizadas WHERE usada_em_pedido = 0 AND criado_em < ?", (limite,)
        )
        return cursor.rowcount


def purgar_recortes_usados_antigos(dias: int = 30) -> int:
    """Apaga o RECORTE (1:1, resolucao real -- o pesado dos dois, ver
    inicializar_db acima) de pedidos de verdade (usada_em_pedido = 1)
    com mais de `dias` dias. NAO e´ chamado automaticamente em nenhum
    job -- so na mao, quando o usuario pedir (ver conversa: guardar pra
    sempre por padrao, mas dar pra apagar sob pedido dele, mesmo espirito
    de resetar_numeracao_modelo_personalizada em services/pedidos.py). A
    PREVIEW (menor, com moldura) NUNCA e´ apagada por essa funcao --
    continua pra sempre servindo o "imagem"/imagemLado1/imagemLado2
    mostrado na pagina de acompanhamento do pedido (a "miniatura" que
    fica no link). Devolve quantas linhas foram removidas."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with _conexao() as conexao:
        tokens = [
            linha["token"] for linha in conexao.execute(
                "SELECT token FROM imagens_personalizadas "
                "WHERE tipo = 'recorte' AND usada_em_pedido = 1 AND criado_em < ?",
                (limite,),
            ).fetchall()
        ]
        if tokens and armazenamento_r2.configurado():
            armazenamento_r2.apagar(tokens)
        cursor = conexao.execute(
            "DELETE FROM imagens_personalizadas WHERE tipo = 'recorte' AND usada_em_pedido = 1 AND criado_em < ?",
            (limite,),
        )
        return cursor.rowcount
