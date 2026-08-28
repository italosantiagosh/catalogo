from __future__ import annotations

from unittest.mock import patch

import pytest

import app as app_module
import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
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


def _preparar_admin(monkeypatch):
    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")


def test_criar_pedido_boleto_com_sucesso(client):
    with patch("app.emitir_boleto", return_value={"codigo_solicitacao": "abc-uuid"}), \
         patch("app.consultar_cobranca", return_value={
             "boleto": {"linhaDigitavel": "123456", "codigoBarras": "789"},
             "pix": {"pixCopiaECola": "00020126..."},
         }), \
         patch("app.enviar_boleto_gerado", return_value={"ok": True}):
        resposta = client.post("/api/pedido/criar-boleto", json=_corpo_valido())

    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["linha_digitavel"] == "123456"
    assert dados["pix_copia_cola"] == "00020126..."

    pedido = pedidos.obter_pedido(dados["token"])
    assert pedido["status"] == "pendente"
    assert pedido["inter_codigo_solicitacao"] == "abc-uuid"
    assert pedido["inter_codigo_barras"] == "789"


def test_criar_pedido_boleto_carrinho_vazio_400(client):
    resposta = client.post("/api/pedido/criar-boleto", json=_corpo_valido(itens=[]))
    assert resposta.status_code == 400


def test_criar_pedido_boleto_cpf_invalido_400(client):
    corpo = _corpo_valido(cliente={
        "nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "11111111111",
        "telefone": "84999999999", "email": "maria@example.com",
    })
    resposta = client.post("/api/pedido/criar-boleto", json=corpo)
    assert resposta.status_code == 400
    assert "CPF" in resposta.get_json()["erro"]


def test_criar_pedido_boleto_erro_na_inter_502(client):
    with patch("app.emitir_boleto", return_value={"erro": "Falha na Inter"}):
        resposta = client.post("/api/pedido/criar-boleto", json=_corpo_valido())
    assert resposta.status_code == 502


def test_criar_pedido_boleto_frete_manipulado_e_bloqueado(client):
    corpo = _corpo_valido(frete={"texto": "Correios PAC — R$ 25,50", "preco": 0.01})
    with patch("app.calcular_frete", return_value={
        "frete_gratis": False,
        "opcoes": [{"transportadora": "Correios", "servico": "PAC", "preco": 25.5, "prazo_dias": 6}],
    }):
        resposta = client.post("/api/pedido/criar-boleto", json=corpo)
    assert resposta.status_code == 400


def test_ver_boleto_pdf_com_sucesso(client):
    with patch("app.emitir_boleto", return_value={"codigo_solicitacao": "abc-uuid"}), \
         patch("app.consultar_cobranca", return_value={"boleto": {}, "pix": {}}), \
         patch("app.enviar_boleto_gerado", return_value={"ok": True}):
        criado = client.post("/api/pedido/criar-boleto", json=_corpo_valido()).get_json()

    with patch("app.baixar_pdf", return_value={"pdf_base64": "JVBERi0xLjQ="}):
        resposta = client.get(f"/pedido/{criado['token']}/boleto.pdf")
    assert resposta.status_code == 200
    assert resposta.mimetype == "application/pdf"


