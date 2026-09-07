from __future__ import annotations

from datetime import datetime, timezone

import pytest

import app as app_module
import services.pedidos as pedidos
from app import app


def test_formatar_data_hora_br_converte_utc_pra_horario_de_brasilia():
    """Ver conversa: horario aparecia 3h adiantado no painel porque os
    timestamps sao salvos em UTC (datetime.now(timezone.utc)) e eram
    mostrados sem converter pro fuso de Natal/Brasilia (UTC-3)."""
    utc_meia_noite = "2026-09-08T14:30:00+00:00"  # 14:30 UTC == 11:30 em Natal/Brasilia
    assert app_module._formatar_data_hora_br(utc_meia_noite) == "08/09/2026 11:30"


def test_formatar_data_hora_br_pode_virar_o_dia_anterior():
    """21h em Natal/Brasilia ja e´ meia-noite (ou depois) em UTC -- a
    conversao tem que devolver o dia CERTO do horario local, nao o dia
    UTC."""
    utc_madrugada = "2026-09-09T01:15:00+00:00"  # 01:15 UTC (09/09) == 22:15 (08/09) em Natal/Brasilia
    assert app_module._formatar_data_hora_br(utc_madrugada) == "08/09/2026 22:15"


def test_formatar_data_br_tambem_converte_fuso():
    utc_madrugada = "2026-09-09T01:15:00+00:00"
    assert app_module._formatar_data_br(utc_madrugada) == "08/09/2026"


def test_formatar_data_hora_br_com_none_devolve_vazio():
    assert app_module._formatar_data_hora_br(None) == ""


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def test_painel_de_pedidos_mostra_horario_convertido_pro_brasil(client, monkeypatch):
    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")

    criado = pedidos.criar_pedido(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "produtoId": "sao-jose"}],
        subtotal=100.0, frete_descricao="PAC", frete_preco=10.0,
        cliente={"nome": "Maria", "tipo_pessoa": "fisica", "documento": "11144477735",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua", "numero": "1", "complemento": "",
                  "bairro": "C", "cidade": "Natal", "uf": "RN"},
    )
    with pedidos._conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET criado_em = ? WHERE token = ?",
            ("2026-09-08T14:30:00+00:00", criado["token"]),
        )

    pagina = client.get("/admin/pedidos", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "08/09/2026 11:30" in pagina
    assert "14:30" not in pagina
