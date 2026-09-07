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

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import FAIXAS_PRODUCAO_DIAS_UTEIS, PRODUCAO_DIAS_UTEIS

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
    # Telefone de quem recebe, quando diferente de quem fecha a compra
    # (ver conversa) -- opcional, so pra transportadora/Tiny conseguirem
    # contato se precisar. Formato conferido (telefone_valido) so quando
    # preenchido, nunca obrigatorio.
    ("endereco_destinatario_telefone", "TEXT"),
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
    # E-mail "Nota fiscal disponível" (ver
    # app.py:admin_pedido_status -> services/email.py:enviar_nota_fiscal_disponivel)
    # -- disparado na primeira vez que link_nota_fiscal e´ preenchido.
    ("email_nota_fiscal_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_nota_fiscal_erro", "TEXT"),
    # Arquivamento pelo painel admin (ver conversa) -- so tira o pedido
    # da lista principal pra desafogar o painel, SEM mudar o status nem
    # avisar o cliente (diferente de excluir_pedido acima, que muda
    # status e manda e-mail). Reversivel a qualquer momento.
    ("arquivado", "INTEGER NOT NULL DEFAULT 0"),
    ("arquivado_em", "TEXT"),
    # Marca que a limpeza de imagens personalizadas de pedido CANCELADO
    # ja rodou pra esse pedido (ver app.py:_limpar_imagens_pedidos_
    # cancelados) -- sem isso, a query da limpeza reprocessaria TODO
    # pedido cancelado da historia do site a cada rodada do job, pra
    # sempre (custo crescendo sem limite).
    ("imagens_pedido_apagadas", "INTEGER NOT NULL DEFAULT 0"),
    # 2o e-mail de avaliacao (mesmo conteudo do 1o, ver
    # services/email.py:enviar_pedido_avaliacao), mandado
    # AVALIACAO_SEGUIMENTO_DIAS_APOS_ENTREGA dias depois de "entregue"
    # -- ver app.py:_enviar_seguimento_avaliacao_entregues. O 1o e´
    # imediato (na hora que o status vira "entregue", reusa
    # email_avaliacao_enviado/email_avaliacao_erro que ja existiam).
    ("email_avaliacao_seguimento_enviado", "INTEGER NOT NULL DEFAULT 0"),
    ("email_avaliacao_seguimento_erro", "TEXT"),
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

        # Codigo de verificacao do login por CPF em /meus-pedidos (ver
        # app.py e gerar_codigo_verificacao_documento/verificar_codigo_documento
        # abaixo) -- tabela separada e PEQUENA de proposito: uma linha por
        # documento, sobrescrita a cada pedido de codigo novo (REPLACE INTO),
        # nunca acumula historico. So guarda o HASH do codigo (nunca o
        # codigo em si) e expira em minutos -- limpar_codigos_verificacao_expirados
        # (job agendado, ver app.py) apaga as linhas vencidas periodicamente,
        # entao o tamanho dessa tabela fica limitado ao numero de logins
        # em andamento no momento, nunca cresce sem limite.
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS codigos_verificacao_documento (
                documento TEXT PRIMARY KEY,
                codigo_hash TEXT NOT NULL,
                expira_em TEXT NOT NULL,
                tentativas INTEGER NOT NULL DEFAULT 0,
                criado_em TEXT NOT NULL
            )
            """
        )

        # Numeracao sequencial e GLOBAL (nunca reinicia por pedido, so
        # quando a usuaria pedir -- ver resetar_numeracao_modelo_personalizada
        # abaixo) de cada LADO com foto de verdade -- pedido do usuario:
        # nome do arquivo baixado e a coluna "Modelo" do CSV de producao
        # (ver app.py:_atribuir_numeros_modelo_personalizada) precisam
        # de um numero estavel pra identificar a peca, ja que ela nao
        # tem nome de santo. Item de 1 lado so usa lado="" (um numero so
        # pra peca inteira); item de 2 lados numera lado1/lado2
        # SEPARADO -- cada foto e´ um design distinto que a produção
        # imprime por conta propria, mesmo as duas fazendo parte da
        # MESMA peca fisica no fim (ver conversa). Chave e´ (pedido_token,
        # item_index, lado) -- o indice do item dentro de pedido["itens"]
        # nunca muda depois de criado -- pra dar sempre o MESMO numero
        # pra mesma foto em toda visita futura (painel ou CSV).
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS numeros_modelo_personalizada (
                pedido_token TEXT NOT NULL,
                item_index INTEGER NOT NULL,
                lado TEXT NOT NULL DEFAULT '',
                numero INTEGER NOT NULL,
                atribuido_em TEXT NOT NULL,
                PRIMARY KEY (pedido_token, item_index, lado)
            )
            """
        )
        colunas_numeracao = {
            linha[1] for linha in conexao.execute("PRAGMA table_info(numeros_modelo_personalizada)").fetchall()
        }
        if "lado" not in colunas_numeracao:
            # Formato anterior (numero por ITEM inteiro, sem separar por
            # lado -- ver conversa) -- so guarda sequencia regeneravel,
            # nunca dado de pedido de verdade, entao e´ seguro recriar do
            # zero com o esquema novo em vez de migrar linha a linha.
            conexao.execute("DROP TABLE numeros_modelo_personalizada")
            conexao.execute(
                """
                CREATE TABLE numeros_modelo_personalizada (
                    pedido_token TEXT NOT NULL,
                    item_index INTEGER NOT NULL,
                    lado TEXT NOT NULL DEFAULT '',
                    numero INTEGER NOT NULL,
                    atribuido_em TEXT NOT NULL,
                    PRIMARY KEY (pedido_token, item_index, lado)
                )
                """
            )


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
                endereco_destinatario_uf, endereco_destinatario_telefone,
                criado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                endereco.get("destinatario_telefone", ""),
                agora,
            ),
        )
    return obter_pedido(token)


