"""
Gerador de Pix "Copia e Cola" (BR Code / EMV QR Code -- padrao publicado
pelo Banco Central) com o valor do pedido ja preenchido.

Importante: isso NAO e integracao com a API de Pix Dinamico de um banco
ou PSP (Efi, Mercado Pago, Banco Inter etc.) -- aquilo exige
credenciais/certificado de uma conta digital e da confirmacao
automatica de pagamento via webhook. O que este modulo gera e um BR
Code "estatico com valor": o mesmo formato que qualquer maquininha ou
QR impresso usa, montado localmente so com a chave Pix (nenhum
segredo/API necessaria) -- da pra colar em qualquer app bancario e
pagar o valor exato do pedido, mas o recebimento continua sendo
conferido manualmente pelo vendedor (como ja e feito hoje).

Formato (campos TLV obrigatorios pro nosso caso, id: nome):
    00  Payload Format Indicator ("01")
    01  Point of Initiation Method ("12" -- codigo pensado pra uma
        unica cobranca, mesmo sem passar por um PSP)
    26  Merchant Account Information (GUI + chave Pix)
    52  Merchant Category Code ("0000" -- nao classificado)
    53  Transaction Currency ("986" -- BRL)
    54  Transaction Amount
    58  Country Code ("BR")
    59  Merchant Name
    60  Merchant City
    62  Additional Data Field Template (txid)
    63  CRC16 (calculado por cima de tudo, inclusive o proprio "6304")
"""

from __future__ import annotations

import base64
import io
import re
import unicodedata

import qrcode

from config import PIX_CHAVE, PIX_CIDADE, PIX_NOME_RECEBEDOR

GUI_PIX = "BR.GOV.BCB.PIX"


def _campo(id_: str, valor: str) -> str:
    return f"{id_}{len(valor):02d}{valor}"


def _crc16(payload: str) -> str:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) -- o mesmo usado
    pelo padrao Pix/EMV. Ver test_pix.py pro vetor de teste conhecido
    ("123456789" -> "29B1") que confirma a implementacao."""
    polinomio = 0x1021
    resultado = 0xFFFF
    for byte in payload.encode("utf-8"):
        resultado ^= byte << 8
        for _ in range(8):
            if resultado & 0x8000:
                resultado = ((resultado << 1) ^ polinomio) & 0xFFFF
            else:
                resultado = (resultado << 1) & 0xFFFF
    return f"{resultado:04X}"


def _sanitizar(texto: str, tamanho_max: int, *, permitir_espaco: bool, aleatorio_padrao: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    padrao = r"[^A-Za-z0-9 ]" if permitir_espaco else r"[^A-Za-z0-9]"
    limpo = re.sub(padrao, "", sem_acento).strip().upper()
    return limpo[:tamanho_max] or aleatorio_padrao


def gerar_copia_cola(valor: float, txid: str = "***") -> str:
    """Monta o BR Code Pix (EMV) com o valor do pedido ja preenchido."""
    chave = _sanitizar(PIX_CHAVE, 77, permitir_espaco=False, aleatorio_padrao="CHAVEPIX")
    nome = _sanitizar(PIX_NOME_RECEBEDOR, 25, permitir_espaco=True, aleatorio_padrao="RECEBEDOR")
    cidade = _sanitizar(PIX_CIDADE, 15, permitir_espaco=True, aleatorio_padrao="BRASIL")
    txid_limpo = _sanitizar(txid, 25, permitir_espaco=False, aleatorio_padrao="***")

    conta_pix = _campo("00", GUI_PIX) + _campo("01", chave)
    dados_adicionais = _campo("05", txid_limpo)

    payload = (
        _campo("00", "01")
        + _campo("01", "12")
        + _campo("26", conta_pix)
        + _campo("52", "0000")
        + _campo("53", "986")
        + _campo("54", f"{max(valor, 0):.2f}")
        + _campo("58", "BR")
        + _campo("59", nome)
        + _campo("60", cidade)
        + _campo("62", dados_adicionais)
    )
    payload_com_id_crc = payload + "6304"
    return payload_com_id_crc + _crc16(payload_com_id_crc)


def gerar_qr_data_uri(copia_cola: str) -> str:
    imagem = qrcode.make(copia_cola)
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
