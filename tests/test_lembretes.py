from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import services.carrinhos_abandonados as carrinhos_abandonados
import services.pedidos as pedidos
from app import (
    app,
    _enviar_lembretes_finais_pedidos_pendentes,
    _enviar_lembretes_pedidos_pendentes,
    _enviar_lembretes_precoces_pedidos_pendentes,
)


@pytest.fixture
def client(monkeypatch, tmp_path):
    db_path = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(pedidos, "DB_PATH", db_path)
    monkeypatch.setattr(carrinhos_abandonados, "DB_PATH", db_path)
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


def _envelhecer(token: str, minutos: int) -> None:
    passado = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
    with pedidos._conexao() as conexao:
        conexao.execute("UPDATE pedidos SET criado_em = ? WHERE token = ?", (passado, token))


def test_sem_canonical_domain_nao_faz_nada(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "")
    with patch("app.enviar_lembrete_pedido_pendente") as mock_email:
        _enviar_lembretes_pedidos_pendentes()
    mock_email.assert_not_called()


def test_manda_lembrete_pro_pedido_antigo_e_marca_uma_vez(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "LEMBRETE_MINUTOS", 30)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/original"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _envelhecer(criado["token"], 40)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/novo"}) as mock_link, \
         patch("app.enviar_lembrete_pedido_pendente", return_value={"ok": True}) as mock_email:
        _enviar_lembretes_pedidos_pendentes()

    assert mock_link.call_count == 1
    assert mock_email.call_count == 1
    url_enviada = mock_email.call_args.args[1]
    assert url_enviada == "https://checkout.infinitepay.io/novo"

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_lembrete_enviado"] == 1

    # rodar de novo nao deve mandar duas vezes
    with patch("app.criar_link_pagamento") as mock_link2, \
         patch("app.enviar_lembrete_pedido_pendente") as mock_email2:
        _enviar_lembretes_pedidos_pendentes()
    mock_link2.assert_not_called()
    mock_email2.assert_not_called()


def test_pedido_recente_nao_recebe_lembrete(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        client.post("/api/pedido/criar", json=_corpo_valido())

    with patch("app.enviar_lembrete_pedido_pendente") as mock_email:
        _enviar_lembretes_pedidos_pendentes()
    mock_email.assert_not_called()


def test_falha_ao_gerar_link_marca_erro_sem_mandar_email(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "LEMBRETE_MINUTOS", 30)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _envelhecer(criado["token"], 40)

    with patch("app.criar_link_pagamento", return_value={"erro": "InfinitePay fora do ar"}), \
         patch("app.enviar_lembrete_pedido_pendente") as mock_email:
        _enviar_lembretes_pedidos_pendentes()
    mock_email.assert_not_called()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_lembrete_enviado"] == 1
    assert pedido["email_lembrete_erro"] == "InfinitePay fora do ar"


def test_precoce_sem_canonical_domain_nao_faz_nada(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "")
    with patch("app.enviar_lembrete_precoce_pedido_pendente") as mock_email:
        _enviar_lembretes_precoces_pedidos_pendentes()
    mock_email.assert_not_called()


def test_precoce_manda_mais_cedo_e_e_independente_do_normal(client, monkeypatch):
    # e´ ADICIONAL ao lembrete normal, nao substitui -- pedido velho o
    # suficiente pros dois prazos recebe os dois, cada um controlado
    # pela propria coluna (ver services/pedidos.py).
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "LEMBRETE_PRECOCE_MINUTOS", 15)
    monkeypatch.setattr(app_module, "LEMBRETE_MINUTOS", 30)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/original"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _envelhecer(criado["token"], 20)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/novo"}), \
         patch("app.enviar_lembrete_precoce_pedido_pendente", return_value={"ok": True}) as mock_email:
        _enviar_lembretes_precoces_pedidos_pendentes()
    assert mock_email.call_count == 1

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_lembrete_precoce_enviado"] == 1
    assert pedido["email_lembrete_enviado"] == 0  # normal ainda nao bateu o prazo

    # rodar de novo nao reenvia o precoce
    with patch("app.enviar_lembrete_precoce_pedido_pendente") as mock_email2:
        _enviar_lembretes_precoces_pedidos_pendentes()
    mock_email2.assert_not_called()

    # o normal ainda dispara depois, independente do precoce ja enviado
    _envelhecer(criado["token"], 40)
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/novo2"}), \
         patch("app.enviar_lembrete_pedido_pendente", return_value={"ok": True}) as mock_email3:
        _enviar_lembretes_pedidos_pendentes()
    assert mock_email3.call_count == 1
    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_lembrete_enviado"] == 1