def listar_pedidos(*, status: str | None = None, arquivados: bool = False, limite: int = 200) -> list[dict]:
    """Usado pelo painel interno (/admin/pedidos, ver app.py) -- mais
    recentes primeiro. `arquivado` e´ independente do `status` (ver
    arquivar_pedido abaixo): por padrao (arquivados=False) a lista
    principal e os filtros por status NUNCA mostram pedido arquivado,
    pra realmente desafogar o painel; arquivados=True inverte e mostra
    so os arquivados (opcionalmente ainda filtrados por status)."""
    inicializar_db()
    condicoes = ["arquivado = ?"]
    parametros: list = [1 if arquivados else 0]
    if status:
        condicoes.append("status = ?")
        parametros.append(status)
    consulta = "SELECT * FROM pedidos WHERE " + " AND ".join(condicoes)
    consulta += " ORDER BY criado_em DESC LIMIT ?"
    parametros.append(limite)
    with _conexao() as conexao:
        linhas = conexao.execute(consulta, parametros).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def estatisticas_hoje() -> dict:
    """Resumo rapido pro topo do painel (ver app.py:admin_pedidos) --
    "hoje" aqui e´ o dia em UTC (mesmo criterio ja usado em todo o
    resto do app pra criado_em/pago_em, ver conversa: nao ha conversao
    de fuso em nenhum outro lugar do codigo, entao manter consistente
    em vez de introduzir um criterio novo so pra essa tela). Pendentes
    conta o total em aberto AGORA (nao so os de hoje), pra sempre
    mostrar quanto falta resolver."""
    inicializar_db()
    hoje = datetime.now(timezone.utc).date().isoformat()
    with _conexao() as conexao:
        pedidos_hoje = conexao.execute(
            "SELECT COUNT(*) FROM pedidos WHERE substr(criado_em, 1, 10) = ?", (hoje,)
        ).fetchone()[0]
        linha_pagos = conexao.execute(
            "SELECT COUNT(*), COALESCE(SUM(total), 0) FROM pedidos WHERE substr(pago_em, 1, 10) = ?", (hoje,)
        ).fetchone()
        pendentes = conexao.execute(
            "SELECT COUNT(*) FROM pedidos WHERE status IN ('pendente', 'whatsapp')"
        ).fetchone()[0]
    return {
        "pedidos_hoje": pedidos_hoje,
        "vendas_hoje": linha_pagos[0],
        "faturamento_hoje": linha_pagos[1],
        "pendentes": pendentes,
    }


def contagem_pedidos_por_status(dias: int, status_lista: tuple[str, ...]) -> int:
    """Quantos pedidos com status em `status_lista` foram CRIADOS nos
    ultimos `dias` dias -- usado pro painel de analytics (ver
    app.py:admin_analytics) calcular proporcao de pedidos por visita
    (ex: pendente+pago / visitas)."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    marcadores = ",".join("?" for _ in status_lista)
    with _conexao() as conexao:
        return conexao.execute(
            f"SELECT COUNT(*) FROM pedidos WHERE criado_em >= ? AND status IN ({marcadores})",
            (limite, *status_lista),
        ).fetchone()[0]


def resumo_vendas_periodo(dias: int) -> dict:
    """Quantidade, faturamento total e ticket medio das vendas pagas
    (por pago_em) nos ultimos `dias` dias -- ver app.py:admin_analytics."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with _conexao() as conexao:
        quantidade, valor_total = conexao.execute(
            "SELECT COUNT(*), COALESCE(SUM(total), 0) FROM pedidos WHERE pago_em >= ?", (limite,)
        ).fetchone()
    ticket_medio = (valor_total / quantidade) if quantidade else 0.0
    return {"quantidade": quantidade, "valor_total": valor_total, "ticket_medio": ticket_medio}


