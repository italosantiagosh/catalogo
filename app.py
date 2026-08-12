"""
Catalogo de medalhas -- ponto de entrada Flask.

Rotas ate a ETAPA 7:
    /                       catalogo -- busca + grid de cards por santo/devocional
    /produto/<id>           pagina de produto -- modelos, tamanho, quantidade
    /carrinho               itens do carrinho (persistido em localStorage, static/js/carrinho.js)
    /api/carrinho/calcular  preco/faixa de atacado recalculados a partir da quantidade total
    /personalizada          gerador de medalha personalizada (upload -> simulacao)

O calculo de preco fica centralizado em services/pricing.py
(calcular_preco, proxima_faixa, calcular_carrinho) e so e chamado pelo
servidor -- a pagina do carrinho manda a lista de itens pro endpoint
acima e recebe de volta preco unitario/subtotal por item, a faixa
atingida e o quanto falta pra proxima.

O gerador de medalha personalizada (services/gerador/) e o mesmo
codigo do repositorio `mockup`, ja em producao em
gerador-medalhas.onrender.com -- so o import interno de compositor.py
virou relativo para funcionar como pacote aqui dentro; a logica de
composicao (compositor.py) e a geometria calibrada (config.py) nao
foram alteradas. Adicionar a medalha personalizada ao carrinho e a
ETAPA 8 -- por enquanto o botao existe mas fica desabilitado.
"""

from __future__ import annotations

import base64
import io
import tempfile
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request

from services.catalogo import buscar_produto, carregar_produtos
from services.gerador.compositor import compose_medal
from services.gerador.config import IMAGE_EXTENSIONS, get_medal_spec
from services.pricing import TAMANHOS, calcular_carrinho, preco_minimo

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024  # 60MB no total do upload

_gerador_spec = get_medal_spec()


def _formatar_preco(valor: float) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


app.jinja_env.filters["preco"] = _formatar_preco


def _extensao_valida(nome_arquivo: str) -> bool:
    nome_lower = nome_arquivo.lower()
    return any(nome_lower.endswith(ext) for ext in IMAGE_EXTENSIONS)


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


@app.route("/personalizada", methods=["GET"])
def personalizada():
    return render_template("personalizada.html", tamanho_selecionado="16mm")


@app.route("/personalizada/processar", methods=["POST"])
def personalizada_processar():
    tamanho = request.form.get("tamanho", "16mm")
    if tamanho not in TAMANHOS:
        tamanho = "16mm"

    arquivo = request.files.get("imagem")
    if not arquivo or not arquivo.filename:
        return render_template(
            "personalizada.html", erro="Selecione uma imagem.", tamanho_selecionado=tamanho
        )

    if not _extensao_valida(arquivo.filename):
        return render_template(
            "personalizada.html",
            erro="Formato nao suportado. Envie uma imagem (" + ", ".join(IMAGE_EXTENSIONS) + ").",
            tamanho_selecionado=tamanho,
        )

    sufixo = Path(arquivo.filename).suffix or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=sufixo) as tmp:
        arquivo.save(tmp.name)
        try:
            resultado = compose_medal(_gerador_spec, Path(tmp.name))
        except Exception as exc:
            return render_template(
                "personalizada.html",
                erro=f"Erro ao gerar a simulacao: {exc}",
                tamanho_selecionado=tamanho,
            )

    buffer = io.BytesIO()
    resultado.save(buffer, format="PNG")
    preview_src = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

    return render_template(
        "personalizada.html", preview_src=preview_src, tamanho_selecionado=tamanho
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
