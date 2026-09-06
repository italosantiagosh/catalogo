"""
Script pontual: corrige na mao o tiny_numero_pedido de um pedido
especifico -- usado quando um "reenviar" acabou criando um pedido NOVO
na Tiny (numero diferente do original) em vez de ser recusado como
duplicidade (ver conversa: a Tiny nem sempre recusa reenvio de um
pedido ja existente, mesmo com o mesmo numero_pedido_ecommerce -- nao e´
garantido do lado dela). Depois de apagar manualmente o pedido errado
direto no painel da Tiny, usa esse script pra voltar o numero certo
aqui no site (painel geral e pagina do pedido passam a mostrar de novo
o numero original).

Uso (Render Shell, ou local com PEDIDOS_DB_PATH apontando pro banco
certo):
    python3 scripts/corrigir_numero_tiny.py <codigo_do_pedido> <numero_correto>

Exemplo:
    python3 scripts/corrigir_numero_tiny.py RZNM6R 1119
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import services.pedidos as pedidos  # noqa: E402


def main() -> None:
    if len(sys.argv) != 3:
        print("Uso: python3 scripts/corrigir_numero_tiny.py <codigo_do_pedido> <numero_correto>")
        sys.exit(1)

    codigo, numero_correto = sys.argv[1], sys.argv[2]

    with pedidos._conexao() as conexao:
        linha = conexao.execute("SELECT token FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()

    if linha is None:
        print(f"Nenhum pedido encontrado com código {codigo!r}.")
        sys.exit(1)

    token = linha["token"]
    antes = pedidos.obter_pedido(token)
    pedidos.marcar_tiny_sincronizado(token, numero_pedido=numero_correto, erro=None)
    depois = pedidos.obter_pedido(token)
    print(
        f"Pedido {codigo} (token {token}): tiny_numero_pedido {antes['tiny_numero_pedido']!r} "
        f"-> {depois['tiny_numero_pedido']!r}."
    )


if __name__ == "__main__":
    main()