def vendas_por_dia(dias: int) -> list[dict]:
    """[{"dia": "01/08", "quantidade": int, "valor": float}, ...] um item
    por dia do periodo (0 nos dias sem venda), baseado em pago_em -- pro
    grafico de vendas por dia (ver conversa: usuaria mandou print do
    dashboard da Yampi como referencia)."""
    inicializar_db()
    hoje = datetime.now(timezone.utc).date()
    inicio = hoje - timedelta(days=dias - 1)
    with _conexao() as conexao:
        linhas = conexao.execute(
            "SELECT pago_em, total FROM pedidos WHERE pago_em >= ?", (inicio.isoformat(),)
        ).fetchall()
    por_dia: dict[str, dict] = {}
    for linha in linhas:
        chave = linha["pago_em"][:10]
        registro = por_dia.setdefault(chave, {"quantidade": 0, "valor": 0.0})
        registro["quantidade"] += 1
        registro["valor"] += linha["total"]
    resultado = []
    for i in range(dias):
        data = inicio + timedelta(days=i)
        dados = por_dia.get(data.isoformat(), {"quantidade": 0, "valor": 0.0})
        resultado.append({
            "dia": data.strftime("%d/%m"),
            "quantidade": dados["quantidade"],
            "valor": round(dados["valor"], 2),
        })
    return resultado


def pedidos_por_uf(dias: int) -> list[dict]:
    """[{"uf": "SP", "quantidade": int}, ...] pedidos PAGOS no periodo,
    ordenado do estado com mais pedidos pro com menos -- usa o UF de
    ENTREGA (destinatario, quando diferente) porque e´ o que importa
    pra logistica, mesmo criterio ja usado no calculo de frete."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with _conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT CASE WHEN endereco_destinatario_uf != '' THEN endereco_destinatario_uf ELSE endereco_uf END AS uf,
                   COUNT(*) AS quantidade
            FROM pedidos WHERE pago_em >= ? AND uf != ''
            GROUP BY uf ORDER BY quantidade DESC
            """,
            (limite,),
        ).fetchall()
    return [{"uf": linha["uf"], "quantidade": linha["quantidade"]} for linha in linhas]


def taxa_cancelamento(dias: int) -> dict:
    """{"cancelados": int, "total": int, "taxa_pct": float} sobre pedidos
    CRIADOS pelo site no periodo (exclui leads "whatsapp", que nunca
    chegam a virar pedido de verdade) -- so conta status "cancelado"
    (auto-cancelamento de pendente abandonado, ver cancelar_pedido),
    nao "excluido" (acao manual do admin com motivo, natureza diferente)."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with _conexao() as conexao:
        total = conexao.execute(
            "SELECT COUNT(*) FROM pedidos WHERE criado_em >= ? AND status != 'whatsapp'", (limite,)
        ).fetchone()[0]
        cancelados = conexao.execute(
            "SELECT COUNT(*) FROM pedidos WHERE criado_em >= ? AND status = 'cancelado'", (limite,)
        ).fetchone()[0]
    taxa = round(cancelados / total * 100, 2) if total else 0.0
    return {"cancelados": cancelados, "total": total, "taxa_pct": taxa}


# Normaliza os valores brutos de forma_pagamento (que vem de fontes bem
# diferentes -- "pix"/"credit_card" do webhook da InfinitePay, "boleto"
# do Banco Inter, "manual" da confirmacao manual do admin, ou texto
# livre digitado no confirmar-venda do WhatsApp, tipo "Pix"/"Dinheiro")
# pra um rotulo consistente no relatorio -- ver formas_pagamento_periodo.
_ROTULO_FORMA_PAGAMENTO = {
    "pix": "Pix", "credit_card": "Cartão de crédito", "boleto": "Boleto", "manual": "Confirmado manualmente",
}


def _rotulo_forma_pagamento(bruto: str) -> str:
    bruto = (bruto or "").strip()
    if not bruto:
        return "Não informado"
    return _ROTULO_FORMA_PAGAMENTO.get(bruto.lower(), bruto)


def formas_pagamento_periodo(dias: int) -> list[dict]:
    """[{"forma": "Pix", "quantidade": int, "valor": float}, ...] pedidos
    PAGOS no periodo, agrupados pelo rotulo normalizado acima, do mais
    usado pro menos."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with _conexao() as conexao:
        linhas = conexao.execute(
            "SELECT forma_pagamento, total FROM pedidos WHERE pago_em >= ?", (limite,)
        ).fetchall()
    agregados: dict[str, dict] = {}
    for linha in linhas:
        rotulo = _rotulo_forma_pagamento(linha["forma_pagamento"])
        registro = agregados.setdefault(rotulo, {"quantidade": 0, "valor": 0.0})
        registro["quantidade"] += 1
        registro["valor"] += linha["total"]
    resultado = [
        {"forma": rotulo, "quantidade": dados["quantidade"], "valor": round(dados["valor"], 2)}
        for rotulo, dados in agregados.items()
    ]
    resultado.sort(key=lambda r: r["quantidade"], reverse=True)
    return resultado


