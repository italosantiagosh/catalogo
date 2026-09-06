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


class _R2Fake:
    """Simula o Cloudflare R2 em memoria -- usado pra testar o caminho
    "R2 configurado" de services/imagens_personalizadas.py sem precisar
    de rede/credencial de verdade (o mesmo espirito de _R2Fake.objetos
    valeria pra qualquer teste que precisasse inspecionar o que foi
    upado/apagado)."""

    def __init__(self):
        self.objetos: dict[str, bytes] = {}

    def subir(self, chave, dados, mimetype):
        self.objetos[chave] = dados

    def baixar(self, chave):
        return self.objetos[chave]

    def apagar(self, chaves):
        for chave in chaves:
            self.objetos.pop(chave, None)


@pytest.fixture
def r2_fake(monkeypatch):
    fake = _R2Fake()
    monkeypatch.setattr(imagens_personalizadas.armazenamento_r2, "configurado", lambda: True)
    monkeypatch.setattr(imagens_personalizadas.armazenamento_r2, "subir", fake.subir)
    monkeypatch.setattr(imagens_personalizadas.armazenamento_r2, "baixar", fake.baixar)
    monkeypatch.setattr(imagens_personalizadas.armazenamento_r2, "apagar", fake.apagar)
    return fake


def test_salvar_e_obter_imagem_com_r2_configurado(client, r2_fake):
    token = imagens_personalizadas.salvar_imagem(b"conteudo-r2", "image/png", "foto.png")

    # nao guarda o byte no SQLite quando R2 esta configurado -- so a
    # metadata (ver services/imagens_personalizadas.py:salvar_imagem)
    with imagens_personalizadas._conexao() as conexao:
        linha = conexao.execute(
            "SELECT dados FROM imagens_personalizadas WHERE token = ?", (token,)
        ).fetchone()
    assert linha["dados"] == b""
    assert r2_fake.objetos[token] == b"conteudo-r2"

    dados, mimetype, nome_arquivo = imagens_personalizadas.obter_imagem(token)
    assert dados == b"conteudo-r2"
    assert mimetype == "image/png"
    assert nome_arquivo == "foto.png"


def test_purgar_imagens_antigas_apaga_do_r2_tambem(client, r2_fake):
    token = imagens_personalizadas.salvar_imagem(b"a", "image/png", "a.png")
    assert token in r2_fake.objetos

    removidas = imagens_personalizadas.purgar_imagens_antigas(dias=0)

    assert removidas == 1
    assert token not in r2_fake.objetos


def test_linha_antiga_com_blob_local_continua_funcionando_com_r2_configurado(client, monkeypatch):
    """Uma linha que ainda tem o byte de verdade no SQLite (nunca
    migrada pro R2) continua sendo servida direto do banco, mesmo com
    R2 configurado agora -- so uma linha NOVA (dados vazio) vai buscar
    no R2 (ver obter_imagem)."""
    monkeypatch.setattr(imagens_personalizadas.armazenamento_r2, "configurado", lambda: False)
    token = imagens_personalizadas.salvar_imagem(b"blob-local-antigo", "image/png", "antiga.png")

    monkeypatch.setattr(imagens_personalizadas.armazenamento_r2, "configurado", lambda: True)
    dados, _mimetype, _nome = imagens_personalizadas.obter_imagem(token)
    assert dados == b"blob-local-antigo"


def _envelhecer_imagem(token: str, dias: int) -> None:
    from datetime import datetime, timedelta, timezone

    passado = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with imagens_personalizadas._conexao() as conexao:
        conexao.execute("UPDATE imagens_personalizadas SET criado_em = ? WHERE token = ?", (passado, token))


