from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import services.carrinhos_abandonados as carrinhos_abandonados
import services.pedidos as pedidos
from app import app, _enviar_lembretes_carrinhos_abandonados


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(carrinhos_abandonados, "DB_PATH", db_path)
    monkeypatch.setattr(pedidos, "DB_PATH", db_path)
    app.config["TESTING"] = True
    return app.test_client()


def _itens():
    return [{"chave": "1-1-medalha-16mm", "chave_preco": "16mm", "quantidade": 3, "produtoNome": "São José"}]


def _corpo(**overrides):
    base = dict(token="token-abc", nome="Maria Teste", email="maria@example.com", telefone="",
                itens=_itens(), subtotal=45.0)
    base.update(overrides)
    return base


def _envelhecer(token: str, minutos: int) -> None:
    passado = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
    with carrinhos_abandonados._conexao() as conexao:
        conexao.execute("UPDATE carrinhos_abandonados SET criado_em = ? WHERE token = ?", (passado, token))


def _corpo_pedido(**overrides):
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


# ---- salvar/capturar ----

def test_salvar_carrinho_abandonado_valido(client):
    resposta = client.post("/api/carrinho/abandonado", json=_corpo())
    assert resposta.status_code == 200
    assert resposta.get_json()["ok"] is True

    salvo = carrinhos_abandonados.obter_por_token("token-abc")
    assert salvo["nome"] == "Maria Teste"
    assert salvo["email"] == "maria@example.com"
    assert salvo["itens"] == _itens()


def test_salvar_sem_nome_e_ignorado_sem_erro(client):
    resposta = client.post("/api/carrinho/abandonado", json=_corpo(nome=""))
    assert resposta.status_code == 200
    assert resposta.get_json()["ok"] is False
    assert carrinhos_abandonados.obter_por_token("token-abc") is None


def test_salvar_sem_contato_e_ignorado(client):
    resposta = client.post("/api/carrinho/abandonado", json=_corpo(email="", telefone=""))
    assert resposta.status_code == 200
    assert resposta.get_json()["ok"] is False


def test_salvar_carrinho_vazio_e_ignorado(client):
    resposta = client.post("/api/carrinho/abandonado", json=_corpo(itens=[]))
    assert resposta.status_code == 200
    assert resposta.get_json()["ok"] is False


def test_salvar_de_novo_com_mesmo_token_atualiza_sem_duplicar(client):
    client.post("/api/carrinho/abandonado", json=_corpo())
    client.post("/api/carrinho/abandonado", json=_corpo(nome="Maria Atualizada", subtotal=90.0))

    salvo = carrinhos_abandonados.obter_por_token("token-abc")
    assert salvo["nome"] == "Maria Atualizada"
    assert salvo["subtotal"] == 90.0
    with carrinhos_abandonados._conexao() as conexao:
        total = conexao.execute("SELECT COUNT(*) AS n FROM carrinhos_abandonados").fetchone()["n"]
    assert total == 1


# ---- restaurar por token ----

def test_obter_por_token_inexistente_404(client):
    resposta = client.get("/api/carrinho/abandonado/nao-existe")
    assert resposta.status_code == 404


def test_obter_por_token_existente_devolve_itens(client):
    client.post("/api/carrinho/abandonado", json=_corpo())
    resposta = client.get("/api/carrinho/abandonado/token-abc")
    assert resposta.status_code == 200
    assert resposta.get_json()["itens"] == _itens()


# ---- job de lembrete ----

def test_sem_canonical_domain_nao_faz_nada(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "")
    client.post("/api/carrinho/abandonado", json=_corpo())
    _envelhecer("token-abc", 200)
    with patch("app.enviar_lembrete_carrinho_abandonado") as mock_email:
        _enviar_lembretes_carrinhos_abandonados()
    mock_email.assert_not_called()


def test_manda_lembrete_pro_carrinho_antigo_e_marca_uma_vez(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "LEMBRETE_CARRINHO_MINUTOS", 30)

    client.post("/api/carrinho/abandonado", json=_corpo())
    _envelhecer("token-abc", 40)

    with patch("app.enviar_lembrete_carrinho_abandonado", return_value={"ok": True}) as mock_email:
        _enviar_lembretes_carrinhos_abandonados()
    assert mock_email.call_count == 1
    url_enviada = mock_email.call_args.args[1]
    assert "restaurar=token-abc" in url_enviada

    salvo = carrinhos_abandonados.obter_por_token("token-abc")
    assert salvo["lembrete_enviado"] == 1

    # rodar de novo nao deve mandar duas vezes
    with patch("app.enviar_lembrete_carrinho_abandonado") as mock_email2:
        _enviar_lembretes_carrinhos_abandonados()
    mock_email2.assert_not_called()


def test_carrinho_recente_nao_recebe_lembrete(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    client.post("/api/carrinho/abandonado", json=_corpo())

    with patch("app.enviar_lembrete_carrinho_abandonado") as mock_email:
        _enviar_lembretes_carrinhos_abandonados()
    mock_email.assert_not_called()


def test_carrinho_sem_email_nao_recebe_lembrete(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "LEMBRETE_CARRINHO_MINUTOS", 30)
    client.post("/api/carrinho/abandonado", json=_corpo(email="", telefone="84999999999"))
    _envelhecer("token-abc", 40)

    with patch("app.enviar_lembrete_carrinho_abandonado") as mock_email:
        _enviar_lembretes_carrinhos_abandonados()
    mock_email.assert_not_called()


# ---- marcar recuperado quando um pedido de verdade e´ criado ----

def test_pedido_criado_marca_carrinho_abandonado_como_recuperado(client, monkeypatch):
    """Mesmo e-mail do carrinho abandonado -- depois de um pedido de
    verdade criado, o job de lembrete nao deve mais mandar nada pra essa
    pessoa (ver marcar_recuperado_por_contato)."""
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "LEMBRETE_CARRINHO_MINUTOS", 30)

    client.post("/api/carrinho/abandonado", json=_corpo())
    _envelhecer("token-abc", 40)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        resposta = client.post("/api/pedido/criar", json=_corpo_pedido())
    assert resposta.status_code == 200

    salvo = carrinhos_abandonados.obter_por_token("token-abc")
    assert salvo["recuperado"] == 1

    with patch("app.enviar_lembrete_carrinho_abandonado") as mock_email:
        _enviar_lembretes_carrinhos_abandonados()
    mock_email.assert_not_called()