def _itens_pagos_no_periodo(desde: datetime | None, ate: datetime | None) -> list[list[dict]]:
    """Lista de "itens" (ja decodificados de JSON) de cada pedido PAGO
    dentro da janela -- usada por produtos_mais_vendidos e
    quantidade_por_material abaixo, pra nao duplicar a mesma query com
    janela flexivel (desde/ate None = sem limite naquela ponta; os dois
    None == "total", desde sempre)."""
    inicializar_db()
    condicoes = []
    parametros: list = []
    if desde is not None:
        condicoes.append("pago_em >= ?")
        parametros.append(desde.isoformat())
    if ate is not None:
        condicoes.append("pago_em <= ?")
        parametros.append(ate.isoformat())
    consulta = "SELECT itens FROM pedidos WHERE pago_em IS NOT NULL"
    if condicoes:
        consulta += " AND " + " AND ".join(condicoes)
    with _conexao() as conexao:
        linhas = conexao.execute(consulta, parametros).fetchall()
    return [json.loads(linha["itens"]) for linha in linhas]


def unidades_vendidas_por_produto(dias: int = 30) -> dict[str, int]:
    """{produto_id: quantidade} somando os itens dos pedidos PAGOS nos
    ultimos `dias` dias -- usado pro selo "X vendidas nos ultimos 30
    dias" nos cards do catalogo/home/categoria (ver app.py:
    _com_vendas_recentes). So conta item com produtoId preenchido (um
    santo do catalogo escolhido direto -- personalizada normalmente
    nao tem produtoId proprio, ver conversa, entao fica de fora)."""
    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    contagem: dict[str, int] = {}
    for itens in _itens_pagos_no_periodo(desde, None):
        for item in itens:
            produto_id = item.get("produtoId")
            if not produto_id:
                continue
            contagem[produto_id] = contagem.get(produto_id, 0) + int(item.get("quantidade", 0))
    return contagem


def produtos_mais_vendidos(
    *, desde: datetime | None = None, ate: datetime | None = None, limite_itens: int = 6
) -> list[dict]:
    """[{"produto": nome, "quantidade": int}, ...] a partir dos ITENS
    dos pedidos PAGOS no periodo, somando quantidade por nome de
    produto -- item personalizado (sem produtoNome, ver
    app.py:_itens_com_descricao_do_corpo) vira "Personalizada"."""
    contagem: dict[str, int] = {}
    for itens in _itens_pagos_no_periodo(desde, ate):
        for item in itens:
            nome = item.get("produtoNome") or "Personalizada"
            contagem[nome] = contagem.get(nome, 0) + int(item.get("quantidade", 0))
    resultado = [{"produto": nome, "quantidade": quantidade} for nome, quantidade in contagem.items()]
    resultado.sort(key=lambda r: r["quantidade"], reverse=True)
    return resultado[:limite_itens]


# Rotulo de MATERIAL (nao de produto/santo) por chave_preco -- 12mm/16mm
# viram uma unica categoria "Medalha 1 lado" (mesmo material fisico, so
# tamanho diferente, ver conversa). Usado so pra quantidade_por_material
# abaixo (ver app.py:admin_analytics).
_MATERIAL_LABEL_POR_CHAVE = {
    "12mm": "Medalha 1 lado",
    "16mm": "Medalha 1 lado",
    "medalha_2lados": "Medalha 2 lados",
    "entremeio": "Entremeio 1 lado",
    "entremeio_2lados": "Entremeio 2 lados",
    "chaveiro": "Chaveiro 1 lado",
    "chaveiro_2lados": "Chaveiro 2 lados",
}


