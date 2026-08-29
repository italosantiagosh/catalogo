"""
Persistencia de pedidos pagos via InfinitePay -- ver services/infinitepay.py
e app.py (/api/pedido/criar, /webhook/infinitepay, /pedido/<token>).

Usa SQLite (biblioteca padrao, sem dependencia nova) -- guarda o pedido
assim que o cliente clica em "Pagar agora" (status "pendente") e marca
como "pago" quando o webhook da InfinitePay confirma o pagamento.

IMPORTANTE (producao/Render): por padrao o arquivo fica em
data/pedidos.db, no mesmo disco da aplicacao -- se esse disco NAO for
persistente (padrao do Render pra web services), o banco e apagado a
cada redeploy/restart e os pedidos "somem", quebrando a pagina de
acompanhamento de pedidos ja pagos. Configure um Persistent Disk no
Render e aponte PEDIDOS_DB_PATH pra um caminho dentro dele antes de
depender disso pra pedidos de verdade.

O token usado na URL de acompanhamento (/pedido/<token>) e´ longo e
aleatorio (secrets.token_urlsafe) de proposito -- e´ diferente do codigo
curto de 6 caracteres (so pra referencia humana, ja usado no WhatsApp
via carrinho.js) porque esse token vira uma URL que mostra dados
pessoais do cliente: um codigo curto seria adivinhavel por forca bruta.
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import PRODUCAO_DIAS_UTEIS

DB_PATH = os.environ.get(
    "PEDIDOS_DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "pedidos.db")
)

# Mesmo criterio do codigo curto gerado no navegador (carrinho.js:
# PEDIDO_ID_CHARSET) -- sem O/0, I/1, evita confusao ao ler em voz alta.
_CODIGO_CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _gerar_codigo() -> str:
    return "".join(secrets.choice(_CODIGO_CHARSET) for _ in range(6))


@contextmanager
def _conexao():
    # timeout=30 + WAL: sem isso, qualquer escrita concorrente (job
    # agendado, webhook, um script rodando por fora tipo
    # scripts/migrar_*) podia derrubar com "database is locked" na
    # hora, mesmo sendo uma escrita rapida -- visto na pratica rodando
    # a migracao com o site no ar (ver conversa). WAL deixa leitura e
    # escrita acontecerem ao mesmo tempo sem se bloquear; timeout faz
    # esperar alguns segundos em vez de falhar na hora se colidir.
    conexao = sqlite3.connect(DB_PATH, timeout=30)
    conexao.execute("PRAGMA journal_mode=WAL")
    conexao.row_factory = sqlite3.Row
    try:
        yield conexao
        conexao.commit()
    finally:
        conexao.close()


# Colunas adicionadas depois da criacao original da tabela -- "CREATE
# TABLE IF NOT EXISTS" sozinho NAO adiciona coluna nova a um banco que
# ja existe em disco (so cria do zero se o arquivo nao existir ainda).
# Qualquer coluna nova a partir de agora entra aqui, nunca direto no
# CREATE TABLE abaixo, senao quebra (sqlite3.OperationalError: no such
# column) pra quem ja tem o pedidos.db criado em producao.
_COLUNAS_ADICIONAIS: list[tuple[str, str]] = [
    ("tiny_sincronizado", "INTEGER NOT NULL DEFAULT 0"),
    ("tiny_numero_pedido", "TEXT"),
    ("tiny_erro", "TEXT"),
    ("email_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_erro", "TEXT"),
    ("endereco_destinatario_nome", "TEXT"),
    ("endereco_destinatario_tipo_pessoa", "TEXT"),
    ("endereco_destinatario_documento", "TEXT"),
    ("email_pedido_criado_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_pedido_criado_erro", "TEXT"),
    ("email_lembrete_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_lembrete_erro", "TEXT"),
    ("codigo_rastreio", "TEXT"),
    ("link_rastreio", "TEXT"),
    ("faturado_em", "TEXT"),
    ("enviado_em", "TEXT"),
    ("entregue_em", "TEXT"),
    ("transportadora", "TEXT"),
    ("email_lembrete_enviado_em", "TEXT"),
    ("cancelado_em", "TEXT"),
    ("email_cancelado_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_cancelado_erro", "TEXT"),
    ("email_upsell_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_upsell_erro", "TEXT"),
    ("email_avaliacao_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_avaliacao_erro", "TEXT"),
    # Endereco de entrega DIFERENTE do endereco principal (ver conversa
    # -- pode ser um CEP fisicamente diferente, nao so outro nome na
    # mesma casa; ex: coordenadora da livraria recebe no endereco dela,
    # nota fiscal sai no nome/endereco da paroquia). Sempre opcional em
    # conjunto -- se vazio, a entrega usa o endereco_* principal acima
    # mesmo com destinatario_nome preenchido (ver app.py:_endereco_valido).
    ("endereco_destinatario_cep", "TEXT"),
    ("endereco_destinatario_logradouro", "TEXT"),
    ("endereco_destinatario_numero", "TEXT"),
    ("endereco_destinatario_complemento", "TEXT"),
    ("endereco_destinatario_bairro", "TEXT"),
    ("endereco_destinatario_cidade", "TEXT"),
    ("endereco_destinatario_uf", "TEXT"),
    # Link pro PDF da nota fiscal (emitida na Tiny, colado a mao pelo
    # admin ao marcar "faturado" -- ainda nao ha sincronizacao
    # automatica de NF-e com a Tiny, ver app.py:admin_pedido_status).
    # Opcional -- so mostra o botao "Baixar nota fiscal" na timeline
    # do pedido (templates/pedido.html) quando preenchido.
    ("link_nota_fiscal", "TEXT"),
    # Prazo (em dias uteis) da opcao de frete escolhida -- vem da
    # cotacao real da Frenet/Melhor Envio (ver services/frete.py), usado
    # pra calcular a previsao de envio/entrega (ver
    # app.py:_previsoes_do_pedido). Nulo quando o pedido nunca teve
    # frete calculado (ex: lead do WhatsApp sem simulacao).
    ("frete_prazo_dias", "INTEGER"),
    # Exclusao pelo painel admin (ver app.py:admin_pedido_excluir) --
    # NUNCA apaga a linha de verdade (perderia o historico/numero pra
    # sempre), so marca como excluido com o motivo, pra manter
    # rastreabilidade e poder mandar o e-mail explicando pro cliente.
    ("excluido_em", "TEXT"),
    ("excluido_motivo", "TEXT"),
    # Inscricao Estadual do cliente PJ (opcional -- so faz sentido pra
    # tipo_pessoa="juridica", ver app.py:_cliente_valido e
    # static/js/carrinho_pagina.js). Os tres campos sao mutuamente
    # exclusivos na pratica (isento nunca guarda numero de IE) mas
    # gravados separados porque "isento" e "nao contribuinte" sao
    # categorias fiscais distintas pra nota fiscal (indicador de IE da
    # NFe: 1=contribuinte com IE, 2=isento, 9=nao contribuinte -- uma
    # entidade nao-contribuinte AINDA pode ter numero de IE, por isso
    # nao da pra usar so um campo booleano -- ver conversa).
    ("cliente_inscricao_estadual", "TEXT"),
    ("cliente_ie_isento", "INTEGER NOT NULL DEFAULT 0"),
    ("cliente_ie_nao_contribuinte", "INTEGER NOT NULL DEFAULT 0"),
    # Boleto bancario via Banco Inter (ver services/inter.py e
    # app.py:api_pedido_criar_boleto) -- so preenchido quando o
    # pagamento escolhido foi boleto, em vez do link da InfinitePay.
    # codigo_solicitacao e´ o identificador que a Inter devolve na
    # emissao, usado tanto pra consultar o status (polling, ver
    # app.py:_verificar_boletos_inter_pendentes) quanto pra baixar o
    # PDF sob demanda (nunca guardamos o PDF em si, so o codigo).
    ("inter_codigo_solicitacao", "TEXT"),
    ("inter_linha_digitavel", "TEXT"),
    ("inter_codigo_barras", "TEXT"),
    ("inter_pix_copia_cola", "TEXT"),
    ("inter_erro", "TEXT"),
    # Aviso interno pra loja (e-mail pro dono, ver
    # services/email.py:enviar_notificacao_venda) quando uma venda e´
    # confirmada -- ate aqui essa falha era engolida em silencio (so um
    # `except: pass` em app.py:_pos_pagamento_confirmado), entao se o
    # e-mail nunca chegasse ninguem saberia o motivo nem teria como
    # reenviar. Mesmo padrao de email_enviado/email_erro ja usado pro
    # e-mail do CLIENTE.
    ("notificacao_venda_enviada", "INTEGER NOT NULL DEFAULT 0"),
    ("notificacao_venda_erro", "TEXT"),
    # E-mail "Pedido enviado" (ver app.py:admin_pedido_status ->
    # services/email.py:enviar_pedido_enviado) -- antes disso essa
    # chamada nao tinha try/except NEM registro nenhum, entao uma falha
    # ficava completamente invisivel (nem aparecia erro, nem tinha como
    # reenviar -- ver conversa, caso real relatado pelo usuario).
    ("email_pedido_enviado_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_pedido_enviado_erro", "TEXT"),
]

# Fluxo de status depois de "pago" -- alteravel manualmente pelo painel
# (/admin/pedidos/<token>, ver app.py) e pensado pra tambem poder ser
# disparado automaticamente pela Tiny mais pra frente (webhook de
# situacao/rastreio/NF-e, deixado pra depois -- ver conversa). Os dois
# caminhos (manual e futuro automatico) devem chamar a MESMA
# atualizar_status abaixo, nunca duplicar essa logica em outro lugar.
STATUS_VALIDOS = ("pago", "faturado", "enviado", "entregue")


def inicializar_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _conexao() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos (
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
        colunas_existentes = {linha[1] for linha in conexao.execute("PRAGMA table_info(pedidos)").fetchall()}
        for nome, tipo_sql in _COLUNAS_ADICIONAIS:
            if nome not in colunas_existentes:
                conexao.execute(f"ALTER TABLE pedidos ADD COLUMN {nome} {tipo_sql}")


def criar_pedido(
    *,
    itens: list[dict],
    subtotal: float,
    frete_descricao: str,
    frete_preco: float,
    cliente: dict,
    endereco: dict,
    status_inicial: str = "pendente",
    frete_prazo_dias: int | None = None,
) -> dict:
    """`status_inicial="whatsapp"` e´ usado pelo lead criado ao clicar
    "Finalizar pelo WhatsApp" (ver app.py:api_pedido_criar_whatsapp) --
    sem link de pagamento, so pra aparecer no painel admin ate´ alguem
    preencher os dados na mao se a venda realmente fechar (ver
    confirmar_venda_manual abaixo). cliente/endereco podem vir vazios
    nesse caso (todas as colunas correspondentes sao nullable)."""
    inicializar_db()
    token = secrets.token_urlsafe(24)
    codigo = _gerar_codigo()
    total = round(subtotal + frete_preco, 2)
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            """
            INSERT INTO pedidos (
                token, codigo, status, itens, subtotal, frete_descricao, frete_preco, frete_prazo_dias, total,
                cliente_nome, cliente_tipo_pessoa, cliente_documento, cliente_telefone, cliente_email,
                cliente_inscricao_estadual, cliente_ie_isento, cliente_ie_nao_contribuinte,
                endereco_cep, endereco_logradouro, endereco_numero, endereco_complemento,
                endereco_bairro, endereco_cidade, endereco_uf,
                endereco_destinatario_nome, endereco_destinatario_tipo_pessoa, endereco_destinatario_documento,
                endereco_destinatario_cep, endereco_destinatario_logradouro, endereco_destinatario_numero,
                endereco_destinatario_complemento, endereco_destinatario_bairro, endereco_destinatario_cidade,
                endereco_destinatario_uf,
                criado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                token,
                codigo,
                status_inicial,
                json.dumps(itens),
                subtotal,
                frete_descricao,
                frete_preco,
                frete_prazo_dias,
                total,
                cliente.get("nome", ""),
                cliente.get("tipo_pessoa", ""),
                cliente.get("documento", ""),
                cliente.get("telefone", ""),
                cliente.get("email", ""),
                cliente.get("inscricao_estadual", ""),
                int(bool(cliente.get("ie_isento"))),
                int(bool(cliente.get("ie_nao_contribuinte"))),
                endereco.get("cep", ""),
                endereco.get("logradouro", ""),
                endereco.get("numero", ""),
                endereco.get("complemento", ""),
                endereco.get("bairro", ""),
                endereco.get("cidade", ""),
                endereco.get("uf", ""),
                endereco.get("destinatario_nome", ""),
                endereco.get("destinatario_tipo_pessoa", ""),
                endereco.get("destinatario_documento", ""),
                endereco.get("destinatario_cep", ""),
                endereco.get("destinatario_logradouro", ""),
                endereco.get("destinatario_numero", ""),
                endereco.get("destinatario_complemento", ""),
                endereco.get("destinatario_bairro", ""),
                endereco.get("destinatario_cidade", ""),
                endereco.get("destinatario_uf", ""),
                agora,
            ),
        )
    return obter_pedido(token)


