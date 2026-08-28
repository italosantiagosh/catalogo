from __future__ import annotations

import io

import pytest
from PIL import Image
from unittest.mock import patch

import services.imagens_personalizadas as imagens_personalizadas
import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(pedidos, "DB_PATH", db_path)
    monkeypatch.setattr(imagens_personalizadas, "DB_PATH", db_path)
    app.config["TESTING"] = True
    return app.test_client()


def _corpo_valido(**overrides):
    base = dict(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"}],
        frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0},
        cliente={"nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "11144477735",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


# ---- services/imagens_personalizadas.py ----

def test_salvar_e_obter_imagem(client):
    token = imagens_personalizadas.salvar_imagem(b"conteudo-fake", "image/png", "foto.png")
    dados, mimetype, nome_arquivo = imagens_personalizadas.obter_imagem(token)
    assert dados == b"conteudo-fake"
    assert mimetype == "image/png"
    assert nome_arquivo == "foto.png"


def test_obter_imagem_token_desconhecido_devolve_none(client):
    assert imagens_personalizadas.obter_imagem("token-que-nao-existe") is None


def test_purgar_imagens_antigas_preserva_imagem_usada(client):
    token_usado = imagens_personalizadas.salvar_imagem(b"a", "image/png", "a.png")
    token_nao_usado = imagens_personalizadas.salvar_imagem(b"b", "image/png", "b.png")
    imagens_personalizadas.marcar_imagem_usada(token_usado)

    # dias=0 -- qualquer imagem nao usada, mesmo recem-criada, e removida
    removidas = imagens_personalizadas.purgar_imagens_antigas(dias=0)

    assert removidas == 1
    assert imagens_personalizadas.obter_imagem(token_usado) is not None
    assert imagens_personalizadas.obter_imagem(token_nao_usado) is None


# ---- rota /api/personalizada/preview + /imagem-personalizada/<token> ----

def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_preview_personalizada_devolve_url_duravel_nao_data_uri(client):
    imagem_resultado = Image.new("RGBA", (20, 20), (255, 0, 0, 255))
    with patch("app.compose_medal", return_value=imagem_resultado), \
         patch("app._crop_quadrada", return_value=imagem_resultado.convert("RGB")):
        resposta = client.post(
            "/api/personalizada/preview",
            data={
                "imagem": (io.BytesIO(_png_bytes()), "foto.png"),
                "formato": "medalha",
                "x1": "0", "y1": "0", "x2": "10", "y2": "10",
            },
            content_type="multipart/form-data",
        )
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["preview"].startswith("/imagem-personalizada/")
    assert dados["crop"].startswith("/imagem-personalizada/")
    assert not dados["preview"].startswith("data:")
    assert not dados["crop"].startswith("data:")

    resposta_imagem = client.get(dados["crop"])
    assert resposta_imagem.status_code == 200
    assert resposta_imagem.mimetype == "image/png"


def test_servir_imagem_personalizada_404_para_token_desconhecido(client):
    resposta = client.get("/imagem-personalizada/token-que-nao-existe")
    assert resposta.status_code == 404


def test_criar_pedido_com_imagem_personalizada_marca_como_usada(client):
    token = imagens_personalizadas.salvar_imagem(b"recorte", "image/png", "recorte.png")
    url_recorte = f"/imagem-personalizada/{token}"
    corpo = _corpo_valido(itens=[{
        "chave_preco": "16mm", "quantidade": 10, "produtoNome": "Personalizada",
        "formato": "medalha", "tamanho": "16mm",
        "imagem": url_recorte, "imagemRecorte": url_recorte,
    }])
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        resposta = client.post("/api/pedido/criar", json=corpo)
    assert resposta.status_code == 200

    # imagem referenciada por um pedido nunca deve sumir na limpeza,
    # mesmo com dias=0 (ver test_purgar_imagens_antigas_preserva_imagem_usada)
    imagens_personalizadas.purgar_imagens_antigas(dias=0)
    assert imagens_personalizadas.obter_imagem(token) is not None


def test_carrinho_antigo_com_data_uri_continua_funcionando(client):
    """Compatibilidade com carrinho ja aberto no navegador de antes dessa
    mudanca (ver services/imagens_personalizadas.py) -- data URI direto
    continua sendo aceito e guardado do mesmo jeito."""
    corpo = _corpo_valido(itens=[{
        "chave_preco": "16mm", "quantidade": 10, "produtoNome": "Personalizada",
        "formato": "medalha", "tamanho": "16mm",
        "imagem": "data:image/png;base64,AAAA", "imagemRecorte": "data:image/png;base64,BBBB",
    }])
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        resposta = client.post("/api/pedido/criar", json=corpo)
    assert resposta.status_code == 200
    pedido = pedidos.obter_pedido(resposta.get_json()["token"])
    assert pedido["itens"][0]["imagemRecorte"] == "data:image/png;base64,BBBB"