def quantidade_por_material(*, desde: datetime | None = None, ate: datetime | None = None) -> list[dict]:
    """[{"material": rotulo, "quantidade": int}, ...] a partir dos ITENS
    dos pedidos PAGOS no periodo, somando quantidade por MATERIAL (ver
    _MATERIAL_LABEL_POR_CHAVE) em vez de por santo/produto (ver
    produtos_mais_vendidos acima) -- pedido do usuario: "quantidade
    total de medalhas de 1 lado... e assim por diante de cada
    material". Sempre devolve as 6 categorias, mesmo com quantidade 0,
    pra dar visao completa do que mais consome estoque no periodo."""
    contagem = dict.fromkeys(dict.fromkeys(_MATERIAL_LABEL_POR_CHAVE.values()), 0)
    for itens in _itens_pagos_no_periodo(desde, ate):
        for item in itens:
            rotulo = _MATERIAL_LABEL_POR_CHAVE.get(item.get("chave_preco"))
            if rotulo:
                contagem[rotulo] += int(item.get("quantidade", 0))
    resultado = [{"material": rotulo, "quantidade": quantidade} for rotulo, quantidade in contagem.items()]
    resultado.sort(key=lambda r: r["quantidade"], reverse=True)
    return resultado


def taxa_clientes_recorrentes(dias: int) -> dict:
    """{"recorrentes": int, "total": int, "taxa_pct": float} -- de quantos
    documentos distintos pagaram no periodo, quantos ja tinham pelo
    menos 1 pedido pago ANTES do periodo comecar (cliente recorrente,
    nao so quem comprou 2x dentro da mesma janela)."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with _conexao() as conexao:
        documentos = [
            linha["cliente_documento"]
            for linha in conexao.execute(
                "SELECT DISTINCT cliente_documento FROM pedidos WHERE pago_em >= ? AND cliente_documento != ''",
                (limite,),
            ).fetchall()
        ]
        recorrentes = 0
        for documento in documentos:
            existe_antes = conexao.execute(
                "SELECT 1 FROM pedidos WHERE cliente_documento = ? AND pago_em < ? LIMIT 1",
                (documento, limite),
            ).fetchone()
            if existe_antes:
                recorrentes += 1
    total = len(documentos)
    taxa = round(recorrentes / total * 100, 2) if total else 0.0
    return {"recorrentes": recorrentes, "total": total, "taxa_pct": taxa}


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


def marcar_email_avaliacao_enviado(token: str, *, erro: str | None) -> dict | None:
    """1o e-mail pedindo avaliacao, disparado NA HORA que o pedido vira
    "entregue" (ver app.py:admin_pedido_status ->
    services/email.py:enviar_pedido_avaliacao) -- garante que so manda
    uma vez por pedido, mesmo se o formulario de status for reenviado
    sem querer. O 2o e-mail (mesmo conteudo, alguns dias depois) usa o
    par email_avaliacao_seguimento_enviado/erro abaixo, separado."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_avaliacao_enviado = 1, email_avaliacao_erro = ? WHERE token = ?",
            (erro, token),
        )
    return obter_pedido(token)


def listar_pedidos_entregues_para_seguimento_avaliacao(dias: int) -> list[dict]:
    """Pedidos "entregue" ha´ pelo menos `dias` dias que ainda nao
    receberam o 2o e-mail de avaliacao (mesmo conteudo do 1o, so que de
    seguimento -- ver app.py:_enviar_seguimento_avaliacao_entregues)."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with _conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT * FROM pedidos
            WHERE status = 'entregue' AND email_avaliacao_seguimento_enviado = 0
                AND entregue_em <= ?
            ORDER BY entregue_em ASC
            """,
            (limite,),
        ).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def marcar_email_avaliacao_seguimento_enviado(token: str, *, erro: str | None) -> dict | None:
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_avaliacao_seguimento_enviado = 1, "
            "email_avaliacao_seguimento_erro = ? WHERE token = ?",
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
                endereco_destinatario_uf = ?, endereco_destinatario_telefone = ?,
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
                destinatario.get("uf", ""), destinatario.get("telefone", ""),
                frete_descricao, frete_preco, frete_prazo_dias, total,
                forma_pagamento, valor_pago,
                token,
            ),
        )
    return obter_pedido(token)


def editar_valor(
    token: str, *, subtotal: float, frete_preco: float, valor_pago: float | None
) -> dict | None:
    """Corrige o valor de um pedido ja existente (ver conversa -- admin
    digitou errado no confirmar-venda manual do WhatsApp e so percebeu
    depois). Reconstroi total = subtotal + frete_preco, o mesmo
    invariante usado em criar_pedido/confirmar_venda_manual -- nunca
    deixa a pagina do pedido (templates/pedido.html) mostrar um
    Subtotal + Frete que nao bate com o Total. `valor_pago` fica None
    quando o pedido ainda nao foi pago (nao sobrescreve com 0)."""
    pedido = obter_pedido(token)
    if pedido is None:
        return None
    total = round(subtotal + frete_preco, 2)
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET subtotal = ?, frete_preco = ?, total = ?, valor_pago = ? WHERE token = ?",
            (subtotal, frete_preco, total, valor_pago, token),
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


