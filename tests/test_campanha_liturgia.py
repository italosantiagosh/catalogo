from __future__ import annotations

from unittest.mock import patch

import pytest

import services.carrinhos_abandonados as carrinhos_abandonados
import services.pedidos as pedidos
from app import app, _enviar_lote_campanha_convite_liturgia


@pytest.fixture
def client(monkeypatch, tmp_path):
    import app as app_module

    db_path = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(pedidos, "DB_PATH", db_path)
    monkeypatch.setattr(carrinhos_abandonados, "DB_PATH", db_path)
    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
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


def _criar_pago(client, **overrides) -> str:
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido(**overrides)).get_json()
    token = criado["token"]
    pedidos.marcar_pago(token, forma_pagamento="pix", parcelas=None, valor_pago=100.0, transaction_nsu="nsu-1")
    return token


def _criar_pendente(client, **overrides) -> str:
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido(**overrides)).get_json()
    return criado["token"]


# ---- services/pedidos.py ----

def test_preparar_campanha_so_pega_pedido_pago(client):
    _criar_pendente(client, cliente={"nome": "Pendente", "tipo_pessoa": "fisica", "documento": "11144477735",
                                      "telefone": "84999999999", "email": "pendente@example.com"})
    _criar_pago(client, cliente={"nome": "Paga", "tipo_pessoa": "fisica", "documento": "11144477735",
                                  "telefone": "84999999999", "email": "paga@example.com"})

    novos = pedidos.preparar_campanha_convite_liturgia()

    assert novos == 1
    contagem = pedidos.contar_campanha_convite_liturgia()
    assert contagem == {"total": 1, "enviados": 0, "pendentes": 1, "com_erro": 0}


def test_preparar_campanha_dedupe_por_email_usa_nome_mais_recente(client):
    _criar_pago(client, cliente={"nome": "Nome Antigo", "tipo_pessoa": "fisica", "documento": "11144477735",
                                  "telefone": "84999999999", "email": "repetida@example.com"})
    _criar_pago(client, cliente={"nome": "Nome Novo", "tipo_pessoa": "fisica", "documento": "11144477735",
                                  "telefone": "84999999999", "email": "REPETIDA@example.com"})

    novos = pedidos.preparar_campanha_convite_liturgia()

    assert novos == 1
    pendentes = pedidos.listar_pendentes_campanha_convite_liturgia(10)
    assert len(pendentes) == 1
    assert pendentes[0]["email"] == "repetida@example.com"
    assert pendentes[0]["nome"] == "Nome Novo"


def test_preparar_campanha_e_idempotente(client):
    _criar_pago(client)
    assert pedidos.preparar_campanha_convite_liturgia() == 1
    assert pedidos.preparar_campanha_convite_liturgia() == 0
    assert pedidos.contar_campanha_convite_liturgia()["total"] == 1


def test_marcar_enviado_sai_dos_pendentes(client):
    _criar_pago(client)
    pedidos.preparar_campanha_convite_liturgia()
    email = pedidos.listar_pendentes_campanha_convite_liturgia(10)[0]["email"]

    pedidos.marcar_campanha_convite_liturgia_enviado(email, erro=None)

    assert pedidos.listar_pendentes_campanha_convite_liturgia(10) == []
    contagem = pedidos.contar_campanha_convite_liturgia()
    assert contagem == {"total": 1, "enviados": 1, "pendentes": 0, "com_erro": 0}


def test_marcar_com_erro_continua_pendente(client):
    _criar_pago(client)
    pedidos.preparar_campanha_convite_liturgia()
    email = pedidos.listar_pendentes_campanha_convite_liturgia(10)[0]["email"]

    pedidos.marcar_campanha_convite_liturgia_enviado(email, erro="falha de rede")

    assert len(pedidos.listar_pendentes_campanha_convite_liturgia(10)) == 1
    assert pedidos.contar_campanha_convite_liturgia()["com_erro"] == 1


def test_listar_pendentes_respeita_limite(client):
    for i in range(3):
        _criar_pago(client, cliente={"nome": f"Cliente {i}", "tipo_pessoa": "fisica", "documento": "11144477735",
                                      "telefone": "84999999999", "email": f"cliente{i}@example.com"})
    pedidos.preparar_campanha_convite_liturgia()

    assert len(pedidos.listar_pendentes_campanha_convite_liturgia(2)) == 2
    assert len(pedidos.listar_pendentes_campanha_convite_liturgia(10)) == 3


# ---- app.py: job agendado ----

def test_job_sem_canonical_domain_nao_manda_nada(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "")
    _criar_pago(client)
    pedidos.preparar_campanha_convite_liturgia()

    with patch("app.enviar_convite_liturgia_mensal") as mock_email:
        _enviar_lote_campanha_convite_liturgia()
    mock_email.assert_not_called()


