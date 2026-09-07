from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import services.pedidos as pedidos
from app import app, _enviar_emails_recompra_entregues


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
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


def _criar(client, **overrides) -> str:
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido(**overrides)).get_json()
    return criado["token"]


def _entregar_e_envelhecer(token: str, dias: int) -> None:
    pedidos.atualizar_status(token, "entregue")
    passado = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with pedidos._conexao() as conexao:
        conexao.execute("UPDATE pedidos SET entregue_em = ? WHERE token = ?", (passado, token))


def _com_dominio(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")


# ---- services/pedidos.py: os 3 estagios sao independentes ----

def test_listar_pedidos_entregues_para_recompra_rejeita_dias_invalido():
    with pytest.raises(ValueError):
        pedidos.listar_pedidos_entregues_para_recompra(45)


def test_marcar_email_recompra_enviado_rejeita_dias_invalido(client):
    token = _criar(client)
    with pytest.raises(ValueError):
        pedidos.marcar_email_recompra_enviado(token, 45, erro=None)


def test_estagios_de_recompra_sao_independentes(client, monkeypatch):
    token = _criar(client)
    _entregar_e_envelhecer(token, 35)  # ja passou dos 30 dias
    pedidos.marcar_email_recompra_enviado(token, 30, erro=None)

    candidatos_30 = pedidos.listar_pedidos_entregues_para_recompra(30)
    assert candidatos_30 == []  # ja recebeu o de 30

    candidatos_60 = pedidos.listar_pedidos_entregues_para_recompra(60)
    assert candidatos_60 == []  # ainda nao fez 60 dias


# ---- job agendado (app.py) ----

def test_sem_canonical_domain_nao_faz_nada(client, monkeypatch):
    with patch("app.enviar_pedido_recompra") as mock_email:
        _enviar_emails_recompra_entregues()
    mock_email.assert_not_called()


def test_manda_recompra_30_dias_com_link_de_repetir(client, monkeypatch):
    _com_dominio(monkeypatch)
    token = _criar(client)
    _entregar_e_envelhecer(token, 31)

    with patch("app.enviar_pedido_recompra", return_value={"ok": True}) as mock_email:
        _enviar_emails_recompra_entregues()

    assert mock_email.call_count == 1
    pedido_arg, dias_arg, url_arg = mock_email.call_args.args
    assert dias_arg == 30
    assert f"/pedido/{token}" in url_arg
    assert "repetir=1" in url_arg
    assert mock_email.call_args.kwargs["tem_repetir"] is True

    pedido = pedidos.obter_pedido(token)
    assert pedido["email_recompra_30_enviado"] == 1


def test_pedido_so_personalizada_recebe_link_do_catalogo(client, monkeypatch):
    _com_dominio(monkeypatch)
    token = _criar(client, itens=[{"chave_preco": "16mm", "quantidade": 10}])  # sem produtoId
    _entregar_e_envelhecer(token, 31)

    with patch("app.enviar_pedido_recompra", return_value={"ok": True}) as mock_email:
        _enviar_emails_recompra_entregues()

    assert mock_email.call_count == 1
    _, _, url_arg = mock_email.call_args.args
    assert url_arg.endswith("/catalogo")
    assert mock_email.call_args.kwargs["tem_repetir"] is False


def test_manda_todos_os_3_estagios_quando_todos_vencidos(client, monkeypatch):
    _com_dominio(monkeypatch)
    token = _criar(client)
    _entregar_e_envelhecer(token, 91)  # ja passou dos 3 (30/60/90)

    with patch("app.enviar_pedido_recompra", return_value={"ok": True}) as mock_email:
        _enviar_emails_recompra_entregues()

    assert mock_email.call_count == 3
    dias_mandados = sorted(chamada.args[1] for chamada in mock_email.call_args_list)
    assert dias_mandados == [30, 60, 90]


def test_nao_reenvia_o_mesmo_estagio_duas_vezes(client, monkeypatch):
    _com_dominio(monkeypatch)
    token = _criar(client)
    _entregar_e_envelhecer(token, 31)

    with patch("app.enviar_pedido_recompra", return_value={"ok": True}):
        _enviar_emails_recompra_entregues()

    with patch("app.enviar_pedido_recompra") as mock_email2:
        _enviar_emails_recompra_entregues()
    mock_email2.assert_not_called()


def test_entrega_recente_ainda_nao_recebe_nenhum_estagio(client, monkeypatch):
    _com_dominio(monkeypatch)
    token = _criar(client)
    _entregar_e_envelhecer(token, 5)

    with patch("app.enviar_pedido_recompra") as mock_email:
        _enviar_emails_recompra_entregues()
    mock_email.assert_not_called()
