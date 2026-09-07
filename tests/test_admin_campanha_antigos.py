from __future__ import annotations

import io
from unittest.mock import patch

import openpyxl
import pytest

import services.campanha_reengajamento as campanha
import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    caminho = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(pedidos, "DB_PATH", caminho)
    monkeypatch.setattr(campanha, "DB_PATH", caminho)
    app.config["TESTING"] = True
    return app.test_client()


def _auth(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    return ("admin", "segredo123")


def _planilha_bytes(linhas: list[tuple]) -> bytes:
    pasta = openpyxl.Workbook()
    aba = pasta.active
    aba.append(["ID", "Nome", "Fantasia", "E-mail"])  # cabecalho fora de ordem, igual planilha real
    for linha in linhas:
        aba.append(linha)
    buffer = io.BytesIO()
    pasta.save(buffer)
    return buffer.getvalue()


def test_pagina_exige_autenticacao(client):
    resposta = client.get("/admin/campanha-antigos")
    assert resposta.status_code == 401


def test_pagina_mostra_contagem_zerada_sem_dados(client, monkeypatch):
    credenciais = _auth(monkeypatch)
    resposta = client.get("/admin/campanha-antigos", auth=credenciais)
    assert resposta.status_code == 200
    assert "Reengajamento".encode() in resposta.data


def test_importar_planilha_via_upload(client, monkeypatch):
    credenciais = _auth(monkeypatch)
    arquivo = _planilha_bytes(
        [
            (1, "Maria Silva", "", "maria@example.com"),
            (2, "João Souza", "", "joao@example.com"),
            (3, "Sem E-mail", "", None),
        ]
    )
    resposta = client.post(
        "/admin/campanha-antigos/importar",
        data={"planilhas": (io.BytesIO(arquivo), "contatos.xlsx")},
        content_type="multipart/form-data",
        auth=credenciais,
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert campanha.contagem_por_status() == {"pendente": 2, "enviado": 0, "erro": 0}


def test_importar_duas_planilhas_de_uma_vez_dedupe_entre_elas(client, monkeypatch):
    credenciais = _auth(monkeypatch)
    arquivo1 = _planilha_bytes([(1, "Maria Silva", "", "maria@example.com")])
    arquivo2 = _planilha_bytes([(1, "Maria da Silva", "", "maria@example.com"), (2, "Ana", "", "ana@example.com")])
    resposta = client.post(
        "/admin/campanha-antigos/importar",
        data={"planilhas": [(io.BytesIO(arquivo1), "a.xlsx"), (io.BytesIO(arquivo2), "b.xlsx")]},
        content_type="multipart/form-data",
        auth=credenciais,
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert campanha.contagem_por_status()["pendente"] == 2


def test_enviar_lote_manda_e_marca_status(client, monkeypatch):
    credenciais = _auth(monkeypatch)
    campanha.importar_contatos(
        [{"nome": "Maria Silva", "email": "maria@example.com"}, {"nome": "Ana Costa", "email": "ana@example.com"}]
    )
    with patch("app.enviar_reengajamento_contato_antigo", return_value={"ok": True}) as mock_email:
        resposta = client.post(
            "/admin/campanha-antigos/enviar-lote", data={"tamanho": "1"}, auth=credenciais, follow_redirects=True
        )
    assert resposta.status_code == 200
    assert mock_email.call_count == 1
    contagem = campanha.contagem_por_status()
    assert contagem["enviado"] == 1
    assert contagem["pendente"] == 1  # so mandou 1 do lote de tamanho 1


def test_enviar_lote_marca_erro_quando_email_falha(client, monkeypatch):
    credenciais = _auth(monkeypatch)
    campanha.importar_contatos([{"nome": "Maria Silva", "email": "maria@example.com"}])
    with patch("app.enviar_reengajamento_contato_antigo", return_value={"erro": "falhou"}):
        client.post("/admin/campanha-antigos/enviar-lote", data={"tamanho": "10"}, auth=credenciais)
    assert campanha.contagem_por_status() == {"pendente": 0, "enviado": 0, "erro": 1}


def test_enviar_lote_respeita_tamanho_maximo(client, monkeypatch):
    credenciais = _auth(monkeypatch)
    campanha.importar_contatos([{"nome": f"C{i}", "email": f"c{i}@example.com"} for i in range(3)])
    with patch("app.enviar_reengajamento_contato_antigo", return_value={"ok": True}) as mock_email:
        client.post("/admin/campanha-antigos/enviar-lote", data={"tamanho": "999999"}, auth=credenciais)
    # trava no _CAMPANHA_LOTE_MAXIMO, mas so tem 3 pendentes mesmo
    assert mock_email.call_count == 3