def test_job_manda_ate_o_limite_diario_e_marca_enviado(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "LIMITE_DIARIO_CAMPANHA_LITURGIA", 2)
    for i in range(3):
        _criar_pago(client, cliente={"nome": f"Cliente {i}", "tipo_pessoa": "fisica", "documento": "11144477735",
                                      "telefone": "84999999999", "email": f"cliente{i}@example.com"})
    pedidos.preparar_campanha_convite_liturgia()

    with patch("app.enviar_convite_liturgia_mensal", return_value={"ok": True}) as mock_email:
        _enviar_lote_campanha_convite_liturgia()

    assert mock_email.call_count == 2
    assert mock_email.call_args_list[0].args[2] == "https://lojanovedejulho.com.br/liturgia-do-mes"
    contagem = pedidos.contar_campanha_convite_liturgia()
    assert contagem["enviados"] == 2
    assert contagem["pendentes"] == 1


def test_job_respeita_janela_movel_de_24h_entre_duas_chamadas(client, monkeypatch):
    """Ver conversa 2026-09-25: o teto vale por janela movel de 24h, nao
    por chamada -- chamar a funcao 2x seguidas (ex: clique manual +
    job automatico) no mesmo dia nunca manda mais que o limite."""
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "LIMITE_DIARIO_CAMPANHA_LITURGIA", 2)
    for i in range(3):
        _criar_pago(client, cliente={"nome": f"Cliente {i}", "tipo_pessoa": "fisica", "documento": "11144477735",
                                      "telefone": "84999999999", "email": f"cliente{i}@example.com"})
    pedidos.preparar_campanha_convite_liturgia()

    with patch("app.enviar_convite_liturgia_mensal", return_value={"ok": True}) as mock_email:
        primeiro = _enviar_lote_campanha_convite_liturgia()
        segundo = _enviar_lote_campanha_convite_liturgia()

    assert primeiro == 2
    assert segundo == 0
    assert mock_email.call_count == 2
    assert pedidos.contar_campanha_convite_liturgia()["pendentes"] == 1


