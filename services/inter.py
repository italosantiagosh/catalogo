"""
Boleto bancario via API Cobranca (Boleto com Pix) do Banco Inter --
documentacao real conferida pelo usuario (PDFs exportados do portal do
desenvolvedor, ver conversa), NAO da memoria/treinamento -- os hosts da
API (cdpj.partners.bancointer.com.br e o sandbox) estao bloqueados
nesse ambiente de desenvolvimento, entao nada aqui foi testado contra a
API de verdade. A primeira emissao real precisa ser conferida com
atencao (sobretudo os nomes exatos dos campos na resposta).

Autenticacao: OAuth2 client_credentials (client_id + client_secret) +
certificado mTLS (obrigatorio em toda chamada, nao so no token) -- ver
config.py pras variaveis de ambiente. Token dura 1h, reaproveitado
entre chamadas (ver _obter_token abaixo).

Fluxo escolhido -- POLLING, nao webhook: a documentacao confirma que a
API dispara um callback quando o boleto e´ pago ("apos a emissao...um
callback com os dados da cobranca... pro seu webhook cadastrado"), mas
a pagina de COMO CADASTRAR esse webhook e o formato exato do callback
nao foi enviada (so vieram os PDFs de "API Cobranca" e "Autenticacao
OAuth"). Em vez de adivinhar esse formato (arriscado numa integracao
que mexe com dinheiro), o pagamento e´ confirmado consultando
GET /cobrancas/{codigoSolicitacao} periodicamente (ver
app.py:_verificar_boletos_inter_pendentes) -- schema desse endpoint
esta´ 100% confirmado no PDF. Como a propria regra de negocio ja avisa
"confirmado em ate 2 dias uteis", nao ha perda real de responsividade
nisso -- webhook so faria sentido se a confirmacao precisasse ser
instantanea.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import requests

from config import (
    INTER_AMBIENTE,
    INTER_CERTIFICADO_PEM,
    INTER_CHAVE_PRIVADA_PEM,
    INTER_CLIENT_ID,
    INTER_CLIENT_SECRET,
    INTER_CONTA_CORRENTE,
)

# URLs confirmadas no PDF de Autenticacao OAuth + API Cobranca.
_BASE_URL = {
    "producao": "https://cdpj.partners.bancointer.com.br",
    "sandbox": "https://cdpj-sandbox.partners.uatinter.co",
}

# Numero de dias corridos ate o vencimento (a partir de hoje) -- nunca
# hoje mesmo, a API so aceita vencimento no dia corrente ate as 19h59
# (ver PDF), entao alguns dias de folga evita cair nesse limite.
DIAS_ATE_VENCIMENTO = 3
# Dias corridos APOS o vencimento ate a Inter cancelar automaticamente
# a cobranca nao paga (numDiasAgenda, 0 a 60 -- ver PDF).
DIAS_PARA_CANCELAMENTO_AUTOMATICO = 5


def _configurado() -> bool:
    return bool(INTER_CLIENT_ID and INTER_CLIENT_SECRET and INTER_CERTIFICADO_PEM and INTER_CHAVE_PRIVADA_PEM)


# Arquivos temporarios com o conteudo do certificado/chave -- o cliente
# HTTP (requests) exige caminho de arquivo pro mTLS, nao aceita o
# conteudo direto. Escritos uma unica vez (na primeira chamada) e
# reaproveitados pelo resto da vida do processo -- mesma suposicao de
# 1 worker do gunicorn ja usada em outras partes do site (ver
# Procfile/render.yaml e app.py:_registrar_download).
_arquivos_certificado: tuple[str, str] | None = None


def _caminho_certificado() -> tuple[str, str]:
    global _arquivos_certificado
    if _arquivos_certificado is None:
        pasta = Path(tempfile.mkdtemp(prefix="inter-cert-"))
        caminho_cert = pasta / "certificado.crt"
        caminho_chave = pasta / "chave.key"
        caminho_cert.write_text(INTER_CERTIFICADO_PEM)
        caminho_chave.write_text(INTER_CHAVE_PRIVADA_PEM)
        _arquivos_certificado = (str(caminho_cert), str(caminho_chave))
    return _arquivos_certificado


_token_cache: dict | None = None  # {"access_token": ..., "expira_em": <epoch>}


def _obter_token() -> str | None:
    """Reaproveita o token entre chamadas (dura 1h, ver PDF) -- pede um
    novo so quando faltar menos de 1 minuto pra expirar, margem de
    seguranca contra corrida entre "token valido" e "token expirou no
    meio da chamada seguinte"."""
    global _token_cache
    if _token_cache and _token_cache["expira_em"] - time.time() > 60:
        return _token_cache["access_token"]

    base_url = _BASE_URL.get(INTER_AMBIENTE, _BASE_URL["sandbox"])
    try:
        resposta = requests.post(
            f"{base_url}/oauth/v2/token",
            data={
                "client_id": INTER_CLIENT_ID,
                "client_secret": INTER_CLIENT_SECRET,
                "grant_type": "client_credentials",
                "scope": "boleto-cobranca.read boleto-cobranca.write",
            },
            cert=_caminho_certificado(),
            timeout=15,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except (requests.RequestException, ValueError):
        return None

    token = dados.get("access_token")
    if not token:
        return None
    _token_cache = {"access_token": token, "expira_em": time.time() + int(dados.get("expires_in", 3600))}
    return token


def _cabecalhos(token: str) -> dict:
    cabecalhos = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if INTER_CONTA_CORRENTE:
        cabecalhos["x-conta-corrente"] = INTER_CONTA_CORRENTE
    return cabecalhos


def _telefone_ddd_numero(telefone: str) -> tuple[str, str]:
    """`cliente.telefone` no site vem como uma string so (ex:
    "84999999999", ver checkout) -- a Inter pede ddd e numero
    separados. Primeiros 2 digitos = DDD, resto = numero (formato
    brasileiro padrao)."""
    digitos = "".join(c for c in telefone if c.isdigit())
    if len(digitos) < 3:
        return "", digitos
    return digitos[:2], digitos[2:]


def emitir_boleto(*, seu_numero: str, valor: float, cliente: dict, endereco: dict) -> dict:
    """Emite uma cobranca (boleto + Pix embutido, ver PDF) pro
    pagador/endereco informados. Devolve
    {"codigo_solicitacao": "<uuid>"} ou {"erro": "..."}. `seu_numero`
    e´ o campo "Seu Numero" (<=15 caracteres, ver PDF) -- usamos o
    codigo curto do pedido (services.pedidos:_gerar_codigo, 6
    caracteres)."""
    if not _configurado():
        return {"erro": "Boleto não configurado (faltam credenciais do Banco Inter)."}
    token = _obter_token()
    if not token:
        return {"erro": "Não foi possível autenticar com o Banco Inter agora."}

    ddd, numero_telefone = _telefone_ddd_numero(cliente.get("telefone", ""))
    hoje = time.strftime("%Y-%m-%d")
    # soma DIAS_ATE_VENCIMENTO dias corridos (a API aceita corridos, nao
    # uteis, pro vencimento -- diferente do calculo de previsao de
    # producao em services/pedidos.py, que e´ dias uteis)
    from datetime import datetime, timedelta

    data_vencimento = (datetime.strptime(hoje, "%Y-%m-%d") + timedelta(days=DIAS_ATE_VENCIMENTO)).strftime(
        "%Y-%m-%d"
    )

    payload = {
        "seuNumero": seu_numero[:15],
        "valorNominal": round(valor, 2),
        "dataVencimento": data_vencimento,
        "numDiasAgenda": DIAS_PARA_CANCELAMENTO_AUTOMATICO,
        "pagador": {
            "email": cliente.get("email", ""),
            "ddd": ddd,
            "telefone": numero_telefone,
            "numero": endereco.get("numero", ""),
            "complemento": endereco.get("complemento", ""),
            "cpfCnpj": "".join(c for c in cliente.get("documento", "") if c.isdigit()),
            "tipoPessoa": "JURIDICA" if cliente.get("tipo_pessoa") == "juridica" else "FISICA",
            "nome": cliente.get("nome", ""),
            "endereco": endereco.get("logradouro", ""),
            "bairro": endereco.get("bairro", ""),
            "cidade": endereco.get("cidade", ""),
            "uf": endereco.get("uf", ""),
            "cep": "".join(c for c in endereco.get("cep", "") if c.isdigit()),
        },
        "formasRecebimento": ["BOLETO", "PIX"],
    }

    base_url = _BASE_URL.get(INTER_AMBIENTE, _BASE_URL["sandbox"])
    try:
        resposta = requests.post(
            f"{base_url}/cobranca/v3/cobrancas",
            json=payload,
            headers=_cabecalhos(token),
            cert=_caminho_certificado(),
            timeout=15,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except requests.RequestException as exc:
        return {"erro": f"Não foi possível emitir o boleto agora ({exc})."}
    except ValueError:
        return {"erro": "Resposta inválida do Banco Inter."}

    codigo_solicitacao = dados.get("codigoSolicitacao")
    if not codigo_solicitacao:
        return {"erro": "O Banco Inter não retornou o código da cobrança."}
    return {"codigo_solicitacao": codigo_solicitacao}


def consultar_cobranca(codigo_solicitacao: str) -> dict:
    """Devolve o estado atual da cobranca (situacao, linha digitavel,
    codigo de barras, Pix copia-e-cola -- schema confirmado no PDF,
    ver "Recuperar cobranca") ou {"erro": "..."}."""
    if not _configurado():
        return {"erro": "Boleto não configurado (faltam credenciais do Banco Inter)."}
    token = _obter_token()
    if not token:
        return {"erro": "Não foi possível autenticar com o Banco Inter agora."}

    base_url = _BASE_URL.get(INTER_AMBIENTE, _BASE_URL["sandbox"])
    try:
        resposta = requests.get(
            f"{base_url}/cobranca/v3/cobrancas/{codigo_solicitacao}",
            headers=_cabecalhos(token),
            cert=_caminho_certificado(),
            timeout=15,
        )
        resposta.raise_for_status()
        return resposta.json()
    except requests.RequestException as exc:
        return {"erro": f"Não foi possível consultar o boleto agora ({exc})."}
    except ValueError:
        return {"erro": "Resposta inválida do Banco Inter."}


def baixar_pdf(codigo_solicitacao: str) -> dict:
    """Devolve {"pdf_base64": "..."} (campo "pdf" do PDF de
    documentacao, ja em base64) ou {"erro": "..."}."""
    if not _configurado():
        return {"erro": "Boleto não configurado (faltam credenciais do Banco Inter)."}
    token = _obter_token()
    if not token:
        return {"erro": "Não foi possível autenticar com o Banco Inter agora."}

    base_url = _BASE_URL.get(INTER_AMBIENTE, _BASE_URL["sandbox"])
    try:
        resposta = requests.get(
            f"{base_url}/cobranca/v3/cobrancas/{codigo_solicitacao}/pdf",
            headers=_cabecalhos(token),
            cert=_caminho_certificado(),
            timeout=15,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except requests.RequestException as exc:
        return {"erro": f"Não foi possível baixar o boleto agora ({exc})."}
    except ValueError:
        return {"erro": "Resposta inválida do Banco Inter."}

    pdf_base64 = dados.get("pdf")
    if not pdf_base64:
        return {"erro": "O Banco Inter não retornou o PDF do boleto."}
    return {"pdf_base64": pdf_base64}