# ---- painel admin ----

def _preparar_admin(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")


def test_admin_carrinhos_abandonados_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.get("/admin/carrinhos-abandonados")
    assert resposta.status_code == 401


def test_admin_carrinhos_abandonados_lista_pendentes_por_padrao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    client.post("/api/carrinho/abandonado", json=_corpo())
    client.post("/api/carrinho/abandonado", json=_corpo(token="token-recuperado", email="outra@example.com"))
    carrinhos_abandonados.marcar_recuperado_por_contato(email="outra@example.com")

    pagina = client.get("/admin/carrinhos-abandonados", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "Maria Teste" in pagina
    assert "outra@example.com" not in pagina  # recuperado nao aparece no filtro padrao

    pagina_todos = client.get(
        "/admin/carrinhos-abandonados?status=todos", auth=("admin", "segredo123")
    ).get_data(as_text=True)
    assert "outra@example.com" in pagina_todos


def test_admin_carrinhos_abandonados_mostra_link_whatsapp_e_email(client, monkeypatch):
    _preparar_admin(monkeypatch)
    client.post("/api/carrinho/abandonado", json=_corpo(email="maria@example.com", telefone="84999999999"))

    pagina = client.get("/admin/carrinhos-abandonados", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "https://wa.me/5584999999999" in pagina
    assert "mailto:maria@example.com" in pagina


def test_admin_carrinhos_abandonados_mensagem_whatsapp_tem_itens_e_link_de_volta(client, monkeypatch):
    """Ver conversa: msg do WhatsApp era generica (so nome), sem os
    itens nem link pra voltar -- igual o e-mail ja fazia (ver
    services/email.py:_corpo_html_carrinho_abandonado). Agora usa o
    mesmo link de restauracao (?restaurar=<token>, ver static/js/
    carrinho_pagina.js) pra o carrinho voltar do jeito que estava."""
    _preparar_admin(monkeypatch)
    client.post("/api/carrinho/abandonado", json=_corpo(token="token-xyz", telefone="84999999999"))

    pagina = client.get("/admin/carrinhos-abandonados", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "https://wa.me/5584999999999?text=" in pagina
    assert "S%C3%A3o%20Jos%C3%A9" in pagina  # nome do item, urlencoded
    assert "3x" in pagina
    assert "restaurar%3Dtoken-xyz" in pagina  # link de volta, urlencoded


def test_admin_carrinhos_abandonados_avisa_quando_abaixo_do_minimo(client, monkeypatch):
    _preparar_admin(monkeypatch)
    client.post("/api/carrinho/abandonado", json=_corpo(
        token="token-baixo", telefone="84999999999", subtotal=18.0,
    ))

    pagina = client.get("/admin/carrinhos-abandonados", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "Falta%20s%C3%B3%20R%24%2012%2C00" in pagina  # falta, urlencoded


def test_admin_carrinhos_abandonados_sem_aviso_quando_atinge_minimo(client, monkeypatch):
    _preparar_admin(monkeypatch)
    client.post("/api/carrinho/abandonado", json=_corpo(
        token="token-ok", telefone="84999999999", subtotal=45.0,
    ))

    pagina = client.get("/admin/carrinhos-abandonados", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "pedido%20m%C3%ADnimo" not in pagina


def test_listar_todos_ordena_mais_recente_primeiro(client):
    client.post("/api/carrinho/abandonado", json=_corpo(token="primeiro"))
    client.post("/api/carrinho/abandonado", json=_corpo(token="segundo"))
    lista = carrinhos_abandonados.listar_todos()
    assert [c["token"] for c in lista] == ["segundo", "primeiro"]


def test_estatisticas_periodo_sem_nenhum_carrinho(client):
    stats = carrinhos_abandonados.estatisticas_periodo(30)
    assert stats == {"total": 0, "recuperados": 0, "taxa_pct": None}


def test_estatisticas_periodo_calcula_taxa(client):
    client.post("/api/carrinho/abandonado", json=_corpo(token="a", email="a@example.com"))
    client.post("/api/carrinho/abandonado", json=_corpo(token="b", email="b@example.com"))
    carrinhos_abandonados.marcar_recuperado_por_contato(email="a@example.com")

    stats = carrinhos_abandonados.estatisticas_periodo(30)
    assert stats == {"total": 2, "recuperados": 1, "taxa_pct": 50.0}


def test_estatisticas_periodo_ignora_carrinho_fora_da_janela(client):
    client.post("/api/carrinho/abandonado", json=_corpo(token="antigo"))
    _envelhecer("antigo", 60 * 24 * 40)  # 40 dias atras

    stats = carrinhos_abandonados.estatisticas_periodo(30)
    assert stats == {"total": 0, "recuperados": 0, "taxa_pct": None}