def test_job_marca_erro_quando_envio_falha(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    _criar_pago(client)
    pedidos.preparar_campanha_convite_liturgia()

    with patch("app.enviar_convite_liturgia_mensal", return_value={"erro": "Brevo fora do ar"}):
        _enviar_lote_campanha_convite_liturgia()

    contagem = pedidos.contar_campanha_convite_liturgia()
    assert contagem["enviados"] == 0
    assert contagem["com_erro"] == 1


# ---- rota admin ----

def test_admin_preparar_exige_autenticacao(client):
    resposta = client.post("/admin/campanha-liturgia/preparar")
    assert resposta.status_code == 401


def test_admin_preparar_popula_e_devolve_contagem(client):
    _criar_pago(client)
    resposta = client.post("/admin/campanha-liturgia/preparar", auth=("admin", "segredo123"))
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["ok"] is True
    assert dados["novos"] == 1
    assert dados["total"] == 1
    assert dados["pendentes"] == 1


def test_admin_preparar_e_seguro_chamar_duas_vezes(client):
    _criar_pago(client)
    client.post("/admin/campanha-liturgia/preparar", auth=("admin", "segredo123"))
    resposta = client.post("/admin/campanha-liturgia/preparar", auth=("admin", "segredo123"))
    dados = resposta.get_json()
    assert dados["novos"] == 0
    assert dados["total"] == 1


# ---- exportacao em CSV (ver conversa 2026-09-24: usuario prefere CSV
# manual em vez do envio automatico, pedidos antigos de antes desta
# loja nao entram nesta base) ----

def test_clientes_pagos_distintos_ignora_pendente(client):
    _criar_pendente(client, cliente={"nome": "Pendente", "tipo_pessoa": "fisica", "documento": "11144477735",
                                      "telefone": "84999999999", "email": "pendente@example.com"})
    _criar_pago(client, cliente={"nome": "Paga", "tipo_pessoa": "fisica", "documento": "11144477735",
                                  "telefone": "84999999999", "email": "paga@example.com"})

    clientes = pedidos.clientes_pagos_distintos()

    assert clientes == [{"email": "paga@example.com", "nome": "Paga"}]


def test_csv_exige_autenticacao(client):
    resposta = client.get("/admin/campanha-liturgia/exportar.csv")
    assert resposta.status_code == 401


def test_csv_tem_cabecalho_e_uma_linha_por_cliente(client):
    _criar_pago(client, cliente={"nome": "Maria", "tipo_pessoa": "fisica", "documento": "11144477735",
                                  "telefone": "84999999999", "email": "maria@example.com"})
    _criar_pago(client, cliente={"nome": "João", "tipo_pessoa": "fisica", "documento": "11144477735",
                                  "telefone": "84999999999", "email": "joao@example.com"})

    resposta = client.get("/admin/campanha-liturgia/exportar.csv", auth=("admin", "segredo123"))

    assert resposta.status_code == 200
    assert resposta.headers["Content-Type"].startswith("text/csv")
    assert "attachment" in resposta.headers["Content-Disposition"]
    conteudo = resposta.data.decode("utf-8-sig")
    linhas = conteudo.strip().splitlines()
    assert linhas[0] == "E-mail;Nome"
    assert len(linhas) == 3
    assert "maria@example.com;Maria" in linhas
    assert "joao@example.com;João" in linhas


def test_csv_nao_precisa_da_fila_de_campanha_ja_preparada(client):
    """O CSV le direto de pedidos, nao depende de alguem ja ter clicado
    em "Buscar clientes que ja compraram" antes."""
    _criar_pago(client)
    resposta = client.get("/admin/campanha-liturgia/exportar.csv", auth=("admin", "segredo123"))
    linhas = resposta.data.decode("utf-8-sig").strip().splitlines()
    assert len(linhas) == 2


# ---- importacao de planilha de clientes antigos (ver conversa
# 2026-09-24: "foram todos aqueles que subi naquela campanha... queria
# algo parecido, pra eu subir aquelas planilhas e fazer o crivo") ----

def _upload(client, conteudo: str, nome_arquivo: str = "clientes.csv", **auth_kwargs):
    import io

    dados = {"arquivo": (io.BytesIO(conteudo.encode("utf-8")), nome_arquivo)}
    kwargs = auth_kwargs or {"auth": ("admin", "segredo123")}
    return client.post(
        "/admin/campanha-liturgia/importar", data=dados, content_type="multipart/form-data", **kwargs
    )


def test_importar_exige_autenticacao(client):
    resposta = _upload(client, "email;nome\nfulano@example.com;Fulano\n", auth=None)
    assert resposta.status_code == 401


def test_importar_com_ponto_e_virgula(client):
    resposta = _upload(client, "Email;Nome\nfulano@example.com;Fulano de Tal\nciclano@example.com;Ciclano\n")
    dados = resposta.get_json()
    assert resposta.status_code == 200
    assert dados["linhas_lidas"] == 2
    assert dados["novos"] == 2
    assert dados["total"] == 2


def test_importar_com_virgula(client):
    resposta = _upload(client, "email,nome\nfulano@example.com,Fulano\n")
    dados = resposta.get_json()
    assert dados["linhas_lidas"] == 1
    assert dados["novos"] == 1


def test_importar_nao_duplica_quem_ja_esta_na_fila(client):
    _upload(client, "email;nome\nfulano@example.com;Fulano\n")
    resposta = _upload(client, "email;nome\nfulano@example.com;Fulano de Novo\nnovo@example.com;Novo\n")
    dados = resposta.get_json()
    assert dados["linhas_lidas"] == 2
    assert dados["novos"] == 1
    assert dados["total"] == 2


def test_importar_sem_coluna_de_email_da_erro(client):
    resposta = _upload(client, "nome;telefone\nFulano;84999999999\n")
    assert resposta.status_code == 400
    assert "e-mail" in resposta.get_json()["erro"].lower()


def test_importar_sem_arquivo_da_erro(client):
    resposta = client.post("/admin/campanha-liturgia/importar", auth=("admin", "segredo123"))
    assert resposta.status_code == 400


def test_importar_nao_mexe_na_lista_de_newsletter_de_verdade(client):
    """So entra na fila de convite -- nunca chama inscrever_newsletter
    nem toca na lista real do Brevo."""
    with patch("app.inscrever_newsletter") as mock_inscrever:
        _upload(client, "email;nome\nfulano@example.com;Fulano\n")
    mock_inscrever.assert_not_called()


# ---- botao "Enviar agora" (ver conversa 2026-09-25: "como faço pra
# enviar a campanha só pra 200 hj") ----

def test_enviar_agora_exige_autenticacao(client):
    resposta = client.post("/admin/campanha-liturgia/enviar-agora")
    assert resposta.status_code == 401


def test_enviar_agora_manda_o_lote_na_hora(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    _criar_pago(client)
    pedidos.preparar_campanha_convite_liturgia()

    with patch("app.enviar_convite_liturgia_mensal", return_value={"ok": True}):
        resposta = client.post("/admin/campanha-liturgia/enviar-agora", auth=("admin", "segredo123"))

    dados = resposta.get_json()
    assert resposta.status_code == 200
    assert dados["enviados_agora"] == 1
    assert dados["enviados"] == 1
    assert dados["pendentes"] == 0


def test_enviar_agora_duas_vezes_no_mesmo_dia_nao_estoura_o_teto(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    monkeypatch.setattr(app_module, "LIMITE_DIARIO_CAMPANHA_LITURGIA", 1)
    for i in range(2):
        _criar_pago(client, cliente={"nome": f"Cliente {i}", "tipo_pessoa": "fisica", "documento": "11144477735",
                                      "telefone": "84999999999", "email": f"cliente{i}@example.com"})
    pedidos.preparar_campanha_convite_liturgia()

    with patch("app.enviar_convite_liturgia_mensal", return_value={"ok": True}):
        primeira = client.post("/admin/campanha-liturgia/enviar-agora", auth=("admin", "segredo123")).get_json()
        segunda = client.post("/admin/campanha-liturgia/enviar-agora", auth=("admin", "segredo123")).get_json()

    assert primeira["enviados_agora"] == 1
    assert segunda["enviados_agora"] == 0
    assert segunda["pendentes"] == 1