def listar_pedidos(*, status: str | None = None, limite: int = 200) -> list[dict]:
    """Usado pelo painel interno (/admin/pedidos, ver app.py) -- mais
    recentes primeiro."""
    inicializar_db()
    consulta = "SELECT * FROM pedidos"
    parametros: tuple = ()
    if status:
        consulta += " WHERE status = ?"
        parametros = (status,)
    consulta += " ORDER BY criado_em DESC LIMIT ?"
    parametros = parametros + (limite,)
    with _conexao() as conexao:
        linhas = conexao.execute(consulta, parametros).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def listar_pedidos_pendentes_para_lembrete(minutos: int) -> list[dict]:
    """Pedidos "pendente" ha´ pelo menos `minutos`, que ainda nao
    receberam o lembrete de pagamento -- usado pelo job agendado em
    app.py (ver services/email.py:enviar_lembrete_pedido_pendente).
    Exclui pedido de boleto (inter_codigo_solicitacao preenchido): esse
    fluxo tem vencimento medido em DIAS (ver services/inter.py), o
    lembrete de "pague agora" de minutos so faz sentido pro link da
    InfinitePay, que expira rapido."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
    with _conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT * FROM pedidos
            WHERE status = 'pendente' AND email_lembrete_enviado = 0 AND criado_em <= ?
                AND (inter_codigo_solicitacao IS NULL OR inter_codigo_solicitacao = '')
            ORDER BY criado_em ASC
            """,
            (limite,),
        ).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def listar_pedidos_pendentes_para_cancelar(minutos: int) -> list[dict]:
    """Pedidos "pendente" que ja receberam o lembrete (2o link) ha´ pelo
    menos `minutos` e continuam sem pagar -- usado pelo job agendado em
    app.py (ver services.pedidos.cancelar_pedido e
    services/email.py:enviar_pedido_cancelado). O corte usa
    email_lembrete_enviado_em (quando o lembrete foi TENTADO, com ou
    sem sucesso) em vez de exigir entrega confirmada do e-mail --
    assim um pedido nao fica "pendente" pra sempre so porque o envio
    do lembrete falhou."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()
    with _conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT * FROM pedidos
            WHERE status = 'pendente' AND email_lembrete_enviado = 1
                AND email_cancelado_enviado = 0 AND email_lembrete_enviado_em <= ?
            ORDER BY email_lembrete_enviado_em ASC
            """,
            (limite,),
        ).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def listar_pedidos_pagos_para_upsell(horas: int) -> list[dict]:
    """Pedidos "pago" ha´ pelo menos `horas`, que ainda nao receberam o
    e-mail de oportunidade (empurrao pra proxima faixa de desconto no
    proximo pedido) -- usado pelo job agendado em app.py (ver
    services/email.py:enviar_oportunidade_upsell)."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()
    with _conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT * FROM pedidos
            WHERE status = 'pago' AND email_upsell_enviado = 0 AND pago_em <= ?
            ORDER BY pago_em ASC
            """,
            (limite,),
        ).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def marcar_email_upsell_enviado(token: str, *, erro: str | None) -> dict | None:
    """E-mail de oportunidade (empurrao de desconto) enviado horas depois
    do pagamento confirmado (ver listar_pedidos_pagos_para_upsell acima)
    -- garante que o job agendado so manda uma vez por pedido, mesmo
    quando nao havia oportunidade real pra oferecer (erro=None nesse
    caso tambem, so nao chega a chamar a Brevo)."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_upsell_enviado = 1, email_upsell_erro = ? WHERE token = ?",
            (erro, token),
        )
    return obter_pedido(token)


def listar_pedidos_pagos_para_avaliacao(dias: int) -> list[dict]:
    """Pedidos "pago" (ou ja adiante no fluxo -- faturado/enviado/entregue)
    ha´ pelo menos `dias`, que ainda nao receberam o pedido de avaliacao
    -- usado pelo job agendado em app.py (ver
    services/email.py:enviar_pedido_avaliacao). Inclui os 4 status
    porque o pedido pode ter avancado no fluxo antes dos 30 dias
    passarem -- nao faz sentido esperar continuar "pago" especificamente."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with _conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT * FROM pedidos
            WHERE status IN ('pago', 'faturado', 'enviado', 'entregue')
                AND email_avaliacao_enviado = 0 AND pago_em <= ?
            ORDER BY pago_em ASC
            """,
            (limite,),
        ).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def marcar_email_avaliacao_enviado(token: str, *, erro: str | None) -> dict | None:
    """E-mail pedindo avaliacao, disparado dias depois do pagamento (ver
    listar_pedidos_pagos_para_avaliacao acima) -- garante que o job
    agendado so manda uma vez por pedido."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_avaliacao_enviado = 1, email_avaliacao_erro = ? WHERE token = ?",
            (erro, token),
        )
    return obter_pedido(token)


