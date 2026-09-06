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
        itens=[{"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "produtoId": "sao-jose",
                "modeloNome": "Modelo 1", "descricao": "São José — Modelo 1"}],
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


def test_pendente_menciona_itens_frete_total_e_link_do_pedido(client):
    token = _criar(client)
    with app.test_request_context():
        mensagem = app_module._mensagem_whatsapp_cliente(pedidos.obter_pedido(token))

    pedido = pedidos.obter_pedido(token)
    assert "Maria Teste" in mensagem
    assert "São José" in mensagem
    assert "Correios PAC" in mensagem
    assert f"R$ {pedido['total']:.2f}".replace(".", ",") in mensagem
    assert f"/pedido/{token}" in mensagem
    assert "aguardando seu pagamento" in mensagem


def test_pendente_com_boleto_manda_codigo_de_barras_e_link_do_boleto(client):
    token = _criar(client)
    pedidos.salvar_dados_boleto_inter(
        token, codigo_solicitacao="abc-uuid", linha_digitavel="123.456", codigo_barras="789456123",
        pix_copia_cola="",
    )
    with app.test_request_context():
        mensagem = app_module._mensagem_whatsapp_cliente(pedidos.obter_pedido(token))

    assert "789456123" in mensagem
    assert f"/pedido/{token}/boleto.pdf" in mensagem
    assert f"/pedido/{token}" in mensagem  # link de acompanhamento continua junto


def test_cancelado_oferece_reativar_pix_e_boleto(client):
    token = _criar(client)
    pedidos.cancelar_pedido(token)
    with app.test_request_context():
        mensagem = app_module._mensagem_whatsapp_cliente(pedidos.obter_pedido(token))

    assert f"/pedido/{token}/reativar-pix" in mensagem
    assert f"/pedido/{token}/reativar-boleto" in mensagem
    assert "valores imperdíveis" in mensagem


def test_pago_menciona_producao_e_nota_fiscal(client):
    token = _criar(client)
    pedidos.marcar_pago(token, forma_pagamento="pix", parcelas=None, valor_pago=78.65, transaction_nsu="tx")
    with app.test_request_context():
        mensagem = app_module._mensagem_whatsapp_cliente(pedidos.obter_pedido(token))

    assert "produção" in mensagem
    assert "nota fiscal" in mensagem


def test_faturado_menciona_link_da_nota_fiscal(client):
    token = _criar(client)
    pedidos.marcar_pago(token, forma_pagamento="pix", parcelas=None, valor_pago=78.65, transaction_nsu="tx")
    pedidos.atualizar_status(token, "faturado", link_nota_fiscal="https://nf.exemplo/123")
    with app.test_request_context():
        mensagem = app_module._mensagem_whatsapp_cliente(pedidos.obter_pedido(token))

    assert "faturado" in mensagem
    assert "https://nf.exemplo/123" in mensagem


def test_enviado_menciona_transportadora_e_rastreio(client):
    token = _criar(client)
    pedidos.marcar_pago(token, forma_pagamento="pix", parcelas=None, valor_pago=78.65, transaction_nsu="tx")
    pedidos.atualizar_status(
        token, "enviado", transportadora="Loggi", codigo_rastreio="BR123",
        link_rastreio="https://rastreio.exemplo/BR123",
    )
    with app.test_request_context():
        mensagem = app_module._mensagem_whatsapp_cliente(pedidos.obter_pedido(token))

    assert "Loggi" in mensagem
    assert "BR123" in mensagem
    assert "https://rastreio.exemplo/BR123" in mensagem


def test_entregue_convida_a_avaliar_o_produto(client):
    token = _criar(client)
    pedidos.marcar_pago(token, forma_pagamento="pix", parcelas=None, valor_pago=78.65, transaction_nsu="tx")
    pedidos.atualizar_status(token, "entregue")
    with app.test_request_context():
        mensagem = app_module._mensagem_whatsapp_cliente(pedidos.obter_pedido(token))

    assert "chegou" in mensagem
    assert "avaliar" in mensagem.lower()
    assert "/avaliar" in mensagem


def test_status_sem_mensagem_especial_devolve_vazio(client):
    criado = pedidos.criar_pedido(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "descricao": "São José — Modelo 1"}],
        subtotal=60.0, frete_descricao="Loggi", frete_preco=10.0,
        cliente={"nome": "Maria", "tipo_pessoa": "fisica", "documento": "11144477735",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua", "numero": "1", "complemento": "",
                  "bairro": "C", "cidade": "Natal", "uf": "RN"},
        status_inicial="whatsapp",
    )
    with app.test_request_context():
        mensagem = app_module._mensagem_whatsapp_cliente(pedidos.obter_pedido(criado["token"]))
    assert mensagem == ""


def test_link_whatsapp_no_admin_tem_o_texto_preenchido(client, monkeypatch):
    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    token = _criar(client)

    detalhe = client.get(f"/admin/pedidos/{token}", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "https://wa.me/5584999999999?text=" in detalhe
