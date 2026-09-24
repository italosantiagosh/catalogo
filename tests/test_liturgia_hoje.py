from __future__ import annotations

import datetime

from services.liturgia_hoje import DIAS_SETEMBRO_2026, contexto_liturgia_de_hoje, liturgia_de_hoje
from services.liturgia_pdf import DIAS_OUTUBRO_2026
from app import app


def test_setembro_tem_30_dias_e_outubro_31():
    assert len(DIAS_SETEMBRO_2026) == 30
    assert len(DIAS_OUTUBRO_2026) == 31
    assert {d["dia"] for d in DIAS_SETEMBRO_2026} == set(range(1, 31))


def test_todo_dia_de_setembro_tem_cor_liturgica_valida():
    for info in DIAS_SETEMBRO_2026:
        assert info["cor_liturgica"] in ("branco", "vermelho", "verde")
        assert info["rank"] in ("solenidade", "festa", "obrigatoria", "facultativa", "comum")


def test_liturgia_de_hoje_em_setembro():
    info = liturgia_de_hoje(datetime.date(2026, 9, 3))
    assert info["titulo"] == "São Gregório Magno, papa e doutor da Igreja"
    assert info["rank"] == "obrigatoria"


def test_liturgia_de_hoje_em_outubro_reusa_dados_do_ebook():
    info = liturgia_de_hoje(datetime.date(2026, 10, 12))
    assert info["titulo"] == "Nossa Senhora Aparecida, padroeira do Brasil"
    assert info["rank"] == "solenidade"


def test_liturgia_de_hoje_fora_de_setembro_outubro_devolve_none():
    assert liturgia_de_hoje(datetime.date(2026, 11, 1)) is None
    assert liturgia_de_hoje(datetime.date(2026, 8, 15)) is None


def test_liturgia_de_hoje_em_outro_ano_devolve_none():
    """Dados conferidos so pra 2026 (leituras/calendario mudam a cada
    ano) -- em 2027 o widget precisa sumir, nao mostrar dado errado."""
    assert liturgia_de_hoje(datetime.date(2027, 9, 3)) is None


def test_contexto_pronto_pro_template():
    contexto = contexto_liturgia_de_hoje(datetime.date(2026, 9, 24))
    assert contexto == {
        "data_extenso": "24 de setembro",
        "titulo": "25ª Semana do Tempo Comum",
        "leituras": "Ecl 1,2-11 · Sl 89(90) · Lc 9,7-9",
        "rank_rotulo": "Tempo comum",
        "rank_cor_hex": "#3d6b4f",
        "cor_liturgica_rotulo": "Verde",
    }


def test_contexto_none_quando_sem_dado():
    assert contexto_liturgia_de_hoje(datetime.date(2026, 11, 1)) is None


def test_home_mostra_o_widget_quando_ha_dado_pro_dia(monkeypatch):
    # Nao depende do relogio real (o teste nao pode quebrar so porque
    # o dia mudou de mes/ano) -- fixa o retorno como se hoje tivesse dado.
    import app as app_module

    monkeypatch.setattr(
        app_module, "contexto_liturgia_de_hoje",
        lambda: {
            "data_extenso": "24 de setembro", "titulo": "25ª Semana do Tempo Comum",
            "leituras": "Ecl 1,2-11 · Sl 89(90) · Lc 9,7-9", "rank_rotulo": "Tempo comum",
            "rank_cor_hex": "#3d6b4f", "cor_liturgica_rotulo": "Verde",
        },
    )
    resposta = app.test_client().get("/")
    assert resposta.status_code == 200
    assert b'liturgia-hoje-card' in resposta.data
    assert b'liturgia-do-mes' in resposta.data


def test_home_esconde_o_widget_quando_nao_ha_dado(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "contexto_liturgia_de_hoje", lambda: None)
    resposta = app.test_client().get("/")
    assert resposta.status_code == 200
    assert b'liturgia-hoje-card' not in resposta.data