def obter_pedido(token: str) -> dict | None:
    inicializar_db()
    with _conexao() as conexao:
        linha = conexao.execute("SELECT * FROM pedidos WHERE token = ?", (token,)).fetchone()
    if linha is None:
        return None
    pedido = dict(linha)
    pedido["itens"] = json.loads(pedido["itens"])
    return pedido


def salvar_dados_boleto_inter(
    token: str, *, codigo_solicitacao: str, linha_digitavel: str, codigo_barras: str, pix_copia_cola: str
) -> dict | None:
    """Grava os dados do boleto assim que emitido na Inter (ver
    app.py:api_pedido_criar_boleto) -- codigo_solicitacao e´ o que o
    job de polling usa depois pra consultar se foi pago (ver
    services.inter.consultar_cobranca)."""
    with _conexao() as conexao:
        conexao.execute(
            """
            UPDATE pedidos SET
                inter_codigo_solicitacao = ?, inter_linha_digitavel = ?,
                inter_codigo_barras = ?, inter_pix_copia_cola = ?
            WHERE token = ?
            """,
            (codigo_solicitacao, linha_digitavel, codigo_barras, pix_copia_cola, token),
        )
    return obter_pedido(token)


def marcar_boleto_erro(token: str, erro: str) -> dict | None:
    """Consulta de status do boleto falhou (rede fora, credencial
    expirada etc, ver app.py:_verificar_boletos_inter_pendentes) --
    so pra aparecer no painel admin, nao impede novas tentativas no
    proximo ciclo do job."""
    with _conexao() as conexao:
        conexao.execute("UPDATE pedidos SET inter_erro = ? WHERE token = ?", (erro, token))
    return obter_pedido(token)