def test_precoce_pedido_recente_nao_recebe_lembrete(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        client.post("/api/pedido/criar", json=_corpo_valido())

    with patch("app.enviar_lembrete_precoce_pedido_pendente") as mock_email:
        _enviar_lembretes_precoces_pedidos_pendentes()
    mock_email.assert_not_called()


def test_final_sem_canonical_domain_nao_faz_nada(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "")
    with patch("app.enviar_lembrete_pedido_pendente") as mock_email:
        _enviar_lembretes_finais_pedidos_pendentes()
    mock_email.assert_not_called()


def test_final_so_dispara_depois_do_normal(client, monkeypatch):
    # ainda nao recebeu o lembrete normal (12h) -- mesmo com criado_em
    # ja passando dos 18h, o final NAO pode disparar antes do normal
    # (evita ordem invertida de e-mails).
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "LEMBRETE_FINAL_MINUTOS", 5)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    _envelhecer(criado["token"], 999)

    with patch("app.enviar_lembrete_pedido_pendente") as mock_email:
        _enviar_lembretes_finais_pedidos_pendentes()
    mock_email.assert_not_called()


def test_fluxo_completo_6h_12h_18h_na_ordem(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "LEMBRETE_PRECOCE_MINUTOS", 10)
    monkeypatch.setattr(app_module, "LEMBRETE_MINUTOS", 20)
    monkeypatch.setattr(app_module, "LEMBRETE_FINAL_MINUTOS", 30)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    token = criado["token"]

    with patch("app.enviar_lembrete_pedido_pendente", return_value={"ok": True}), \
         patch("app.enviar_lembrete_precoce_pedido_pendente", return_value={"ok": True}):
        # so 15min: passa do precoce (10min), ainda nao do normal (20min)
        _envelhecer(token, 15)
        _enviar_lembretes_precoces_pedidos_pendentes()
        _enviar_lembretes_pedidos_pendentes()
        _enviar_lembretes_finais_pedidos_pendentes()
        pedido = pedidos.obter_pedido(token)
        assert pedido["email_lembrete_precoce_enviado"] == 1
        assert pedido["email_lembrete_enviado"] == 0
        assert pedido["email_lembrete_final_enviado"] == 0

        # 25min: passa do normal (20min), ainda nao do final (30min)
        _envelhecer(token, 25)
        _enviar_lembretes_precoces_pedidos_pendentes()
        _enviar_lembretes_pedidos_pendentes()
        _enviar_lembretes_finais_pedidos_pendentes()
        pedido = pedidos.obter_pedido(token)
        assert pedido["email_lembrete_enviado"] == 1
        assert pedido["email_lembrete_final_enviado"] == 0

        # 35min: passa do final (30min) -- os 3 ja foram
        _envelhecer(token, 35)
        _enviar_lembretes_precoces_pedidos_pendentes()
        _enviar_lembretes_pedidos_pendentes()
        _enviar_lembretes_finais_pedidos_pendentes()
        pedido = pedidos.obter_pedido(token)
        assert pedido["email_lembrete_final_enviado"] == 1


def test_final_pedido_recente_nao_recebe_lembrete(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        client.post("/api/pedido/criar", json=_corpo_valido())

    with patch("app.enviar_lembrete_pedido_pendente") as mock_email:
        _enviar_lembretes_finais_pedidos_pendentes()
    mock_email.assert_not_called()
