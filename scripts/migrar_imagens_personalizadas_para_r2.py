"""
Script de migracao ONE-OFF: sobe pro Cloudflare R2 as imagens
personalizadas que ainda estao guardadas como BLOB no SQLite (de antes
dessa integracao existir, ou de qualquer periodo em que
R2_ACCOUNT_ID/ACCESS_KEY/SECRET nao estavam configurados) -- depois de
subir, esvazia a coluna `dados` da linha (fica so a referencia por
token, ver services/imagens_personalizadas.py:obter_imagem) pra liberar
de verdade o disco de 1GB do Render.

Idempotente: seguro rodar mais de uma vez -- so mexe nas linhas que
ainda tem `dados` de verdade (length(dados) > 0); linha ja migrada (ou
que ja nasceu no R2) e´ ignorada.

Uso (no shell do Render, ou localmente com PEDIDOS_DB_PATH e as 3
variaveis R2_* apontando pro banco/bucket certos):
    python3 scripts/migrar_imagens_personalizadas_para_r2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import services.armazenamento_r2 as armazenamento_r2  # noqa: E402
import services.imagens_personalizadas as imagens_personalizadas  # noqa: E402


def main() -> None:
    if not armazenamento_r2.configurado():
        print("R2 não configurado (R2_ACCOUNT_ID/ACCESS_KEY/SECRET) -- nada a fazer.")
        return

    imagens_personalizadas.inicializar_db()
    with imagens_personalizadas._conexao() as conexao:
        linhas = conexao.execute(
            "SELECT token, dados, mimetype FROM imagens_personalizadas WHERE length(dados) > 0"
        ).fetchall()

    print(f"{len(linhas)} imagem(ns) pra migrar.")
    for linha in linhas:
        armazenamento_r2.subir(linha["token"], linha["dados"], linha["mimetype"])
        with imagens_personalizadas._conexao() as conexao:
            conexao.execute(
                "UPDATE imagens_personalizadas SET dados = ? WHERE token = ?", (b"", linha["token"])
            )
        print(f"  migrada: {linha['token']}")

    print("Concluído.")


if __name__ == "__main__":
    main()
