"""
Migra pedidos ANTIGOS (criados antes do fix de hoje, ver conversa) que
ainda guardam a foto da medalha personalizada como data URI inteiro
(base64) direto no campo `itens` do pedido -- pro formato novo, leve
(URL curta pra services/imagens_personalizadas.py).

Por que isso importa: o painel admin (/admin/pedidos) carrega e faz
json.loads() do campo `itens` de TODOS os pedidos recentes pra montar a
lista -- um pedido com foto no formato antigo carrega a imagem inteira
em memoria nesse processo, mesmo a lista nao mostrando a foto. Pedidos
com foto acumulados entre os mais recentes pesam na RAM do servidor
toda vez que o painel e´ aberto (ver conversa: contribuiu junto com o
bug ja corrigido pro servico estourar o limite de memoria do Render).

Seguro rodar mais de uma vez (idempotente) -- so mexe em item que
ainda tem "data:" no campo imagem/imagemRecorte; pedido ja migrado
(ou que nunca teve foto) e´ ignorado. NAO apaga nem muda nada
visualmente pro cliente/admin, so troca onde o byte da imagem mora.

Uso (no shell do Render, ou localmente com PEDIDOS_DB_PATH apontando
pro banco certo):
    python3 scripts/migrar_imagens_personalizadas_antigas.py
"""

from __future__ import annotations

import base64
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import services.imagens_personalizadas as imagens_personalizadas  # noqa: E402
import services.pedidos as pedidos  # noqa: E402

_PADRAO_DATA_URI = re.compile(r"^data:([^;]+);base64,(.+)$", re.DOTALL)


def _migrar_data_uri(valor: str, *, nome_arquivo: str) -> str | None:
    """Devolve a nova URL se `valor` for um data URI valido, ou None se
    nao for (ja migrado, vazio, ou formato inesperado -- nesse caso
    NAO mexe, mais seguro deixar como esta do que arriscar corromper)."""
    encontrado = _PADRAO_DATA_URI.match(valor or "")
    if not encontrado:
        return None
    mimetype, base64_dados = encontrado.groups()
    try:
        dados = base64.b64decode(base64_dados)
    except Exception:
        return None
    token = imagens_personalizadas.salvar_imagem(dados, mimetype, nome_arquivo)
    imagens_personalizadas.marcar_imagem_usada(token)
    return f"/imagem-personalizada/{token}"


def main() -> None:
    # timeout=30 + WAL -- roda com o site AO VIVO no ar (mesmo banco),
    # sem isso da "database is locked" na primeira escrita concorrente
    # com o processo do site (ver conversa, erro real visto no shell
    # do Render). WAL fica gravado no proprio arquivo, entao ajuda os
    # dois lados (script e app) a partir da primeira conexao que abrir
    # com isso.
    conexao = sqlite3.connect(pedidos.DB_PATH, timeout=30)
    conexao.execute("PRAGMA journal_mode=WAL")
    conexao.row_factory = sqlite3.Row
    linhas = conexao.execute("SELECT token, codigo, itens FROM pedidos").fetchall()

    pedidos_alterados = 0
    imagens_migradas = 0

    for linha in linhas:
        itens = json.loads(linha["itens"])
        mudou = False
        for indice, item in enumerate(itens):
            nova_imagem = _migrar_data_uri(
                item.get("imagem", ""), nome_arquivo=f"{linha['codigo']}_{indice}_previa.png"
            )
            if nova_imagem:
                item["imagem"] = nova_imagem
                mudou = True
                imagens_migradas += 1

            nova_recorte = _migrar_data_uri(
                item.get("imagemRecorte", ""), nome_arquivo=f"{linha['codigo']}_{indice}_recorte.png"
            )
            if nova_recorte:
                item["imagemRecorte"] = nova_recorte
                mudou = True
                imagens_migradas += 1

        if mudou:
            # commita CADA pedido na hora (em vez de um commit gigante
            # so no final) -- prende o lock de escrita por menos tempo
            # de cada vez, e se o script for interrompido no meio o
            # progresso ja feito nao se perde (idempotente, ver
            # _migrar_data_uri -- rodar de novo so pega o que sobrou).
            conexao.execute(
                "UPDATE pedidos SET itens = ? WHERE token = ?",
                (json.dumps(itens, ensure_ascii=False), linha["token"]),
            )
            conexao.commit()
            pedidos_alterados += 1

    conexao.close()
    print(
        f"{pedidos_alterados} pedido(s) migrado(s), {imagens_migradas} imagem(ns) "
        f"movida(s) pra armazenamento duravel."
    )


if __name__ == "__main__":
    main()
