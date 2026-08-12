"""
Catalogo de medalhas -- ponto de entrada Flask.

Rotas ate a ETAPA 5:
    /                      catalogo -- busca + grid de cards por santo/devocional
    /produto/<id>          pagina de produto -- modelos, tamanho, quantidade
    /carrinho              itens do carrinho (persistido em localStorage, static/js/carrinho.js)
    /api/carrinho/calcular preco/faixa de atacado recalculados a partir da quantidade total

O calculo de preco fica centralizado em services/pricing.py
(calcular_preco, proxima_faixa, calcular_carrinho) e so e chamado pelo
servidor -- a pagina do carrinho manda a lista de itens pro endpoint
acima e recebe de volta preco unitario/subtotal por item, a faixa
atingida e o quanto falta pra proxima. O indicador visual "Faltam X
unidades" (barra de progresso, mensagem de desbloqueio) e a ETAPA 6. O
gerador de medalha personalizada -- portado sem alteracoes do
repositorio `mockup`, ja em producao em gerador-medalhas.onrender.com
-- entra em /personalizada na ETAPA 7.
"""

from __future__ import annotations

from flask import Flask, abort, jsonify, render_template, request

from services.catalogo import buscar_produto, carregar_produtos
from services.pricing import TAMANHOS, calcular_carrinho, preco_minimo

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


@app.route("/api/carrinho/calcular", methods=["POST"])
def api_calcular_carrinho():
    dados = request.get_json(silent=True) or {}
    itens_recebidos = dados.get("itens", [])

    itens_validos = []
    for item in itens_recebidos:
        try:
            tamanho = str(item["tamanho"])
            quantidade = int(item["quantidade"])
        except (KeyError, TypeError, ValueError):
            continue
        if tamanho not in TAMANHOS or quantidade <= 0:
            continue
        itens_validos.append({"tamanho": tamanho, "quantidade": quantidade})

    return jsonify(calcular_carrinho(itens_validos))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
