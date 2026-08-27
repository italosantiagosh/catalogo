from __future__ import annotations

from unittest.mock import patch

import pytest

from app import app


@pytest.fixture
def client():
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
    assert "ainda não configurado" in resposta.get_data(as_text=True)


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
