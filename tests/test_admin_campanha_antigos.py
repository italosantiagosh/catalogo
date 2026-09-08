from __future__ import annotations

import io
import threading
from unittest.mock import patch

import openpyxl
import pytest

import services.campanha_reengajamento as campanha
import services.pedidos as pedidos
from app import app


class _ThreadSincrona:
    """Substitui threading.Thread nos testes -- o envio de verdade roda
    em segundo plano (ver app.py:admin_campanha_enviar_lote, corrige o
    bug do worker travando durante o lote), mas nos testes queremos o
    resultado pronto assim que o POST retorna, entao .start() chama a
    funcao na hora, sincrono, na mesma thread do teste."""

    def __init__(self, target, args=(), kwargs=None, daemon=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self):
        self._target(*self._args, **self._kwargs)


@pytest.fixture
def client(monkeypatch, tmp_path):
    caminho = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(pedidos, "DB_PATH", caminho)
    monkeypatch.setattr(campanha, "DB_PATH", caminho)
    monkeypatch.setattr(threading, "Thread", _ThreadSincrona)
    import app as app_module

    monkeypatch.setattr(app_module, "_CAMPANHA_PAUSA_ENTRE_ENVIOS_SEGUNDOS", 0)
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
    assert campanha.contagem_por_status() == {"pendente": 2, "enviado": 0, "erro": 0, "ignorado": 0}


def test_importar_planilha_com_cabecalho_minusculo(client, monkeypatch):
    """ver conversa: planilha real chegou com cabecalho "nome"/"email"
    em minusculo (formato diferente do "Nome"/"E-mail" do Tiny) -- nada
    tinha importado por causa da comparacao exata que so aceitava
    maiuscula."""
    credenciais = _auth(monkeypatch)
    pasta = openpyxl.Workbook()
    aba = pasta.active
    aba.append(["id", "tipo", "nome", "email", "cpf"])
    aba.append([1, "f", "Maria Silva", "maria@example.com", "11144477735"])
    aba.append([2, "f", "João Souza", "joao@example.com", "22233344456"])
    buffer = io.BytesIO()
    pasta.save(buffer)
    resposta = client.post(
        "/admin/campanha-antigos/importar",
        data={"planilhas": (io.BytesIO(buffer.getvalue()), "clientes.xlsx")},
        content_type="multipart/form-data",
        auth=credenciais,
        follow_redirects=True,
    )
    assert resposta.status_code == 200
    assert campanha.contagem_por_status() == {"pendente": 2, "enviado": 0, "erro": 0, "ignorado": 0}


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
    assert campanha.contagem_por_status() == {"pendente": 0, "enviado": 0, "erro": 1, "ignorado": 0}


def test_enviar_lote_respeita_tamanho_maximo(client, monkeypatch):
    credenciais = _auth(monkeypatch)
    campanha.importar_contatos([{"nome": f"C{i}", "email": f"c{i}@example.com"} for i in range(3)])
    with patch("app.enviar_reengajamento_contato_antigo", return_value={"ok": True}) as mock_email:
        client.post("/admin/campanha-antigos/enviar-lote", data={"tamanho": "999999"}, auth=credenciais)
    # trava no _CAMPANHA_LOTE_MAXIMO, mas so tem 3 pendentes mesmo
    assert mock_email.call_count == 3


def test_enviar_lote_roda_em_segundo_plano_nao_no_request(client, monkeypatch):
    """ver conversa: um lote sincrono dentro do request trava o UNICO
    worker do gunicorn ate´ o --timeout 90 matar ele -- por isso o
    envio precisa ir pra uma thread separada e o redirect volta na
    hora, sem esperar o lote terminar."""
    credenciais = _auth(monkeypatch)
    campanha.importar_contatos([{"nome": "Maria Silva", "email": "maria@example.com"}])
    with patch("app.enviar_reengajamento_contato_antigo", return_value={"ok": True}):
        resposta = client.post("/admin/campanha-antigos/enviar-lote", data={"tamanho": "1"}, auth=credenciais)
    assert resposta.status_code == 302
    assert "lote_iniciado=1" in resposta.headers["Location"]


def test_nao_deixa_2_lotes_rodarem_ao_mesmo_tempo(client, monkeypatch):
    import app as app_module

    credenciais = _auth(monkeypatch)
    campanha.importar_contatos([{"nome": "Maria Silva", "email": "maria@example.com"}])
    app_module._CAMPANHA_ENVIO_EM_ANDAMENTO.acquire()  # simula um lote ja´ em andamento
    try:
        with patch("app.enviar_reengajamento_contato_antigo") as mock_email:
            resposta = client.post("/admin/campanha-antigos/enviar-lote", data={"tamanho": "1"}, auth=credenciais)
        mock_email.assert_not_called()
        assert "lote_ja_em_andamento=1" in resposta.headers["Location"]
    finally:
        app_module._CAMPANHA_ENVIO_EM_ANDAMENTO.release()


def test_exportar_csv_exige_autenticacao(client):
    resposta = client.get("/admin/campanha-antigos/csv")
    assert resposta.status_code == 401


def test_exportar_csv_lista_email_nome_status(client, monkeypatch):
    credenciais = _auth(monkeypatch)
    campanha.importar_contatos([
        {"nome": "Maria Silva", "email": "maria@example.com"},
        {"nome": "Ana Costa", "email": "ana@example.com"},
    ])
    campanha.marcar_enviado("maria@example.com", erro=None)
    campanha.marcar_enviado("ana@example.com", erro="Não foi possível enviar.")

    resposta = client.get("/admin/campanha-antigos/csv", auth=credenciais)
    assert resposta.status_code == 200
    assert resposta.mimetype == "text/csv"
    texto = resposta.data.decode("utf-8-sig")
    linhas = texto.strip().splitlines()
    assert linhas[0] == "email;nome;status;criado_em;enviado_em;erro"
    assert any(l.startswith("maria@example.com;Maria Silva;enviado;") for l in linhas)
    assert any("ana@example.com;Ana Costa;erro;" in l and "Não foi possível enviar." in l for l in linhas)


def test_marcar_nao_enviar_exige_autenticacao(client):
    resposta = client.post("/admin/campanha-antigos/marcar-nao-enviar", data={"emails": "x@example.com"})
    assert resposta.status_code == 401


def test_marcar_nao_enviar_tira_da_fila(client, monkeypatch):
    credenciais = _auth(monkeypatch)
    campanha.importar_contatos([
        {"nome": "Maria Silva", "email": "maria@example.com"},
        {"nome": "Ana Costa", "email": "ana@example.com"},
    ])
    resposta = client.post(
        "/admin/campanha-antigos/marcar-nao-enviar",
        data={"emails": "maria@example.com\n\n  "},
        auth=credenciais,
    )
    assert resposta.status_code == 302
    assert "nao_enviar_marcados=1" in resposta.headers["Location"]
    assert campanha.contagem_por_status() == {"pendente": 1, "enviado": 0, "erro": 0, "ignorado": 1}


def test_marcar_nao_enviar_varios_de_uma_vez(client, monkeypatch):
    credenciais = _auth(monkeypatch)
    campanha.importar_contatos([{"nome": f"C{i}", "email": f"c{i}@example.com"} for i in range(3)])
    resposta = client.post(
        "/admin/campanha-antigos/marcar-nao-enviar",
        data={"emails": "c0@example.com\nc1@example.com"},
        auth=credenciais,
    )
    assert "nao_enviar_marcados=2" in resposta.headers["Location"]
    assert campanha.contagem_por_status()["pendente"] == 1
