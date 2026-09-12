from __future__ import annotations

from datetime import date, datetime

import services.pedidos as pedidos


def test_domingo_de_pascoa_bate_com_datas_conhecidas():
    # datas de Pascoa publicamente conhecidas, conferidas independente
    # do algoritmo (Meeus/Jones/Butcher).
    esperado = {
        2020: date(2020, 4, 12),
        2023: date(2023, 4, 9),
        2024: date(2024, 3, 31),
        2025: date(2025, 4, 20),
        2026: date(2026, 4, 5),
        2027: date(2027, 3, 28),
    }
    for ano, data in esperado.items():
        assert pedidos._domingo_de_pascoa(ano) == data


def test_feriados_nacionais_2026_inclui_fixos_e_moveis():
    feriados = pedidos.feriados_nacionais(2026)
    assert date(2026, 1, 1) in feriados  # confraternizacao
    assert date(2026, 4, 21) in feriados  # tiradentes
    assert date(2026, 9, 7) in feriados  # independencia
    assert date(2026, 12, 25) in feriados  # natal
    assert date(2026, 4, 3) in feriados  # sexta-feira santa (pascoa 05/04 - 2 dias)
    assert date(2026, 6, 4) in feriados  # corpus christi (pascoa 05/04 + 60 dias)


def test_somar_dias_uteis_pula_feriado_nacional_no_meio_da_semana():
    # ver conversa: pedido postado sexta 04/09/2026, mas so foi de fato
    # encaminhado na terca 08/09 porque 07/09 (segunda) e feriado
    # nacional -- o site prometia entrega antecipada demais por nao
    # pular esse dia. Correios confirmou entrega em 14/09; com 5 dias
    # uteis de prazo (services/frete.py ja soma margem pra Correios) a
    # conta bate exatamente.
    enviado = datetime(2026, 9, 4, 18, 33)
    assert pedidos.somar_dias_uteis(enviado, 5).date() == date(2026, 9, 14)


def test_somar_dias_uteis_sem_feriado_no_meio_continua_igual_a_antes():
    # semana comum, sem feriado -- comportamento inalterado (so pula
    # sabado/domingo).
    segunda = datetime(2026, 8, 3, 10, 0)  # segunda-feira comum
    assert pedidos.somar_dias_uteis(segunda, 3).date() == date(2026, 8, 6)  # quinta