def marcar_email_nota_fiscal_enviado(token: str, *, erro: str | None) -> dict | None:
    """E-mail "Nota fiscal disponível" (ver app.py:admin_pedido_status) --
    mesma logica de marcar_email_pedido_enviado_enviado, so que pra esse
    e-mail especifico."""
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET email_nota_fiscal_enviado = 1, email_nota_fiscal_erro = ? WHERE token = ?",
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


def reativar_pedido_cancelado(token: str) -> dict | None:
    """Reaproveita um pedido CANCELADO (ver e-mail de recuperacao,
    services/email.py:enviar_pedido_cancelado) -- volta pra "pendente"
    com os MESMOS itens/foto personalizada, pronto pra gerar um novo
    link de pagamento ou boleto (ver app.py:pedido_reativar_pix/
    pedido_reativar_boleto). So funciona se ainda estiver "cancelado"
    (idempotente -- se ja foi pago ou reativado por outro clique/aba,
    nao mexe em nada, devolve como esta´).

    Reseta criado_em e os flags de lembrete/cancelamento pro pedido se
    comportar como um "pendente" novinho pros jobs agendados (ver
    listar_pedidos_pendentes_para_lembrete/cancelar) -- sem isso, esses
    jobs veriam email_lembrete_enviado_em de dias atras e cancelariam
    de novo no proximo ciclo, quase na hora."""
    pedido = obter_pedido(token)
    if pedido is None or pedido["status"] != "cancelado":
        return pedido
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            """
            UPDATE pedidos SET
                status = 'pendente', criado_em = ?, cancelado_em = NULL,
                email_lembrete_enviado = 0, email_lembrete_enviado_em = NULL,
                email_cancelado_enviado = 0
            WHERE token = ?
            """,
            (agora, token),
        )
    return obter_pedido(token)


