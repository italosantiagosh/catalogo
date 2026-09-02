"""
Dashboard de leitura do Google Analytics 4 pro painel admin (ver
app.py:/admin/analytics, templates/admin_analytics.html).

IMPORTANTE: API diferente do pixel que ja roda no site (GA4_MEASUREMENT_ID
em config.py/base.html) -- aquele so ENVIA eventos pro Google. Esse
modulo LE os numeros de volta, usando a Google Analytics Data API
(https://developers.google.com/analytics/devguide/reporting/data/v1),
autenticada com uma conta de servico do Google Cloud (ver
config.py:GA4_SERVICE_ACCOUNT_JSON/GA4_PROPERTY_ID).

Toda funcao aqui devolve None em caso de erro (nao configurado, conta
de servico sem acesso, GA4 fora do ar) -- o painel admin trata isso
mostrando um aviso, nunca quebra a pagina.
"""

from __future__ import annotations

import json

from config import GA4_PROPERTY_ID, GA4_SERVICE_ACCOUNT_JSON

_cliente = None
_cliente_tentado = False


def _client():
    """Cliente autenticado, construido uma unica vez por processo (lazy
    -- so tenta na primeira chamada de verdade, nao no import do
    modulo). Devolve None se nao configurado ou se a credencial for
    invalida."""
    global _cliente, _cliente_tentado
    if _cliente_tentado:
        return _cliente
    _cliente_tentado = True
    if not GA4_SERVICE_ACCOUNT_JSON or not GA4_PROPERTY_ID:
        return None
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.oauth2 import service_account

        info = json.loads(GA4_SERVICE_ACCOUNT_JSON)
        credenciais = service_account.Credentials.from_service_account_info(info)
        _cliente = BetaAnalyticsDataClient(credentials=credenciais)
    except Exception:
        _cliente = None
    return _cliente


def configurado() -> bool:
    return _client() is not None


def usuarios_ativos_agora() -> int | None:
    """Quantas pessoas estao no site AGORA (relatorio em tempo real do
    GA4) -- ver conversa: "o numero de quem esta ao vivo"."""
    cliente = _client()
    if cliente is None:
        return None
    from google.analytics.data_v1beta.types import Metric, RunRealtimeReportRequest

    try:
        resposta = cliente.run_realtime_report(
            RunRealtimeReportRequest(
                property=f"properties/{GA4_PROPERTY_ID}",
                metrics=[Metric(name="activeUsers")],
            )
        )
    except Exception:
        return None
    if not resposta.rows:
        return 0
    return int(resposta.rows[0].metric_values[0].value)


def resumo_periodo(inicio: str, fim: str) -> dict | None:
    """Visitas (sessions), pessoas (totalUsers) e visualizacoes de pagina
    (screenPageViews) num periodo do GA4 (strings tipo "yesterday",
    "today", "NdaysAgo" ou "YYYY-MM-DD" -- mesmo formato aceito pela Data
    API). Base de resumo_ultimos_dias (periodo corrido ate hoje) e de
    resumo_ontem (UM dia so, ja fechado -- ver docstring de resumo_ontem)."""
    cliente = _client()
    if cliente is None:
        return None
    from google.analytics.data_v1beta.types import DateRange, Metric, RunReportRequest

    try:
        resposta = cliente.run_report(
            RunReportRequest(
                property=f"properties/{GA4_PROPERTY_ID}",
                date_ranges=[DateRange(start_date=inicio, end_date=fim)],
                metrics=[Metric(name="sessions"), Metric(name="totalUsers"), Metric(name="screenPageViews")],
            )
        )
    except Exception:
        return None
    if not resposta.rows:
        return {"visitas": 0, "pessoas": 0, "visualizacoes": 0}
    valores = resposta.rows[0].metric_values
    return {
        "visitas": int(valores[0].value),
        "pessoas": int(valores[1].value),
        "visualizacoes": int(valores[2].value),
    }


def resumo_ultimos_dias(dias: int) -> dict | None:
    """Visitas/pessoas/visualizacoes nos ultimos `dias` dias ATE hoje --
    ver resumo_periodo. `dias=0` da "so hoje", mas ver a ressalva na
    docstring de resumo_ontem: o numero de hoje sozinho costuma vir 0."""
    return resumo_periodo(f"{dias}daysAgo", "today")