def listar_pedidos_boleto_pendentes() -> list[dict]:
    """Pedidos "pendente" com boleto Inter emitido -- usado pelo job de
    polling (ver app.py:_verificar_boletos_inter_pendentes) pra
    consultar quais ja foram pagos."""
    inicializar_db()
    with _conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT * FROM pedidos
            WHERE status = 'pendente' AND inter_codigo_solicitacao IS NOT NULL AND inter_codigo_solicitacao != ''
            ORDER BY criado_em ASC
            """
        ).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def marcar_pago(
    token: str, *, forma_pagamento: str, parcelas: int | None, valor_pago: float, transaction_nsu: str
) -> dict | None:
    """Idempotente -- se o pedido ja estiver 'pago' (webhook repetido, comum
    em integracoes de pagamento), so devolve o pedido sem reprocessar."""
    pedido = obter_pedido(token)
    if pedido is None or pedido["status"] == "pago":
        return pedido
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            """
            UPDATE pedidos SET status = 'pago', forma_pagamento = ?, parcelas = ?,
                valor_pago = ?, transaction_nsu = ?, pago_em = ?
            WHERE token = ?
            """,
            (forma_pagamento, parcelas, valor_pago, transaction_nsu, agora, token),
        )
    return obter_pedido(token)


def confirmar_venda_manual(
    token: str,
    *,
    cliente: dict,
    endereco: dict,
    frete_descricao: str,
    frete_preco: float,
    forma_pagamento: str,
    valor_pago: float,
    frete_prazo_dias: int | None = None,
    destinatario: dict | None = None,
) -> dict | None:
    """Promove um lead "whatsapp" (ver criar_pedido) pra "pago" depois do
    admin preencher os dados na mao, quando a pessoa realmente fechou o
    pedido combinado pelo WhatsApp (ver app.py:admin_pedido_confirmar_venda).
    So funciona nesse status -- nao reprocessa um pedido ja confirmado
    nem mexe num pedido de outro fluxo (evita sobrescrever cliente/
    endereco de um pedido pago normalmente pelo site). `destinatario`
    e´ o endereco de ENTREGA quando diferente do cliente que fechou a
    compra (ex: livraria que recebe por conta de outra pessoa, ver
    conversa) -- mesmas colunas endereco_destinatario_* usadas no
    checkout do site (ver criar_pedido/_endereco_valido em app.py), so
    que aqui vem em branco quando None (nenhum destinatario informado)."""
    pedido = obter_pedido(token)
    if pedido is None or pedido["status"] != "whatsapp":
        return pedido
    destinatario = destinatario or {}
    total = round(pedido["subtotal"] + frete_preco, 2)
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            """
            UPDATE pedidos SET
                status = 'pago', pago_em = ?,
                cliente_nome = ?, cliente_tipo_pessoa = ?, cliente_documento = ?,
                cliente_telefone = ?, cliente_email = ?,
                cliente_inscricao_estadual = ?, cliente_ie_isento = ?, cliente_ie_nao_contribuinte = ?,
                endereco_cep = ?, endereco_logradouro = ?, endereco_numero = ?, endereco_complemento = ?,
                endereco_bairro = ?, endereco_cidade = ?, endereco_uf = ?,
                endereco_destinatario_nome = ?, endereco_destinatario_tipo_pessoa = ?,
                endereco_destinatario_documento = ?,
                endereco_destinatario_cep = ?, endereco_destinatario_logradouro = ?,
                endereco_destinatario_numero = ?, endereco_destinatario_complemento = ?,
                endereco_destinatario_bairro = ?, endereco_destinatario_cidade = ?,
                endereco_destinatario_uf = ?,
                frete_descricao = ?, frete_preco = ?, frete_prazo_dias = ?, total = ?,
                forma_pagamento = ?, valor_pago = ?
            WHERE token = ?
            """,
            (
                agora,
                cliente.get("nome", ""), cliente.get("tipo_pessoa", ""), cliente.get("documento", ""),
                cliente.get("telefone", ""), cliente.get("email", ""),
                cliente.get("inscricao_estadual", ""),
                int(bool(cliente.get("ie_isento"))), int(bool(cliente.get("ie_nao_contribuinte"))),
                endereco.get("cep", ""), endereco.get("logradouro", ""), endereco.get("numero", ""),
                endereco.get("complemento", ""), endereco.get("bairro", ""), endereco.get("cidade", ""),
                endereco.get("uf", ""),
                destinatario.get("nome", ""), destinatario.get("tipo_pessoa", ""),
                destinatario.get("documento", ""),
                destinatario.get("cep", ""), destinatario.get("logradouro", ""),
                destinatario.get("numero", ""), destinatario.get("complemento", ""),
                destinatario.get("bairro", ""), destinatario.get("cidade", ""),
                destinatario.get("uf", ""),
                frete_descricao, frete_preco, frete_prazo_dias, total,
                forma_pagamento, valor_pago,
                token,
            ),
        )
    return obter_pedido(token)


def atualizar_status(
    token: str,
    novo_status: str,
    *,
    codigo_rastreio: str | None = None,
    link_rastreio: str | None = None,
    transportadora: str | None = None,
    link_nota_fiscal: str | None = None,
) -> dict | None:
    """Avanca o status manualmente (painel admin) ou automaticamente
    (futuro webhook da Tiny) -- as duas origens devem usar essa mesma
    funcao, nunca duplicar a logica. `codigo_rastreio`/`link_rastreio`/
    `transportadora` so fazem sentido pra novo_status="enviado";
    `link_nota_fiscal` so pra novo_status="faturado" (ver app.py)."""
    if novo_status not in STATUS_VALIDOS:
        return None
    pedido = obter_pedido(token)
    if pedido is None:
        return None
    agora = datetime.now(timezone.utc).isoformat()
    coluna_data = {"faturado": "faturado_em", "enviado": "enviado_em", "entregue": "entregue_em"}.get(novo_status)
    with _conexao() as conexao:
        if coluna_data:
            conexao.execute(
                f"""
                UPDATE pedidos SET status = ?, {coluna_data} = ?,
                    codigo_rastreio = COALESCE(?, codigo_rastreio), link_rastreio = COALESCE(?, link_rastreio),
                    transportadora = COALESCE(?, transportadora),
                    link_nota_fiscal = COALESCE(?, link_nota_fiscal)
                WHERE token = ?
                """,
                (novo_status, agora, codigo_rastreio, link_rastreio, transportadora, link_nota_fiscal, token),
            )
        else:
            conexao.execute("UPDATE pedidos SET status = ? WHERE token = ?", (novo_status, token))
    return obter_pedido(token)


def marcar_email_enviado(token: str, *, erro: str | None) -> dict | None:
    """E-mail de PAGAMENTO CONFIRMADO -- mesma logica do
    marcar_tiny_sincronizado (ver abaixo), evita reenviar em webhook
    duplicado. Ver marcar_email_pedido_criado_enviado pro e-mail
    disparado na CRIACAO do pedido (com o link de pagamento)."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_enviado = 1, email_erro = ? WHERE token = ?", (erro, token)
        )
    return obter_pedido(token)


