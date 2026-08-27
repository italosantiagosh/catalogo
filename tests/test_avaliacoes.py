from __future__ import annotations

import io

import pytest

import services.avaliacoes as avaliacoes
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(avaliacoes, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _preparar_admin(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")


def _foto_teste():
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buffer, format="PNG")
    buffer.seek(0)
    return (buffer, "foto.png")


def _produto_id_real():
    from services.catalogo import carregar_produtos

    return carregar_produtos()[0]["id"]


def _corpo_avaliacao(**overrides):
    base = dict(
        produto_id=_produto_id_real(),
        nome_cliente="Maria Teste",
        nota="5",
        formato="medalha",
        texto="Chegou rápido e é linda!",
    )
    base.update(overrides)
    return base


def test_envio_sem_foto_e_aceito(client):
    """Foto e´ opcional -- avaliacao sem foto tambem entra na fila de
    moderacao normalmente (ver conversa: exigir foto tava barrando
    quem so queria deixar um comentario rapido)."""
    resposta = client.post("/api/avaliacoes", data=_corpo_avaliacao())
    assert resposta.status_code == 200

    pendentes = avaliacoes.listar_avaliacoes(status="pendente")
    assert len(pendentes) == 1
    assert pendentes[0]["foto"] == ""


def test_envio_com_foto_invalida_retorna_erro(client):
    resposta = client.post(
        "/api/avaliacoes",
        data={**_corpo_avaliacao(), "foto": (io.BytesIO(b"nao e uma imagem"), "arquivo.txt")},
        content_type="multipart/form-data",
    )
    assert resposta.status_code == 400


def test_envio_produto_inexistente_404(client):
    dados = _corpo_avaliacao(produto_id="nao-existe")
    arquivo, nome = _foto_teste()
    resposta = client.post("/api/avaliacoes", data={**dados, "foto": (arquivo, nome)})
    assert resposta.status_code == 404


def test_pagina_avaliar_produto_mostra_formulario_aberto(client):
    """Link direto pra mandar pra base de clientes antiga (ver conversa)
    -- so o formulario, ja aberto, sem o resto do site em volta."""
    produto_id = _produto_id_real()
    resposta = client.get(f"/avaliar/{produto_id}")
    assert resposta.status_code == 200
    corpo = resposta.get_data(as_text=True)
    assert f'value="{produto_id}"' in corpo
    assert 'id="form-avaliacao"' in corpo
    assert "hidden" not in corpo.split('id="form-avaliacao"')[1].split(">")[0]


def test_pagina_avaliar_produto_inexistente_404(client):
    resposta = client.get("/avaliar/nao-existe")
    assert resposta.status_code == 404


def test_envio_sem_nome_retorna_erro(client):
    dados = _corpo_avaliacao(nome_cliente="")
    arquivo, nome = _foto_teste()
    resposta = client.post("/api/avaliacoes", data={**dados, "foto": (arquivo, nome)})
    assert resposta.status_code == 400


def test_envio_nota_invalida_retorna_erro(client):
    dados = _corpo_avaliacao(nota="6")
    arquivo, nome = _foto_teste()
    resposta = client.post("/api/avaliacoes", data={**dados, "foto": (arquivo, nome)})
    assert resposta.status_code == 400


def test_envio_valido_fica_pendente_e_nao_aparece_no_produto(client, monkeypatch):
    _preparar_admin(monkeypatch)
    produto_id = _produto_id_real()
    dados = _corpo_avaliacao(produto_id=produto_id)
    arquivo, nome = _foto_teste()
    resposta = client.post("/api/avaliacoes", data={**dados, "foto": (arquivo, nome)})
    assert resposta.status_code == 200
    assert resposta.get_json()["ok"] is True

    # nao aparece na pagina publica do produto ainda (pendente)
    pagina = client.get(f"/produto/{produto_id}").get_data(as_text=True)
    assert "Maria Teste" not in pagina

    # aparece na fila de moderacao do admin
    lista_admin = client.get("/admin/avaliacoes", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "Maria Teste" in lista_admin
    assert "pendente" in lista_admin


def test_aprovar_avaliacao_aparece_na_pagina_do_produto(client, monkeypatch):
    _preparar_admin(monkeypatch)
    produto_id = _produto_id_real()
    dados = _corpo_avaliacao(produto_id=produto_id)
    arquivo, nome = _foto_teste()
    client.post("/api/avaliacoes", data={**dados, "foto": (arquivo, nome)})

    avaliacao = avaliacoes.listar_avaliacoes()[0]
    resposta = client.post(f"/admin/avaliacoes/{avaliacao['id']}/aprovar", auth=("admin", "segredo123"))
    assert resposta.status_code == 302

    pagina = client.get(f"/produto/{produto_id}").get_data(as_text=True)
    assert "Maria Teste" in pagina
    assert "Chegou rápido e é linda!" in pagina
    assert "AggregateRating" in pagina


def test_recusar_avaliacao_nao_aparece(client, monkeypatch):
    _preparar_admin(monkeypatch)
    produto_id = _produto_id_real()
    dados = _corpo_avaliacao(produto_id=produto_id)
    arquivo, nome = _foto_teste()
    client.post("/api/avaliacoes", data={**dados, "foto": (arquivo, nome)})

    avaliacao = avaliacoes.listar_avaliacoes()[0]
    client.post(f"/admin/avaliacoes/{avaliacao['id']}/recusar", auth=("admin", "segredo123"))

    pagina = client.get(f"/produto/{produto_id}").get_data(as_text=True)
    assert "Maria Teste" not in pagina


def test_envio_com_foto_heic_do_iphone_funciona(client):
    """Fotos de iPhone vem em HEIC por padrao (nao JPEG) -- ver
    app.py:register_heif_opener. Sem isso, esse upload falhava com
    "Não foi possível processar a foto enviada."."""
    import io

    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()
    buffer = io.BytesIO()
    Image.new("RGB", (50, 50), color="blue").save(buffer, format="HEIF")
    buffer.seek(0)

    dados = _corpo_avaliacao()
    resposta = client.post("/api/avaliacoes", data={**dados, "foto": (buffer, "IMG_1234.HEIC")})
    assert resposta.status_code == 200
    assert resposta.get_json()["ok"] is True


def test_admin_avaliacoes_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.get("/admin/avaliacoes")
    assert resposta.status_code == 401


def test_aprovar_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    produto_id = _produto_id_real()
    dados = _corpo_avaliacao(produto_id=produto_id)
    arquivo, nome = _foto_teste()
    client.post("/api/avaliacoes", data={**dados, "foto": (arquivo, nome)})
    avaliacao = avaliacoes.listar_avaliacoes()[0]

    resposta = client.post(f"/admin/avaliacoes/{avaliacao['id']}/aprovar")
    assert resposta.status_code == 401
