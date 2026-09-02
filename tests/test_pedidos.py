from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import services.pedidos as pedidos


def _reapontar_db(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))


def _pedido_exemplo(**overrides):
    base = dict(
        itens=[{"chave_preco": "16mm", "quantidade": 30, "descricao": "São José — Modelo 1"}],
        subtotal=120.0,
        frete_descricao="Correios PAC — R$ 20,00",
        frete_preco=20.0,
        cliente={"nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "12345678900",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def test_criar_pedido_gera_token_longo_e_codigo_curto_diferentes(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    assert len(pedido["token"]) > 20  # token de URL -- longo, nao adivinhavel
    assert len(pedido["codigo"]) == 6  # codigo curto, so pra exibicao humana
    assert pedido["token"] != pedido["codigo"]
    assert pedido["status"] == "pendente"


def test_criar_pedido_soma_total_como_subtotal_mais_frete(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo(subtotal=120.0, frete_preco=20.0))
    assert pedido["total"] == 140.0


def test_obter_pedido_inexistente_devolve_none(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    assert pedidos.obter_pedido("token-que-nao-existe") is None


def test_obter_pedido_preserva_itens_como_lista(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    criado = pedidos.criar_pedido(**_pedido_exemplo())
    lido = pedidos.obter_pedido(criado["token"])
    assert lido["itens"] == [{"chave_preco": "16mm", "quantidade": 30, "descricao": "São José — Modelo 1"}]


def test_marcar_pago_atualiza_status_e_dados_do_pagamento(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    atualizado = pedidos.marcar_pago(
        pedido["token"], forma_pagamento="pix", parcelas=None, valor_pago=140.0, transaction_nsu="abc123"
    )
    assert atualizado["status"] == "pago"
    assert atualizado["forma_pagamento"] == "pix"
    assert atualizado["valor_pago"] == 140.0
    assert atualizado["transaction_nsu"] == "abc123"
    assert atualizado["pago_em"] is not None


def test_marcar_pago_e_idempotente_nao_reprocessa_webhook_repetido(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    primeiro = pedidos.marcar_pago(
        pedido["token"], forma_pagamento="pix", parcelas=None, valor_pago=140.0, transaction_nsu="abc123"
    )
    # segunda chamada com dados diferentes -- nao deve sobrescrever o
    # primeiro pagamento ja confirmado (webhook duplicado e comum)
    segundo = pedidos.marcar_pago(
        pedido["token"], forma_pagamento="credit_card", parcelas=3, valor_pago=999.0, transaction_nsu="outro"
    )
    assert segundo["forma_pagamento"] == "pix"
    assert segundo["transaction_nsu"] == "abc123"
    assert segundo["pago_em"] == primeiro["pago_em"]


def test_marcar_pago_pedido_inexistente_devolve_none(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    resultado = pedidos.marcar_pago(
        "token-que-nao-existe", forma_pagamento="pix", parcelas=None, valor_pago=10.0, transaction_nsu="x"
    )
    assert resultado is None


def test_marcar_email_pedido_criado_enviado(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    assert pedido["email_pedido_criado_enviado"] == 0

    atualizado = pedidos.marcar_email_pedido_criado_enviado(pedido["token"], erro=None)
    assert atualizado["email_pedido_criado_enviado"] == 1
    assert atualizado["email_pedido_criado_erro"] is None
    # nao mexe no e-mail de confirmacao de pagamento (coluna separada)
    assert atualizado["email_enviado"] == 0


def _envelhecer_pedido(token: str, minutos: int) -> None:
    passado = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
    with pedidos._conexao() as conexao:
        conexao.execute("UPDATE pedidos SET criado_em = ? WHERE token = ?", (passado, token))


def test_listar_pendentes_para_lembrete_ignora_pedido_recente(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedidos.criar_pedido(**_pedido_exemplo())
    assert pedidos.listar_pedidos_pendentes_para_lembrete(30) == []


def test_listar_pendentes_para_lembrete_pega_pedido_antigo(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    _envelhecer_pedido(pedido["token"], 40)

    resultado = pedidos.listar_pedidos_pendentes_para_lembrete(30)
    assert len(resultado) == 1
    assert resultado[0]["token"] == pedido["token"]


def test_listar_pendentes_para_lembrete_ignora_ja_notificado(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    _envelhecer_pedido(pedido["token"], 40)
    pedidos.marcar_email_lembrete_enviado(pedido["token"], erro=None)
    assert pedidos.listar_pedidos_pendentes_para_lembrete(30) == []


def test_listar_pendentes_para_lembrete_ignora_pedido_pago(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    _envelhecer_pedido(pedido["token"], 40)
    pedidos.marcar_pago(
        pedido["token"], forma_pagamento="pix", parcelas=None, valor_pago=140.0, transaction_nsu="x"
    )
    assert pedidos.listar_pedidos_pendentes_para_lembrete(30) == []


def test_atualizar_status_faturado_grava_timestamp(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    atualizado = pedidos.atualizar_status(pedido["token"], "faturado")
    assert atualizado["status"] == "faturado"
    assert atualizado["faturado_em"] is not None
    assert atualizado["enviado_em"] is None


def test_atualizar_status_enviado_grava_rastreio(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    atualizado = pedidos.atualizar_status(
        pedido["token"], "enviado", codigo_rastreio="BR123456789BR", link_rastreio="https://rastreio.exemplo/BR123"
    )
    assert atualizado["status"] == "enviado"
    assert atualizado["enviado_em"] is not None
    assert atualizado["codigo_rastreio"] == "BR123456789BR"
    assert atualizado["link_rastreio"] == "https://rastreio.exemplo/BR123"


def test_atualizar_status_entregue_preserva_rastreio_anterior(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    pedidos.atualizar_status(pedido["token"], "enviado", codigo_rastreio="BR123456789BR", link_rastreio=None)
    atualizado = pedidos.atualizar_status(pedido["token"], "entregue")
    assert atualizado["status"] == "entregue"
    assert atualizado["entregue_em"] is not None
    # nao apaga o rastreio ja registrado, so nao veio um novo dessa vez
    assert atualizado["codigo_rastreio"] == "BR123456789BR"


def test_atualizar_status_invalido_devolve_none(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    assert pedidos.atualizar_status(pedido["token"], "cancelado_inventado") is None


def test_atualizar_status_pedido_inexistente_devolve_none(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    assert pedidos.atualizar_status("token-que-nao-existe", "faturado") is None


def test_arquivar_pedido_marca_arquivado_e_nao_muda_status(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    pedidos.marcar_pago(pedido["token"], forma_pagamento="pix", parcelas=None, valor_pago=140.0, transaction_nsu="123")

    atualizado = pedidos.arquivar_pedido(pedido["token"])
    assert atualizado["arquivado"] == 1
    assert atualizado["arquivado_em"] is not None
    assert atualizado["status"] == "pago"


def test_desarquivar_pedido_reverte(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    pedidos.arquivar_pedido(pedido["token"])

    atualizado = pedidos.desarquivar_pedido(pedido["token"])
    assert atualizado["arquivado"] == 0
    assert atualizado["arquivado_em"] is None


def test_arquivar_pedido_inexistente_devolve_none(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    assert pedidos.arquivar_pedido("token-que-nao-existe") is None
    assert pedidos.desarquivar_pedido("token-que-nao-existe") is None


def test_listar_pedidos_por_padrao_esconde_arquivados(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    visivel = pedidos.criar_pedido(**_pedido_exemplo())
    arquivado = pedidos.criar_pedido(**_pedido_exemplo())
    pedidos.arquivar_pedido(arquivado["token"])

    tokens = {p["token"] for p in pedidos.listar_pedidos()}
    assert visivel["token"] in tokens
    assert arquivado["token"] not in tokens

    tokens_arquivados = {p["token"] for p in pedidos.listar_pedidos(arquivados=True)}
    assert tokens_arquivados == {arquivado["token"]}


def test_marcar_email_lembrete_enviado(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    atualizado = pedidos.marcar_email_lembrete_enviado(pedido["token"], erro="falhou")
    assert atualizado["email_lembrete_enviado"] == 1
    assert atualizado["email_lembrete_erro"] == "falhou"


def test_banco_antigo_ganha_as_colunas_novas_sem_quebrar(monkeypatch, tmp_path):
    """Simula um pedidos.db criado antes das colunas tiny_*/email_*/
    endereco_destinatario_* existirem -- CREATE TABLE IF NOT EXISTS
    sozinho NAO adiciona coluna nova a uma tabela que ja existe, entao
    isso so funciona por causa da migracao em inicializar_db()."""
    caminho_db = str(tmp_path / "pedidos_antigo.db")
    monkeypatch.setattr(pedidos, "DB_PATH", caminho_db)

    conexao_antiga = sqlite3.connect(caminho_db)
    conexao_antiga.execute(
        """
        CREATE TABLE pedidos (
            token TEXT PRIMARY KEY,
            codigo TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendente',
            itens TEXT NOT NULL,
            subtotal REAL NOT NULL,
            frete_descricao TEXT,
            frete_preco REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL,
            cliente_nome TEXT,
            cliente_tipo_pessoa TEXT,
            cliente_documento TEXT,
            cliente_telefone TEXT,
            cliente_email TEXT,
            endereco_cep TEXT,
            endereco_logradouro TEXT,
            endereco_numero TEXT,
            endereco_complemento TEXT,
            endereco_bairro TEXT,
            endereco_cidade TEXT,
            endereco_uf TEXT,
            forma_pagamento TEXT,
            parcelas INTEGER,
            valor_pago REAL,
            transaction_nsu TEXT,
            criado_em TEXT NOT NULL,
            pago_em TEXT
        )
        """
    )
    conexao_antiga.commit()
    conexao_antiga.close()

    # nao deve estourar "sqlite3.OperationalError: no such column"
    pedido = pedidos.criar_pedido(**_pedido_exemplo())
    assert pedido["tiny_sincronizado"] == 0
    assert pedido["endereco_destinatario_nome"] == ""

    atualizado = pedidos.marcar_tiny_sincronizado(pedido["token"], numero_pedido="42", erro=None)
    assert atualizado["tiny_numero_pedido"] == "42"


def _marcar_pago_em(token: str, quando: datetime) -> None:
    with pedidos._conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET status = 'pago', pago_em = ? WHERE token = ?", (quando.isoformat(), token)
        )


def _marcar_enviado_em(token: str, quando: datetime) -> None:
    with pedidos._conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET status = 'enviado', enviado_em = ? WHERE token = ?", (quando.isoformat(), token)
        )


def test_previsoes_marca_enviado_antecipado_e_recalcula_entrega_pelo_envio_real(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    monkeypatch.setattr(pedidos, "PRODUCAO_DIAS_UTEIS", 5)
    pedido = pedidos.criar_pedido(**_pedido_exemplo(frete_prazo_dias=7))
    # segunda-feira 04/11/2024 -- previsao de envio (+5 dias uteis) cai em 11/11 (segunda)
    pago_em = datetime(2024, 11, 4, tzinfo=timezone.utc)
    _marcar_pago_em(pedido["token"], pago_em)
    # mas o pedido saiu bem antes do prometido: quarta 06/11
    enviado_em = datetime(2024, 11, 6, tzinfo=timezone.utc)
    _marcar_enviado_em(pedido["token"], enviado_em)

    previsoes = pedidos.previsoes_do_pedido(pedidos.obter_pedido(pedido["token"]))
    assert previsoes["previsao_envio"].date().isoformat() == "2024-11-11"
    assert previsoes["enviado_antecipado"] is True
    # entrega recalculada a partir do envio REAL (06/11), nao da promessa original (11/11)
    esperado = pedidos.somar_dias_uteis(enviado_em, 7)
    assert previsoes["previsao_entrega"].date().isoformat() == esperado.date().isoformat()


def test_previsoes_nao_marca_antecipado_quando_envio_nao_foi_adiantado(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    monkeypatch.setattr(pedidos, "PRODUCAO_DIAS_UTEIS", 5)
    pedido = pedidos.criar_pedido(**_pedido_exemplo(frete_prazo_dias=7))
    pago_em = datetime(2024, 11, 4, tzinfo=timezone.utc)
    _marcar_pago_em(pedido["token"], pago_em)
    # previsao de envio era 11/11 -- saiu depois, no dia 12/11
    enviado_em = datetime(2024, 11, 12, tzinfo=timezone.utc)
    _marcar_enviado_em(pedido["token"], enviado_em)

    previsoes = pedidos.previsoes_do_pedido(pedidos.obter_pedido(pedido["token"]))
    assert previsoes["enviado_antecipado"] is False


def test_previsoes_sem_envio_ainda_nao_marca_antecipado(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedido = pedidos.criar_pedido(**_pedido_exemplo(frete_prazo_dias=7))
    _marcar_pago_em(pedido["token"], datetime(2024, 11, 4, tzinfo=timezone.utc))

    previsoes = pedidos.previsoes_do_pedido(pedidos.obter_pedido(pedido["token"]))
    assert previsoes["enviado_antecipado"] is False
    assert previsoes["previsao_entrega"] is not None


def test_estatisticas_hoje_conta_pedidos_criados_hoje(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedidos.criar_pedido(**_pedido_exemplo())
    outro = pedidos.criar_pedido(**_pedido_exemplo())
    # criado ontem -- nao deve contar como "hoje"
    ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    with pedidos._conexao() as conexao:
        conexao.execute("UPDATE pedidos SET criado_em = ? WHERE token = ?", (ontem, outro["token"]))

    stats = pedidos.estatisticas_hoje()
    assert stats["pedidos_hoje"] == 1


def test_estatisticas_hoje_soma_faturamento_so_de_vendas_pagas_hoje(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pago_hoje = pedidos.criar_pedido(**_pedido_exemplo(subtotal=100.0, frete_preco=0.0))
    pedidos.marcar_pago(pago_hoje["token"], forma_pagamento="pix", parcelas=None, valor_pago=100.0, transaction_nsu="tx1")

    pago_ontem = pedidos.criar_pedido(**_pedido_exemplo(subtotal=50.0, frete_preco=0.0))
    pedidos.marcar_pago(pago_ontem["token"], forma_pagamento="pix", parcelas=None, valor_pago=50.0, transaction_nsu="tx2")
    _marcar_pago_em(pago_ontem["token"], datetime.now(timezone.utc) - timedelta(days=1))

    # ainda pendente -- nunca deve entrar no faturamento
    pedidos.criar_pedido(**_pedido_exemplo(subtotal=999.0, frete_preco=0.0))

    stats = pedidos.estatisticas_hoje()
    assert stats["vendas_hoje"] == 1
    assert stats["faturamento_hoje"] == 100.0


def test_estatisticas_hoje_conta_pendentes_e_whatsapp_independente_da_data(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pendente = pedidos.criar_pedido(**_pedido_exemplo())
    antigo = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    with pedidos._conexao() as conexao:
        conexao.execute("UPDATE pedidos SET criado_em = ? WHERE token = ?", (antigo, pendente["token"]))
    pedidos.criar_pedido(**_pedido_exemplo(status_inicial="whatsapp"))
    pago = pedidos.criar_pedido(**_pedido_exemplo())
    pedidos.marcar_pago(pago["token"], forma_pagamento="pix", parcelas=None, valor_pago=140.0, transaction_nsu="tx3")

    stats = pedidos.estatisticas_hoje()
    assert stats["pendentes"] == 2


def test_vendas_por_dia_preenche_dias_sem_venda_com_zero(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    hoje_pago = pedidos.criar_pedido(**_pedido_exemplo(subtotal=100.0, frete_preco=0.0))
    pedidos.marcar_pago(hoje_pago["token"], forma_pagamento="pix", parcelas=None, valor_pago=100.0, transaction_nsu="tx1")

    resultado = pedidos.vendas_por_dia(3)
    assert len(resultado) == 3
    assert resultado[-1]["quantidade"] == 1
    assert resultado[-1]["valor"] == 100.0
    assert resultado[0]["quantidade"] == 0
    assert resultado[0]["valor"] == 0.0


def test_vendas_por_dia_soma_mais_de_uma_venda_no_mesmo_dia(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    p1 = pedidos.criar_pedido(**_pedido_exemplo(subtotal=100.0, frete_preco=0.0))
    pedidos.marcar_pago(p1["token"], forma_pagamento="pix", parcelas=None, valor_pago=100.0, transaction_nsu="tx1")
    p2 = pedidos.criar_pedido(**_pedido_exemplo(subtotal=50.0, frete_preco=0.0))
    pedidos.marcar_pago(p2["token"], forma_pagamento="pix", parcelas=None, valor_pago=50.0, transaction_nsu="tx2")

    resultado = pedidos.vendas_por_dia(1)
    assert resultado[0]["quantidade"] == 2
    assert resultado[0]["valor"] == 150.0


def test_pedidos_por_uf_usa_uf_do_destinatario_quando_diferente(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    normal = pedidos.criar_pedido(**_pedido_exemplo(endereco={
        "cep": "59000000", "logradouro": "Rua A", "numero": "1", "complemento": "",
        "bairro": "Centro", "cidade": "Natal", "uf": "RN",
    }))
    pedidos.marcar_pago(normal["token"], forma_pagamento="pix", parcelas=None, valor_pago=140.0, transaction_nsu="tx1")

    com_destinatario = pedidos.criar_pedido(**_pedido_exemplo(endereco={
        "cep": "59000000", "logradouro": "Rua B", "numero": "2", "complemento": "",
        "bairro": "Centro", "cidade": "Natal", "uf": "RN",
        "destinatario_nome": "Livraria", "destinatario_tipo_pessoa": "juridica",
        "destinatario_documento": "11222333000181",
        "destinatario_cep": "80000000", "destinatario_logradouro": "Rua C", "destinatario_numero": "3",
        "destinatario_complemento": "", "destinatario_bairro": "Centro", "destinatario_cidade": "Curitiba",
        "destinatario_uf": "PR", "destinatario_telefone": "",
    }))
    pedidos.marcar_pago(com_destinatario["token"], forma_pagamento="pix", parcelas=None, valor_pago=140.0, transaction_nsu="tx2")

    resultado = {r["uf"]: r["quantidade"] for r in pedidos.pedidos_por_uf(7)}
    assert resultado == {"RN": 1, "PR": 1}


def test_taxa_cancelamento_ignora_lead_whatsapp(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pedidos.criar_pedido(**_pedido_exemplo(status_inicial="whatsapp"))
    cancelado = pedidos.criar_pedido(**_pedido_exemplo())
    pedidos.cancelar_pedido(cancelado["token"])
    pedidos.criar_pedido(**_pedido_exemplo())  # pendente

    resultado = pedidos.taxa_cancelamento(7)
    assert resultado["total"] == 2  # so o cancelado + o pendente, nao o lead whatsapp
    assert resultado["cancelados"] == 1
    assert resultado["taxa_pct"] == 50.0


def test_formas_pagamento_periodo_normaliza_rotulos(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    pix = pedidos.criar_pedido(**_pedido_exemplo(subtotal=100.0, frete_preco=0.0))
    pedidos.marcar_pago(pix["token"], forma_pagamento="pix", parcelas=None, valor_pago=100.0, transaction_nsu="tx1")
    cartao = pedidos.criar_pedido(**_pedido_exemplo(subtotal=50.0, frete_preco=0.0))
    pedidos.marcar_pago(cartao["token"], forma_pagamento="credit_card", parcelas=3, valor_pago=50.0, transaction_nsu="tx2")

    resultado = {r["forma"]: r for r in pedidos.formas_pagamento_periodo(7)}
    assert resultado["Pix"]["quantidade"] == 1
    assert resultado["Pix"]["valor"] == 100.0
    assert resultado["Cartão de crédito"]["quantidade"] == 1
    assert resultado["Cartão de crédito"]["valor"] == 50.0


def test_produtos_mais_vendidos_soma_quantidade_por_nome(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    p1 = pedidos.criar_pedido(**_pedido_exemplo(
        itens=[{"chave_preco": "16mm", "quantidade": 20, "produtoNome": "São José"}],
        subtotal=100.0, frete_preco=0.0,
    ))
    pedidos.marcar_pago(p1["token"], forma_pagamento="pix", parcelas=None, valor_pago=100.0, transaction_nsu="tx1")
    p2 = pedidos.criar_pedido(**_pedido_exemplo(
        itens=[{"chave_preco": "16mm", "quantidade": 5, "produtoNome": "São José"},
               {"chave_preco": "12mm", "quantidade": 3}],  # sem produtoNome -- personalizada
        subtotal=40.0, frete_preco=0.0,
    ))
    pedidos.marcar_pago(p2["token"], forma_pagamento="pix", parcelas=None, valor_pago=40.0, transaction_nsu="tx2")

    resultado = {r["produto"]: r["quantidade"] for r in pedidos.produtos_mais_vendidos(7)}
    assert resultado["São José"] == 25
    assert resultado["Personalizada"] == 3


def test_taxa_clientes_recorrentes_conta_so_quem_ja_comprou_antes(monkeypatch, tmp_path):
    _reapontar_db(monkeypatch, tmp_path)
    cliente_novo = pedidos.criar_pedido(**_pedido_exemplo(
        cliente={"nome": "Nova", "tipo_pessoa": "fisica", "documento": "11111111111",
                 "telefone": "84999999999", "email": "nova@example.com"},
    ))
    pedidos.marcar_pago(cliente_novo["token"], forma_pagamento="pix", parcelas=None, valor_pago=140.0, transaction_nsu="tx1")

    doc_recorrente = "22222222222"
    compra_antiga = pedidos.criar_pedido(**_pedido_exemplo(
        cliente={"nome": "Recorrente", "tipo_pessoa": "fisica", "documento": doc_recorrente,
                 "telefone": "84999999999", "email": "r@example.com"},
    ))
    _marcar_pago_em(compra_antiga["token"], datetime.now(timezone.utc) - timedelta(days=30))
    compra_nova = pedidos.criar_pedido(**_pedido_exemplo(
        cliente={"nome": "Recorrente", "tipo_pessoa": "fisica", "documento": doc_recorrente,
                 "telefone": "84999999999", "email": "r@example.com"},
    ))
    pedidos.marcar_pago(compra_nova["token"], forma_pagamento="pix", parcelas=None, valor_pago=140.0, transaction_nsu="tx2")

    resultado = pedidos.taxa_clientes_recorrentes(7)
    assert resultado["total"] == 2
    assert resultado["recorrentes"] == 1
    assert resultado["taxa_pct"] == 50.0