def marcar_notificacao_venda_enviada(token: str, *, erro: str | None) -> dict | None:
    """Aviso interno pra loja (e-mail pro dono, ver
    app.py:_pos_pagamento_confirmado) -- mesma logica do
    marcar_email_enviado, mas pro e-mail de NOTIFICACAO (pro dono), nao
    de confirmacao (pro cliente). Existe pra nunca mais engolir em
    silencio uma falha nessa notificacao (ver conversa)."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET notificacao_venda_enviada = 1, notificacao_venda_erro = ? WHERE token = ?",
            (erro, token),
        )
    return obter_pedido(token)


def marcar_email_pedido_enviado_enviado(token: str, *, erro: str | None) -> dict | None:
    """E-mail "Pedido enviado" (ver app.py:admin_pedido_status), disparado
    quando o admin muda o status pra "enviado" -- mesma logica de
    marcar_email_enviado, so que pra esse e-mail especifico."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_pedido_enviado_enviado = 1, email_pedido_enviado_erro = ? WHERE token = ?",
            (erro, token),
        )
    return obter_pedido(token)


def marcar_email_pedido_criado_enviado(token: str, *, erro: str | None) -> dict | None:
    """E-mail com o link de pagamento, disparado assim que o pedido e´
    criado (ver app.py:api_pedido_criar) -- diferente do
    marcar_email_enviado acima (esse e´ o de pagamento confirmado)."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_pedido_criado_enviado = 1, email_pedido_criado_erro = ? WHERE token = ?",
            (erro, token),
        )
    return obter_pedido(token)


def marcar_email_lembrete_enviado(token: str, *, erro: str | None) -> dict | None:
    """E-mail de lembrete pra pedido pendente ha´ muito tempo sem pagar
    (ver listar_pedidos_pendentes_para_lembrete acima) -- garante que
    o job agendado so manda esse lembrete uma vez por pedido. Tambem
    grava email_lembrete_enviado_em (mesmo quando `erro` vem
    preenchido), usado por listar_pedidos_pendentes_para_cancelar pra
    contar os minutos ate´ o cancelamento automatico."""
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            """
            UPDATE pedidos SET email_lembrete_enviado = 1, email_lembrete_erro = ?,
                email_lembrete_enviado_em = ?
            WHERE token = ?
            """,
            (erro, agora, token),
        )
    return obter_pedido(token)


def cancelar_pedido(token: str) -> dict | None:
    """Cancela um pedido ainda "pendente" (abandonado apos o lembrete --
    ver listar_pedidos_pendentes_para_cancelar e app.py) ou descarta um
    lead "whatsapp" que o admin decidiu que nao fechou (ver
    app.py:admin_pedido_descartar_whatsapp). Idempotente: se o pedido ja
    nao estiver mais num desses dois status (por exemplo, o cliente
    pagou entre o job rodar e o cancelamento ser processado), nao faz
    nada e devolve o pedido como esta´."""
    pedido = obter_pedido(token)
    if pedido is None or pedido["status"] not in ("pendente", "whatsapp"):
        return pedido
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET status = 'cancelado', cancelado_em = ? WHERE token = ?",
            (agora, token),
        )
    return obter_pedido(token)


def excluir_pedido(token: str, *, motivo: str) -> dict | None:
    """Exclusao pelo painel admin (ver app.py:admin_pedido_excluir) --
    de QUALQUER status, com motivo obrigatorio. NUNCA apaga a linha de
    verdade (perderia numero/historico pra sempre e quebraria o link
    de acompanhamento que o cliente pode ainda ter salvo) -- so marca
    status="excluido" com o motivo, pra manter rastreabilidade e poder
    mandar o e-mail explicando pro cliente (ver
    services/email.py:enviar_pedido_excluido). Idempotente: excluir de
    novo so atualiza o motivo."""
    if obter_pedido(token) is None:
        return None
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET status = 'excluido', excluido_em = ?, excluido_motivo = ? WHERE token = ?",
            (agora, motivo, token),
        )
    return obter_pedido(token)


def marcar_email_cancelado_enviado(token: str, *, erro: str | None) -> dict | None:
    """E-mail motivacional de recuperacao, disparado quando o pedido e´
    cancelado automaticamente (ver cancelar_pedido acima) -- garante
    que o job agendado so manda esse e-mail uma vez por pedido."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_cancelado_enviado = 1, email_cancelado_erro = ? WHERE token = ?",
            (erro, token),
        )
    return obter_pedido(token)


