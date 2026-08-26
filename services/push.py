"""
Notificacao push no navegador (Web Push, RFC 8291) -- avisa a loja de
uma venda nova sem precisar checar o e-mail (ver app.py:webhook_infinitepay
e services/email.py:enviar_notificacao_venda, o aviso por e-mail
equivalente ja existente).

Usa o pacote `webpush` (nao o mais antigo `pywebpush`/`http-ece` -- esse
ultimo tem um sdist quebrado com setuptools moderno, nao instala via
pip hoje, ver conversa) -- puro Python, so depende de `cryptography`
(ja usado no projeto) + `pydantic`/`pyjwt`, todos distribuidos como
wheel, sem risco de quebrar o build no Render.

As chaves VAPID (par de chaves do SERVIDOR, identifica quem esta´
mandando a notificacao pros servicos de push do navegador -- Google,
Mozilla etc.) sao geradas UMA VEZ e guardadas so como variavel de
ambiente (VAPID_PRIVATE_KEY_PEM/VAPID_PUBLIC_KEY_PEM em config.py) --
nunca gravadas no repositorio. Sem essas variaveis configuradas, todo
mundo aqui vira no-op silencioso (mesmo padrao de BREVO_API_KEY/
TINY_API_TOKEN ausentes).

Guarda as "inscricoes" (1 por navegador/dispositivo que ativou as
notificacoes) no mesmo SQLite de services/pedidos.py -- mesmo aviso de
Persistent Disk no Render se aplica aqui.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import requests
from cryptography.hazmat.primitives import serialization
from webpush import WebPush, WebPushSubscription
from webpush.vapid import VAPID as _VapidHelper

from config import VAPID_PRIVATE_KEY_PEM, VAPID_PUBLIC_KEY_PEM, VAPID_SUBSCRIBER_EMAIL

# Mesmo banco/mesma variavel de ambiente de services/pedidos.py -- nao
# faz sentido um Persistent Disk separado so pra essa tabela nova.
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
    with _conexao() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                endpoint TEXT PRIMARY KEY,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,
                criado_em TEXT NOT NULL
            )
            """
        )


def salvar_subscription(*, endpoint: str, p256dh: str, auth: str) -> None:
    inicializar_db()
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            "INSERT OR REPLACE INTO push_subscriptions (endpoint, p256dh, auth, criado_em) VALUES (?, ?, ?, ?)",
            (endpoint, p256dh, auth, agora),
        )


def remover_subscription(endpoint: str) -> None:
    inicializar_db()
    with _conexao() as conexao:
        conexao.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))


def listar_subscriptions() -> list[dict]:
    inicializar_db()
    with _conexao() as conexao:
        linhas = conexao.execute("SELECT * FROM push_subscriptions").fetchall()
    return [dict(linha) for linha in linhas]


def obter_application_server_key() -> str:
    """Chave publica no formato que o navegador espera
    (`applicationServerKey` do PushManager.subscribe) -- string, nao
    PEM. Vazio se VAPID nao estiver configurado (esconde o botao de
    ativar notificacao no admin, ver app.py)."""
    if not VAPID_PUBLIC_KEY_PEM:
        return ""
    chave_publica = serialization.load_pem_public_key(VAPID_PUBLIC_KEY_PEM.encode())
    return _VapidHelper.get_application_server_key(chave_publica)


def enviar_notificacao(*, titulo: str, corpo: str, url: str) -> None:
    """Manda a notificacao push pra TODAS as inscricoes salvas (na
    pratica, 1 por dispositivo que o admin ativou) -- uma inscricao
    expirada/invalida (404/410 do servico de push) e´ removida
    silenciosamente; falha numa inscricao nao impede as outras. Nunca
    levanta excecao -- quem chama (webhook de pagamento) nao pode
    quebrar por causa disso."""
    if not VAPID_PRIVATE_KEY_PEM or not VAPID_PUBLIC_KEY_PEM:
        return
    inscricoes = listar_subscriptions()
    if not inscricoes:
        return

    try:
        wp = WebPush(
            private_key=VAPID_PRIVATE_KEY_PEM.encode(),
            public_key=VAPID_PUBLIC_KEY_PEM.encode(),
            subscriber=VAPID_SUBSCRIBER_EMAIL,
        )
    except Exception:
        return

    payload = json.dumps({"titulo": titulo, "corpo": corpo, "url": url}, ensure_ascii=False)
    for inscricao in inscricoes:
        try:
            subscription = WebPushSubscription.model_validate(
                {
                    "endpoint": inscricao["endpoint"],
                    "keys": {"p256dh": inscricao["p256dh"], "auth": inscricao["auth"]},
                }
            )
            mensagem = wp.get(message=payload, subscription=subscription)
            resposta = requests.post(
                inscricao["endpoint"], data=mensagem.encrypted, headers=mensagem.headers, timeout=10
            )
            if resposta.status_code in (404, 410):
                remover_subscription(inscricao["endpoint"])
        except Exception:
            continue