def listar_pedidos_cancelados_para_limpar_imagens(dias: int) -> list[dict]:
    """Pedidos "cancelado" ha´ pelo menos `dias` dias, cujas imagens
    personalizadas (se tiver) ainda nao foram limpas -- usado pelo job
    agendado (ver app.py:_limpar_imagens_pedidos_cancelados). Um pedido
    REATIVADO (ver reativar_pedido_cancelado acima) sai do status
    "cancelado" e some sozinho dessa lista, protegendo a imagem."""
    inicializar_db()
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    with _conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT * FROM pedidos
            WHERE status = 'cancelado' AND imagens_pedido_apagadas = 0
                AND cancelado_em IS NOT NULL AND cancelado_em <= ?
            ORDER BY cancelado_em ASC
            """,
            (limite,),
        ).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def marcar_imagens_pedido_apagadas(token: str) -> None:
    with _conexao() as conexao:
        conexao.execute("UPDATE pedidos SET imagens_pedido_apagadas = 1 WHERE token = ?", (token,))


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


def arquivar_pedido(token: str) -> dict | None:
    """Tira o pedido da lista principal do painel (ver
    app.py:admin_pedido_arquivar) -- NAO muda o status nem avisa o
    cliente, so marca arquivado=1 pra sumir da visao do dia a dia
    (pedidos antigos/resolvidos que so ocupam espaco na lista). De
    QUALQUER status, inclusive excluido/cancelado. Reversivel a
    qualquer momento via desarquivar_pedido."""
    if obter_pedido(token) is None:
        return None
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET arquivado = 1, arquivado_em = ? WHERE token = ?",
            (agora, token),
        )
    return obter_pedido(token)


def desarquivar_pedido(token: str) -> dict | None:
    """Desfaz arquivar_pedido -- volta o pedido pra lista principal."""
    if obter_pedido(token) is None:
        return None
    with _conexao() as conexao:
        conexao.execute(
            "UPDATE pedidos SET arquivado = 0, arquivado_em = NULL WHERE token = ?",
            (token,),
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


def producao_dias_uteis_para_quantidade(quantidade_total: int) -> int:
    """Prazo de producao (dias uteis) pra um pedido com essa quantidade
    TOTAL de pecas (todos os formatos somados) -- ver config.py:
    FAIXAS_PRODUCAO_DIAS_UTEIS. Abaixo da primeira faixa cadastrada,
    vale PRODUCAO_DIAS_UTEIS (a promessa base de sempre)."""
    dias = PRODUCAO_DIAS_UTEIS
    for inicio, valor in sorted(FAIXAS_PRODUCAO_DIAS_UTEIS.items()):
        if quantidade_total >= inicio:
            dias = valor
    return dias


def previsoes_do_pedido(pedido: dict) -> dict:
    """Previsao de envio (pago_em + dias de producao, que cresce com a
    quantidade do pedido -- ver producao_dias_uteis_para_quantidade) e
    de entrega (frete_prazo_dias dias uteis a partir do envio, quando
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
    resultado = {"previsao_envio": None, "previsao_entrega": None, "enviado_antecipado": False, "dias_producao": None}
    pago_em = pedido.get("pago_em")
    if not pago_em:
        return resultado
    quantidade_total = sum(int(item.get("quantidade", 0)) for item in pedido.get("itens", []))
    dias_producao = producao_dias_uteis_para_quantidade(quantidade_total)
    resultado["dias_producao"] = dias_producao
    data_pago = datetime.fromisoformat(pago_em)
    previsao_envio = somar_dias_uteis(data_pago, dias_producao)
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


# ---- login por CPF em /meus-pedidos (ver app.py) -- extra pra quem quer
# ver de novo como estao os proprios pedidos, sem precisar guardar cada
# link de acompanhamento avulso. Baixar a foto personalizada continua so
# por fora (WhatsApp), nao muda nada aqui -- essa tela so mostra status.

_CODIGO_VERIFICACAO_VALIDADE_MINUTOS = 10
_CODIGO_VERIFICACAO_MAX_TENTATIVAS = 5


def _somente_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def _hash_codigo_verificacao(documento: str, codigo: str) -> str:
    return hashlib.sha256(f"{documento}:{codigo}".encode()).hexdigest()


def gerar_codigo_verificacao_documento(documento: str) -> str:
    """Gera um codigo numerico de 6 digitos pro login em /meus-pedidos e
    grava so o HASH dele (nunca o codigo em texto puro), com validade de
    _CODIGO_VERIFICACAO_VALIDADE_MINUTOS -- REPLACE (via ON CONFLICT)
    sobrescreve qualquer codigo anterior desse mesmo documento, entao a
    tabela nunca acumula mais de uma linha por documento em andamento.
    Chamado sempre que alguem pede o codigo, mesmo pra um documento sem
    nenhum pedido -- quem decide se manda e-mail de verdade e´ o
    chamador (app.py), pra essa funcao nunca revelar se o CPF existe ou
    nao na base so pelo tempo de resposta."""
    inicializar_db()
    documento = _somente_digitos(documento)
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    agora = datetime.now(timezone.utc)
    expira_em = (agora + timedelta(minutes=_CODIGO_VERIFICACAO_VALIDADE_MINUTOS)).isoformat()
    with _conexao() as conexao:
        conexao.execute(
            """
            INSERT INTO codigos_verificacao_documento (documento, codigo_hash, expira_em, tentativas, criado_em)
            VALUES (?, ?, ?, 0, ?)
            ON CONFLICT(documento) DO UPDATE SET
                codigo_hash = excluded.codigo_hash,
                expira_em = excluded.expira_em,
                tentativas = 0,
                criado_em = excluded.criado_em
            """,
            (documento, _hash_codigo_verificacao(documento, codigo), expira_em, agora.isoformat()),
        )
    return codigo


def verificar_codigo_documento(documento: str, codigo: str) -> bool:
    """True so quando o codigo bate, ainda nao expirou e nao passou do
    limite de tentativas (protege contra forca bruta nos 6 digitos --
    ver _CODIGO_VERIFICACAO_MAX_TENTATIVAS). Codigo certo OU numero de
    tentativas esgotado apagam a linha -- um codigo so serve uma vez;
    certo ou errado demais vezes forca pedir um novo."""
    inicializar_db()
    documento = _somente_digitos(documento)
    codigo = _somente_digitos(codigo)
    with _conexao() as conexao:
        linha = conexao.execute(
            "SELECT * FROM codigos_verificacao_documento WHERE documento = ?", (documento,)
        ).fetchone()
        if linha is None:
            return False
        if linha["tentativas"] >= _CODIGO_VERIFICACAO_MAX_TENTATIVAS:
            conexao.execute("DELETE FROM codigos_verificacao_documento WHERE documento = ?", (documento,))
            return False
        if datetime.fromisoformat(linha["expira_em"]) < datetime.now(timezone.utc):
            conexao.execute("DELETE FROM codigos_verificacao_documento WHERE documento = ?", (documento,))
            return False
        bate = hmac.compare_digest(linha["codigo_hash"], _hash_codigo_verificacao(documento, codigo))
        if bate:
            conexao.execute("DELETE FROM codigos_verificacao_documento WHERE documento = ?", (documento,))
            return True
        conexao.execute(
            "UPDATE codigos_verificacao_documento SET tentativas = tentativas + 1 WHERE documento = ?",
            (documento,),
        )
        return False


def limpar_codigos_verificacao_expirados() -> int:
    """Job agendado (ver app.py:_iniciar_scheduler_jobs) -- apaga codigos
    vencidos que ninguem verificou, pra tabela nunca crescer sem limite
    (ela so guarda um login em andamento por documento, mas sem essa
    limpeza um codigo pedido e nunca usado ficaria pra sempre)."""
    inicializar_db()
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conexao:
        cursor = conexao.execute("DELETE FROM codigos_verificacao_documento WHERE expira_em < ?", (agora,))
        return cursor.rowcount


def listar_pedidos_por_documento(documento: str) -> list[dict]:
    """Pedidos de um CPF/CNPJ pra pagina /meus-pedidos -- mais recentes
    primeiro. Compara so os DIGITOS (cliente_documento fica gravado
    formatado, ex: "123.456.789-00") -- REPLACE encadeado tira pontuacao
    de CPF (.  -) e CNPJ (.  /  -) direto no SQL. Nunca mostra lead de
    whatsapp (sem checkout de verdade, ver criar_pedido) nem pedido
    excluido pelo admin (ver excluir_pedido)."""
    inicializar_db()
    documento = _somente_digitos(documento)
    if not documento:
        return []
    with _conexao() as conexao:
        linhas = conexao.execute(
            """
            SELECT * FROM pedidos
            WHERE REPLACE(REPLACE(REPLACE(cliente_documento, '.', ''), '-', ''), '/', '') = ?
              AND status NOT IN ('whatsapp', 'excluido')
            ORDER BY criado_em DESC
            """,
            (documento,),
        ).fetchall()
    pedidos = []
    for linha in linhas:
        pedido = dict(linha)
        pedido["itens"] = json.loads(pedido["itens"])
        pedidos.append(pedido)
    return pedidos


def email_para_documento(documento: str) -> str | None:
    """E-mail do pedido mais recente desse documento -- pra onde manda o
    codigo de verificacao (ver app.py). None se o documento nunca fez
    nenhum pedido de verdade (mesmo filtro de listar_pedidos_por_documento)."""
    for pedido in listar_pedidos_por_documento(documento):
        if pedido.get("cliente_email"):
            return pedido["cliente_email"]
    return None


def numero_modelo_personalizada(pedido_token: str, item_index: int, lado: str = "") -> int:
    """Numero sequencial (1, 2, 3...) dessa foto personalizada -- ver
    app.py:_atribuir_numeros_modelo_personalizada. `lado` e´ "" pra item
    de 1 lado (um numero so pra peca inteira) ou "lado1"/"lado2" pra
    item de 2 lados (cada foto numerada separado, mesmo as duas
    fazendo parte da mesma peca fisica -- ver conversa). Primeira vez
    que essa (pedido_token, item_index, lado) e´ pedida, atribui o
    PROXIMO numero da fila (MAX atual + 1) e grava; nas proximas vezes
    so devolve o mesmo numero ja gravado -- nunca muda depois de
    atribuido, mesmo que o pedido seja visto de novo dias depois."""
    inicializar_db()
    with _conexao() as conexao:
        linha = conexao.execute(
            "SELECT numero FROM numeros_modelo_personalizada WHERE pedido_token = ? AND item_index = ? AND lado = ?",
            (pedido_token, item_index, lado),
        ).fetchone()
        if linha is not None:
            return linha["numero"]
        proximo = conexao.execute("SELECT COALESCE(MAX(numero), 0) + 1 FROM numeros_modelo_personalizada").fetchone()[0]
        conexao.execute(
            "INSERT INTO numeros_modelo_personalizada (pedido_token, item_index, lado, numero, atribuido_em) "
            "VALUES (?, ?, ?, ?, ?)",
            (pedido_token, item_index, lado, proximo, datetime.now(timezone.utc).isoformat()),
        )
        return proximo


def resetar_numeracao_modelo_personalizada() -> None:
    """Zera a numeracao de numero_modelo_personalizada -- o PROXIMO item
    personalizado visto (painel ou CSV) volta a comecar do 1. So chamar
    quando a usuaria pedir explicitamente (ver conversa: "a contagem nao
    reseta, so quando eu falar") -- sem uso nenhum automatico/agendado."""
    inicializar_db()
    with _conexao() as conexao:
        conexao.execute("DELETE FROM numeros_modelo_personalizada")