def marcar_tiny_sincronizado(token: str, *, numero_pedido: str | None, erro: str | None) -> dict | None:
    """Registra o resultado da tentativa de sincronizar com a Tiny (ver
    services/tiny.py) -- so pra evitar reenviar o mesmo pedido pra Tiny
    a cada webhook repetido (a InfinitePay pode reenviar). `erro` fica
    guardado pra dar pra conferir manualmente quais pedidos falharam
    a sincronizacao, mesmo sem reprocessar automaticamente."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET tiny_sincronizado = 1, tiny_numero_pedido = ?, tiny_erro = ? WHERE token = ?",
            (numero_pedido, erro, token),
        )
    return obter_pedido(token)


def somar_dias_uteis(data_inicio: datetime, dias: int) -> datetime:
    """Soma `dias` dias UTEIS (pula sabado/domingo) a partir de
    `data_inicio` -- usado pra calcular previsao de envio/entrega (ver
    previsoes_do_pedido abaixo). Nao considera feriados (mesma
    aproximacao ja usada na promessa de texto fixo "5 dias uteis" em
    varias paginas -- calcular feriado municipal/estadual certo exigiria
    uma base de dados de feriados que o site nao tem hoje)."""
    data = data_inicio
    restantes = dias
    while restantes > 0:
        data += timedelta(days=1)
        if data.weekday() < 5:  # 0=segunda ... 4=sexta
            restantes -= 1
    return data


def previsoes_do_pedido(pedido: dict) -> dict:
    """Previsao de envio (pago_em + PRODUCAO_DIAS_UTEIS dias uteis) e de
    entrega (frete_prazo_dias dias uteis a partir do envio, quando
    conhecido) -- mostrado no painel admin, na timeline do cliente
    (app.py:ver_pedido) e no e-mail de confirmacao (services/email.py)
    (ver conversa: "pago dia X, enviar ate dia X+5 dias uteis").

    `previsao_envio` sempre reflete a promessa original (baseada em
    pago_em), mesmo depois do pedido ja ter sido enviado de verdade --
    e´ o que da´ base pra comparar com o envio real e descobrir se saiu
    adiantado (ver enviado_antecipado abaixo).

    Ja´ `previsao_entrega`, uma vez que o pedido tenha um enviado_em real
    (admin marcou como "enviado"), passa a ser calculada a partir dessa
    data de verdade em vez da promessa -- se o pedido saiu antes do
    prazo, a entrega tende a chegar antes tambem (ver conversa: "alterar
    o prazo de entrega... e colocar nova data"). `enviado_antecipado`
    fica True quando isso aconteceu, pra` templates/pedido.html mostrar
    uma mensagem alegre nesse caso."""
    resultado = {"previsao_envio": None, "previsao_entrega": None, "enviado_antecipado": False}
    pago_em = pedido.get("pago_em")
    if not pago_em:
        return resultado
    data_pago = datetime.fromisoformat(pago_em)
    previsao_envio = somar_dias_uteis(data_pago, PRODUCAO_DIAS_UTEIS)
    resultado["previsao_envio"] = previsao_envio

    prazo_frete = pedido.get("frete_prazo_dias")
    enviado_em = pedido.get("enviado_em")
    if enviado_em:
        data_enviado = datetime.fromisoformat(enviado_em)
        resultado["enviado_antecipado"] = data_enviado.date() < previsao_envio.date()
        if prazo_frete:
            resultado["previsao_entrega"] = somar_dias_uteis(data_enviado, int(prazo_frete))
    elif prazo_frete:
        resultado["previsao_entrega"] = somar_dias_uteis(previsao_envio, int(prazo_frete))
    return resultado