def test_purgar_recortes_usados_antigos_apaga_so_recorte_usado_e_velho(client):
    recorte_velho_usado = imagens_personalizadas.salvar_imagem(b"r1", "image/png", "r1.png", tipo="recorte")
    recorte_novo_usado = imagens_personalizadas.salvar_imagem(b"r2", "image/png", "r2.png", tipo="recorte")
    recorte_velho_nao_usado = imagens_personalizadas.salvar_imagem(b"r3", "image/png", "r3.png", tipo="recorte")
    preview_velha_usada = imagens_personalizadas.salvar_imagem(b"p1", "image/png", "p1.png", tipo="preview")

    for token in (recorte_velho_usado, recorte_novo_usado, preview_velha_usada):
        imagens_personalizadas.marcar_imagem_usada(token)

    _envelhecer_imagem(recorte_velho_usado, dias=31)
    _envelhecer_imagem(recorte_velho_nao_usado, dias=31)
    _envelhecer_imagem(preview_velha_usada, dias=31)

    removidas = imagens_personalizadas.purgar_recortes_usados_antigos(dias=30)

    assert removidas == 1
    assert imagens_personalizadas.obter_imagem(recorte_velho_usado) is None
    # nao usado -- fica pra purgar_imagens_antigas(dias=7), nao essa funcao
    assert imagens_personalizadas.obter_imagem(recorte_velho_nao_usado) is not None
    # recente -- ainda dentro do prazo de retencao
    assert imagens_personalizadas.obter_imagem(recorte_novo_usado) is not None
    # preview nunca e´ apagada por essa funcao, mesmo velha e usada
    assert imagens_personalizadas.obter_imagem(preview_velha_usada) is not None


def test_migracao_adiciona_coluna_tipo_em_banco_antigo(client, tmp_path):
    """Simula um banco criado antes da coluna `tipo` existir (imagem
    salva direto via SQL, sem passar por salvar_imagem) -- inicializar_db
    precisa migrar sem quebrar as linhas ja existentes."""
    import sqlite3
    from datetime import datetime, timezone

    with imagens_personalizadas._conexao() as conexao:
        conexao.execute("DROP TABLE IF EXISTS imagens_personalizadas")
        conexao.execute(
            """
            CREATE TABLE imagens_personalizadas (
                token TEXT PRIMARY KEY,
                dados BLOB NOT NULL,
                mimetype TEXT NOT NULL,
                nome_arquivo TEXT NOT NULL,
                criado_em TEXT NOT NULL,
                usada_em_pedido INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conexao.execute(
            "INSERT INTO imagens_personalizadas (token, dados, mimetype, nome_arquivo, criado_em, usada_em_pedido) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            ("token-antigo", b"x", "image/png", "x.png", datetime.now(timezone.utc).isoformat()),
        )

    imagens_personalizadas.inicializar_db()

    with imagens_personalizadas._conexao() as conexao:
        linha = conexao.execute(
            "SELECT tipo FROM imagens_personalizadas WHERE token = ?", ("token-antigo",)
        ).fetchone()
    assert linha["tipo"] == "preview"
    # imagem antiga (sem tipo definido) vira "preview" por padrao -- nunca
    # e´ apagada por purgar_recortes_usados_antigos, mesmo usada e velha
    assert imagens_personalizadas.obter_imagem("token-antigo") is not None


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

    # url_preview/url_crop (botoes "baixar previa/recorte" da propria
    # pagina /personalizada) usam o MESMO token, so com ?baixar=1 --
    # antes existia um mecanismo separado guardado em memoria do
    # processo pra isso (ver conversa: contribuiu pro servico estourar
    # o limite de memoria do Render), unificado num so.
    assert dados["url_preview"] == dados["preview"] + "?baixar=1"
    assert dados["url_crop"] == dados["crop"] + "?baixar=1"

    resposta_download = client.get(dados["url_crop"])
    assert resposta_download.status_code == 200
    assert resposta_download.mimetype == "application/octet-stream"
    assert "attachment" in resposta_download.headers["Content-Disposition"]

    # multi-leitura: baixar de novo (ou o <img> renderizar de novo)
    # continua funcionando, diferente do mecanismo antigo de uso unico.
    assert client.get(dados["crop"]).status_code == 200


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
