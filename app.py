"""
Catalogo de medalhas -- ponto de entrada Flask.

Rotas ate a ETAPA 4:
    /              catalogo -- busca + grid de cards por santo/devocional
    /produto/<id>  pagina de produto -- modelos, tamanho, quantidade
    /carrinho      itens do carrinho (persistido em localStorage, static/js/carrinho.js)

O carrinho ainda nao calcula preco/faixa de atacado -- isso e a ETAPA 5
(services/pricing.py ja tem o preco_minimo usado no "a partir de" dos
cards, mas calcular_preco/proxima_faixa por quantidade total do carrinho
ainda nao existem). O gerador de medalha personalizada -- portado sem
alteracoes do repositorio `mockup`, ja em producao em
gerador-medalhas.onrender.com -- entra em /personalizada na ETAPA 7.
"""

from __future__ import annotations

from flask import Flask, abort, render_template

from services.catalogo import buscar_produto, carregar_produtos
from services.pricing import preco_minimo

app = Flask(__name__)


def _formatar_preco(valor: float) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


app.jinja_env.filters["preco"] = _formatar_preco


@app.route("/", methods=["GET"])
def index():
    produtos = carregar_produtos()
    itens = [
        {
            "id": p["id"],
            "nome": p["nome"],
            "thumbnail": p["modelos"][0]["imagem"],
        }
        for p in produtos
    ]
    return render_template(
        "index.html", produtos=itens, preco_a_partir_de=preco_minimo()
    )


@app.route("/produto/<produto_id>", methods=["GET"])
def produto(produto_id: str):
    produto = buscar_produto(produto_id)
    if produto is None:
        abort(404)
    return render_template("produto.html", produto=produto)


@app.route("/carrinho", methods=["GET"])
def carrinho():
    return render_template("carrinho.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