def test_ver_boleto_pdf_pedido_sem_boleto_404(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    resposta = client.get(f"/pedido/{criado['token']}/boleto.pdf")
    assert resposta.status_code == 404


def test_pagina_de_pedido_mostra_boleto_pendente(client):
    with patch("app.emitir_boleto", return_value={"codigo_solicitacao": "abc-uuid"}), \
         patch("app.consultar_cobranca", return_value={
             "boleto": {"linhaDigitavel": "123456789", "codigoBarras": "789"},
             "pix": {"pixCopiaECola": "00020126copia"},
         }), \
         patch("app.enviar_boleto_gerado", return_value={"ok": True}):
        criado = client.post("/api/pedido/criar-boleto", json=_corpo_valido()).get_json()

    corpo_html = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "123456789" in corpo_html
    assert "00020126copia" in corpo_html
    assert "até 2 dias úteis" in corpo_html
    assert "Baixar boleto" in corpo_html


def test_verificar_boletos_confirma_pagamento_quando_recebido(client, monkeypatch):
    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    with patch("app.emitir_boleto", return_value={"codigo_solicitacao": "abc-uuid"}), \
         patch("app.consultar_cobranca", return_value={"boleto": {}, "pix": {}}), \
         patch("app.enviar_boleto_gerado", return_value={"ok": True}):
        criado = client.post("/api/pedido/criar-boleto", json=_corpo_valido()).get_json()

    with patch("app.consultar_cobranca", return_value={
        "cobranca": {"situacao": "RECEBIDO", "valorTotalRecebido": "60.00"},
    }), patch("app.enviar_confirmacao_pedido", return_value={"ok": True}), \
         patch("app.enviar_notificacao_venda", return_value={"ok": True}), \
         patch("app.criar_pedido_tiny", return_value={"ok": True, "numero_pedido": "1"}), \
         patch("app.enviar_notificacao_push", return_value=None):
        app_module._verificar_boletos_inter_pendentes()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "pago"
    assert pedido["forma_pagamento"] == "boleto"


def test_verificar_boletos_cancela_quando_expirado(client, monkeypatch):
    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    with patch("app.emitir_boleto", return_value={"codigo_solicitacao": "abc-uuid"}), \
         patch("app.consultar_cobranca", return_value={"boleto": {}, "pix": {}}), \
         patch("app.enviar_boleto_gerado", return_value={"ok": True}):
        criado = client.post("/api/pedido/criar-boleto", json=_corpo_valido()).get_json()

    with patch("app.consultar_cobranca", return_value={"cobranca": {"situacao": "EXPIRADO"}}), \
         patch("app.enviar_pedido_cancelado", return_value={"ok": True}):
        app_module._verificar_boletos_inter_pendentes()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "cancelado"


def test_verificar_boletos_sem_canonical_domain_nao_faz_nada(client, monkeypatch):
    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "")
    with patch("app.emitir_boleto", return_value={"codigo_solicitacao": "abc-uuid"}), \
         patch("app.consultar_cobranca", return_value={"boleto": {}, "pix": {}}), \
         patch("app.enviar_boleto_gerado", return_value={"ok": True}):
        criado = client.post("/api/pedido/criar-boleto", json=_corpo_valido()).get_json()

    with patch("app.consultar_cobranca") as consultar_mock:
        app_module._verificar_boletos_inter_pendentes()
    consultar_mock.assert_not_called()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "pendente"


def test_verificar_boletos_erro_de_consulta_marca_e_continua(client, monkeypatch):
    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "atacado.lojanovedejulho.com.br")
    with patch("app.emitir_boleto", return_value={"codigo_solicitacao": "abc-uuid"}), \
         patch("app.consultar_cobranca", return_value={"boleto": {}, "pix": {}}), \
         patch("app.enviar_boleto_gerado", return_value={"ok": True}):
        criado = client.post("/api/pedido/criar-boleto", json=_corpo_valido()).get_json()

    with patch("app.consultar_cobranca", return_value={"erro": "fora do ar"}):
        app_module._verificar_boletos_inter_pendentes()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "pendente"
    assert pedido["inter_erro"] == "fora do ar"


def test_boleto_pendente_nao_recebe_lembrete_de_link_expirado(client, monkeypatch):
    """Pedido de boleto tem vencimento medido em dias (ver
    services/inter.py), o lembrete de "seu link expirou" de minutos so
    faz sentido pro fluxo InfinitePay -- ver
    services.pedidos.listar_pedidos_pendentes_para_lembrete."""
    with patch("app.emitir_boleto", return_value={"codigo_solicitacao": "abc-uuid"}), \
         patch("app.consultar_cobranca", return_value={"boleto": {}, "pix": {}}), \
         patch("app.enviar_boleto_gerado", return_value={"ok": True}):
        client.post("/api/pedido/criar-boleto", json=_corpo_valido()).get_json()

    assert pedidos.listar_pedidos_pendentes_para_lembrete(0) == []