def resumo_ontem() -> dict | None:
    """Visitas/pessoas/visualizacoes de ONTEM (dia certo, ja fechado no
    GA4) -- ver conversa 2026-09-02: "Visitas hoje"/"Simulações de frete
    hoje" (resumo_ultimos_dias(0)/contagem_evento(..., 0)) usam o
    relatorio PADRAO do GA4, que so fecha os dados do dia atual no dia
    SEGUINTE -- na pratica isso mostra 0 (ou quase) o dia inteiro, nao e´
    bug daqui, e´ como a Data API funciona (so o relatorio em tempo real,
    usuarios_ativos_agora/contagem_evento_tempo_real, reflete na hora).
    "Ontem" e´ o numero mais recente confiavel desse relatorio."""
    return resumo_periodo("yesterday", "yesterday")


def paginas_mais_vistas(dias: int, limite: int = 10) -> list[dict] | None:
    """Paginas com mais visualizacao nos ultimos `dias` dias -- como
    cada produto tem sua propria URL (/produto/<id>), isso ja mostra
    "visualizacoes de um produto" sem precisar de configuracao extra
    no GA4 (dimensao padrao, funciona pra qualquer propriedade)."""
    cliente = _client()
    if cliente is None:
        return None
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, OrderBy, RunReportRequest

    try:
        resposta = cliente.run_report(
            RunReportRequest(
                property=f"properties/{GA4_PROPERTY_ID}",
                date_ranges=[DateRange(start_date=f"{dias}daysAgo", end_date="today")],
                dimensions=[Dimension(name="pagePath")],
                metrics=[Metric(name="screenPageViews")],
                order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
                limit=limite,
            )
        )
    except Exception:
        return None
    return [
        {"pagina": linha.dimension_values[0].value, "visualizacoes": int(linha.metric_values[0].value)}
        for linha in resposta.rows
    ]


def _contagem_evento_periodo(nome_evento: str, inicio: str, fim: str) -> int | None:
    cliente = _client()
    if cliente is None:
        return None
    from google.analytics.data_v1beta.types import DateRange, Dimension, Filter, FilterExpression, Metric, RunReportRequest

    try:
        resposta = cliente.run_report(
            RunReportRequest(
                property=f"properties/{GA4_PROPERTY_ID}",
                date_ranges=[DateRange(start_date=inicio, end_date=fim)],
                dimensions=[Dimension(name="eventName")],
                metrics=[Metric(name="eventCount")],
                dimension_filter=FilterExpression(
                    filter=Filter(
                        field_name="eventName",
                        string_filter=Filter.StringFilter(value=nome_evento),
                    )
                ),
            )
        )
    except Exception:
        return None
    if not resposta.rows:
        return 0
    return int(resposta.rows[0].metric_values[0].value)


def contagem_evento(nome_evento: str, dias: int) -> int | None:
    """Quantas vezes um evento (ver static/js/carrinho.js:rastrearEventoGA4)
    foi disparado nos ultimos `dias` dias ATE hoje -- usado pra "quantas
    pessoas simularam o frete" (evento calculate_shipping). `dias=0` tem
    a mesma ressalva de resumo_ontem: o numero de "so hoje" costuma vir
    0 (relatorio padrao do GA4 so fecha o dia atual no dia seguinte)."""
    return _contagem_evento_periodo(nome_evento, f"{dias}daysAgo", "today")


def contagem_evento_ontem(nome_evento: str) -> int | None:
    """Mesma ideia de resumo_ontem, pra um evento especifico -- numero de
    ONTEM (dia ja fechado no GA4), mais confiavel que o de "hoje"."""
    return _contagem_evento_periodo(nome_evento, "yesterday", "yesterday")


def contagem_evento_tempo_real(nome_evento: str) -> int | None:
    """Quantas vezes um evento disparou nos ULTIMOS ~30 MINUTOS (relatorio
    em tempo real do GA4, mesma fonte de usuarios_ativos_agora) -- ver
    conversa: o relatorio padrao usado em contagem_evento demora um
    tempo (minutos a horas) pra processar, entao um teste feito agora
    mesmo nao aparece la na hora. Esse aqui serve pra validar um teste
    na hora, sem esperar."""
    cliente = _client()
    if cliente is None:
        return None
    from google.analytics.data_v1beta.types import Dimension, Filter, FilterExpression, Metric, RunRealtimeReportRequest

    try:
        resposta = cliente.run_realtime_report(
            RunRealtimeReportRequest(
                property=f"properties/{GA4_PROPERTY_ID}",
                dimensions=[Dimension(name="eventName")],
                metrics=[Metric(name="eventCount")],
                dimension_filter=FilterExpression(
                    filter=Filter(
                        field_name="eventName",
                        string_filter=Filter.StringFilter(value=nome_evento),
                    )
                ),
            )
        )
    except Exception:
        return None
    if not resposta.rows:
        return 0
    return int(resposta.rows[0].metric_values[0].value)
