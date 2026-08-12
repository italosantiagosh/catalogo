"""
Catalogo de medalhas -- ponto de entrada Flask.

Nesta etapa (ETAPA 2) a rota "/" e apenas um placeholder que lista os
santos cadastrados em data/produtos.json, so para validar que os dados
centralizados carregam corretamente. O catalogo completo (busca,
filtros, pagina de produto) entra na ETAPA 3; o gerador de medalha
personalizada -- portado sem alteracoes do repositorio `mockup`, que ja
esta em producao em gerador-medalhas.onrender.com -- entra em
/personalizada na ETAPA 7.
"""

from __future__ import annotations

from flask import Flask, render_template

from services.catalogo import carregar_produtos

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    produtos = carregar_produtos()
    return render_template("index.html", produtos=produtos)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
