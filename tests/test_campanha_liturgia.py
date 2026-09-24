from __future__ import annotations

from unittest.mock import patch

import pytest

import services.carrinhos_abandonados as carrinhos_abandonados
import services.pedidos as pedidos
from app import app, _enviar_lote_campanha_convite_liturgia


@pytest.fixture
def client(monkeypatch, tmp_path):
    import app as app_module

    db_path = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(pedidos, "DB_PATH", db_path)
    monkeypatch.setattr(carrinhos_abandonados, "DB_PATH", db_path)
    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    app.config["TESTING"] = True
    return app.test_client()


def _corpo_valido(**overrides):
    base = dict(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "produtoId": "sao-jose",
                "produtoNome": "São José", "modeloId": "modelo-1", "modeloNome": "Modelo 1"}],
        frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0},
        cliente={"nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "11144477735",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def _criar_pago(client, **overrides) -> str:
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido(**overrides)).get_json()
    token = criado["token"]
    pedidos.marcar_pago(token, forma_pagamento="pix", parcelas=None, valor_pago=100.0, transaction_nsu="nsu-1")
    return token


def _criar_pendente(client, **overrides) -> str:
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido(**overrides)).get_json()
    return criado["token"]


# ---- services/pedidos.py ----

def test_preparar_campanha_so_pega_pedido_pago(client):
    _criar_pendente(client, cliente={"nome": "Pendente", "tipo_pessoa": "fisica", "documento": "11144477735",
                                      "telefone": "84999999999", "email": "pendente@example.com"})
    _criar_pago(client, cliente={"nome": "Paga", "tipo_pessoa": "fisica", "documento": "11144477735",
                                  "telefone": "84999999999", "email": "paga@example.com"})

    novos = pedidos.preparar_campanha_convite_liturgia()

    assert novos == 1
    contagem = pedidos.contar_campanha_convite_liturgia()
    assert contagem == {"total": 1, "enviados": 0, "pendentes": 1, "com_erro": 0}


def test_preparar_campanha_dedupe_por_email_usa_nome_mais_recente(client):
    _criar_pago(client, cliente={"nome": "Nome Antigo", "tipo_pessoa": "fisica", "documento": "11144477735",
                                  "telefone": "84999999999", "email": "repetida@example.com"})
    _criar_pago(client, cliente={"nome": "Nome Novo", "tipo_pessoa": "fisica", "documento": "11144477735",
                                  "telefone": "84999999999", "email": "REPETIDA@example.com"})

    novos = pedidos.preparar_campanha_convite_liturgia()

    assert novos == 1
    pendentes = pedidos.listar_pendentes_campanha_convite_liturgia(10)
    assert len(pendentes) == 1
    assert pendentes[0]["email"] == "repetida@example.com"
    assert pendentes[0]["nome"] == "Nome Novo"


def test_preparar_campanha_e_idempotente(client):
    _criar_pago(client)
    assert pedidos.preparar_campanha_convite_liturgia() == 1
    assert pedidos.preparar_campanha_convite_liturgia() == 0
    assert pedidos.contar_campanha_convite_liturgia()["total"] == 1


def test_marcar_enviado_sai_dos_pendentes(client):
    _criar_pago(client)
    pedidos.preparar_campanha_convite_liturgia()
    email = pedidos.listar_pendentes_campanha_convite_liturgia(10)[0]["email"]

    pedidos.marcar_campanha_convite_liturgia_enviado(email, erro=None)

    assert pedidos.listar_pendentes_campanha_convite_liturgia(10) == []
    contagem = pedidos.contar_campanha_convite_liturgia()
    assert contagem == {"total": 1, "enviados": 1, "pendentes": 0, "com_erro": 0}


def test_marcar_com_erro_continua_pendente(client):
    _criar_pago(client)
    pedidos.preparar_campanha_convite_liturgia()
    email = pedidos.listar_pendentes_campanha_convite_liturgia(10)[0]["email"]

    pedidos.marcar_campanha_convite_liturgia_enviado(email, erro="falha de rede")

    assert len(pedidos.listar_pendentes_campanha_convite_liturgia(10)) == 1
    assert pedidos.contar_campanha_convite_liturgia()["com_erro"] == 1


def test_listar_pendentes_respeita_limite(client):
    for i in range(3):
        _criar_pago(client, cliente={"nome": f"Cliente {i}", "tipo_pessoa": "fisica", "documento": "11144477735",
                                      "telefone": "84999999999", "email": f"cliente{i}@example.com"})
    pedidos.preparar_campanha_convite_liturgia()

    assert len(pedidos.listar_pendentes_campanha_convite_liturgia(2)) == 2
    assert len(pedidos.listar_pendentes_campanha_convite_liturgia(10)) == 3


# ---- app.py: job agendado ----

def test_job_sem_canonical_domain_nao_manda_nada(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "")
    _criar_pago(client)
    pedidos.preparar_campanha_convite_liturgia()

    with patch("app.enviar_convite_liturgia_mensal") as mock_email:
        _enviar_lote_campanha_convite_liturgia()
    mock_email.assert_not_called()


def test_job_manda_ate_o_limite_diario_e_marca_enviado(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "LIMITE_DIARIO_CAMPANHA_LITURGIA", 2)
    for i in range(3):
        _criar_pago(client, cliente={"nome": f"Cliente {i}", "tipo_pessoa": "fisica", "documento": "11144477735",
                                      "telefone": "84999999999", "email": f"cliente{i}@example.com"})
    pedidos.preparar_campanha_convite_liturgia()

    with patch("app.enviar_convite_liturgia_mensal", return_value={"ok": True}) as mock_email:
        _enviar_lote_campanha_convite_liturgia()

    assert mock_email.call_count == 2
    assert mock_email.call_args_list[0].args[2] == "https://lojanovedejulho.com.br/liturgia-do-mes"
    contagem = pedidos.contar_campanha_convite_liturgia()
    assert contagem["enviados"] == 2
    assert contagem["pendentes"] == 1


def test_job_marca_erro_quando_envio_falha(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    _criar_pago(client)
    pedidos.preparar_campanha_convite_liturgia()

    with patch("app.enviar_convite_liturgia_mensal", return_value={"erro": "Brevo fora do ar"}):
        _enviar_lote_campanha_convite_liturgia()

    contagem = pedidos.contar_campanha_convite_liturgia()
    assert contagem["enviados"] == 0
    assert contagem["com_erro"] == 1


# ---- rota admin ----

def test_admin_preparar_exige_autenticacao(client):
    resposta = client.post("/admin/campanha-liturgia/preparar")
    assert resposta.status_code == 401


def test_admin_preparar_popula_e_devolve_contagem(client):
    _criar_pago(client)
    resposta = client.post("/admin/campanha-liturgia/preparar", auth=("admin", "segredo123"))
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["ok"] is True
    assert dados["novos"] == 1
    assert dados["total"] == 1
    assert dados["pendentes"] == 1


def test_admin_preparar_e_seguro_chamar_duas_vezes(client):
    _criar_pago(client)
    client.post("/admin/campanha-liturgia/preparar", auth=("admin", "segredo123"))
    resposta = client.post("/admin/campanha-liturgia/preparar", auth=("admin", "segredo123"))
    dados = resposta.get_json()
    assert dados["novos"] == 0
    assert dados["total"] == 1
