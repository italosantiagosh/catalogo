from __future__ import annotations

from unittest.mock import patch

import pytest

import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    # admin_analytics agora tambem cruza com o banco de pedidos (funil
    # de conversao/proporcoes, ver conversa) -- isola num banco vazio
    # por teste, senao os testes leriam o data/pedidos.db real do repo.
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _preparar_admin(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")


def test_admin_analytics_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.get("/admin/analytics")
    assert resposta.status_code == 401


def test_admin_analytics_nao_configurado(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.analytics.configurado", return_value=False):
        resposta = client.get("/admin/analytics", auth=("admin", "segredo123"))
    assert resposta.status_code == 200
    corpo = resposta.get_data(as_text=True)
    assert "ainda não está configurado" in corpo
    # a secao de Vendas nao depende do GA4, tem que continuar aparecendo
    assert "Vendas (30 dias)" in corpo


def test_admin_analytics_mostra_numeros(client, monkeypatch):
    _preparar_admin(monkeypatch)
    with patch("app.analytics.configurado", return_value=True), \
         patch("app.analytics.usuarios_ativos_agora", return_value=3), \
         patch("app.analytics.resumo_ultimos_dias", side_effect=lambda dias: {"visitas": 100 * dias, "pessoas": 50, "visualizacoes": 300}), \
         patch("app.analytics.paginas_mais_vistas", return_value=[{"pagina": "/produto/sao-jose", "visualizacoes": 42}]), \
         patch("app.analytics.contagem_evento", return_value=7), \
         patch("app.analytics.contagem_evento_tempo_real", return_value=2):
        resposta = client.get("/admin/analytics", auth=("admin", "segredo123"))
    corpo = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert ">3<" in corpo
    assert "/produto/sao-jose" in corpo
    assert ">42<" in corpo
    assert ">2<" in corpo
    assert "últimos 30 min" in corpo


def test_admin_analytics_mostra_visitas_e_fretes_de_hoje(client, monkeypatch):
    """Ver conversa: usuario pediu numero de hoje, alem dos de 7/30
    dias, tanto pra visita quanto pra simulacao de frete."""
    _preparar_admin(monkeypatch)
    with patch("app.analytics.configurado", return_value=True), \
         patch("app.analytics.usuarios_ativos_agora", return_value=1), \
         patch("app.analytics.resumo_ultimos_dias", side_effect=lambda dias: {"visitas": 9 if dias == 0 else 100, "pessoas": 5, "visualizacoes": 20}), \
         patch("app.analytics.paginas_mais_vistas", return_value=[]), \
         patch("app.analytics.contagem_evento", side_effect=lambda nome, dias: 4 if dias == 0 else 40), \
         patch("app.analytics.contagem_evento_tempo_real", return_value=0):
        resposta = client.get("/admin/analytics", auth=("admin", "segredo123"))
    corpo = resposta.get_data(as_text=True)
    assert "Visitas hoje" in corpo
    assert "Simulações de frete hoje" in corpo
    assert ">9<" in corpo
    assert ">4<" in corpo


def _corpo_pedido_valido(**overrides):
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


def test_admin_analytics_mostra_funil_e_proporcoes_com_pedidos_reais(client, monkeypatch):
    """Ver conversa: usuario pediu proporcao de simulacao/venda por
    visita, cruzando o GA4 (mockado) com pedidos de verdade no banco."""
    _preparar_admin(monkeypatch)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        pago = client.post("/api/pedido/criar", json=_corpo_pedido_valido()).get_json()
        client.post("/api/pedido/criar", json=_corpo_pedido_valido())  # fica pendente
    with patch("app.criar_pedido_tiny", return_value={"erro": "não configurado"}), \
         patch("app.enviar_confirmacao_pedido", return_value={"erro": "não configurado"}), \
         patch("app.enviar_notificacao_venda", return_value={"ok": True}), \
         patch("app.enviar_notificacao_push", return_value={"ok": True}):
        client.post(
            "/webhook/infinitepay",
            json={"order_nsu": pago["token"], "paid_amount": 6000, "capture_method": "pix"},
        )

    with patch("app.analytics.configurado", return_value=True), \
         patch("app.analytics.usuarios_ativos_agora", return_value=0), \
         patch("app.analytics.resumo_ultimos_dias", return_value={"visitas": 100, "pessoas": 80, "visualizacoes": 200}), \
         patch("app.analytics.paginas_mais_vistas", return_value=[]), \
         patch("app.analytics.contagem_evento", return_value=10), \
         patch("app.analytics.contagem_evento_tempo_real", return_value=0):
        resposta = client.get("/admin/analytics", auth=("admin", "segredo123"))
    corpo = resposta.get_data(as_text=True)

    assert "Funil de conversão" in corpo
    assert "Iniciaram pedido" in corpo
    assert "Compraram" in corpo
    # 2 pedidos iniciados (1 pago + 1 pendente) / 100 visitas = 2.0%
    assert "2.0%" in corpo
    # 1 pago / 100 visitas = 1.0%
    assert "1.0%" in corpo
    # 10 simulacoes / 100 visitas = 10.0%
    assert "10.0%" in corpo
    assert "Ticket médio" in corpo
    assert "R$ 60,00" in corpo  # unica venda paga


def test_admin_analytics_mostra_secao_de_vendas_com_pedidos_reais(client, monkeypatch):
    """Ver conversa: usuaria mandou print do dashboard da Yampi como
    referencia -- grafico por dia, pedidos por estado, formas de
    pagamento, produtos mais vendidos, cancelamento/recorrencia."""
    _preparar_admin(monkeypatch)

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        pago = client.post("/api/pedido/criar", json=_corpo_pedido_valido()).get_json()
    with patch("app.criar_pedido_tiny", return_value={"erro": "não configurado"}), \
         patch("app.enviar_confirmacao_pedido", return_value={"erro": "não configurado"}), \
         patch("app.enviar_notificacao_venda", return_value={"ok": True}), \
         patch("app.enviar_notificacao_push", return_value={"ok": True}):
        client.post(
            "/webhook/infinitepay",
            json={"order_nsu": pago["token"], "paid_amount": 6000, "capture_method": "pix"},
        )

    with patch("app.analytics.configurado", return_value=False):
        resposta = client.get("/admin/analytics", auth=("admin", "segredo123"))
    corpo = resposta.get_data(as_text=True)

    assert "Vendas (30 dias)" in corpo
    assert "R$ 60,00" in corpo  # faturamento = ticket unico
    assert "Pedidos pagos por estado" in corpo
    assert "RN" in corpo
    assert "Formas de pagamento" in corpo
    assert "Pix" in corpo
    assert "Produtos mais vendidos" in corpo
    assert "São José" in corpo


def test_analytics_service_sem_config_devolve_none():
    import services.analytics as analytics

    modulo_original_json = analytics.GA4_SERVICE_ACCOUNT_JSON
    modulo_original_property = analytics.GA4_PROPERTY_ID
    analytics.GA4_SERVICE_ACCOUNT_JSON = ""
    analytics.GA4_PROPERTY_ID = ""
    analytics._cliente = None
    analytics._cliente_tentado = False
    try:
        assert analytics.configurado() is False
        assert analytics.usuarios_ativos_agora() is None
        assert analytics.resumo_ultimos_dias(7) is None
        assert analytics.paginas_mais_vistas(7) is None
        assert analytics.contagem_evento("calculate_shipping", 7) is None
        assert analytics.contagem_evento_tempo_real("calculate_shipping") is None
    finally:
        analytics.GA4_SERVICE_ACCOUNT_JSON = modulo_original_json
        analytics.GA4_PROPERTY_ID = modulo_original_property
        analytics._cliente = None
        analytics._cliente_tentado = False
