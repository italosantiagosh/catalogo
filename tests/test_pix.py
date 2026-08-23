from __future__ import annotations

import services.pix as pix


def test_crc16_vetor_de_teste_conhecido():
    # CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) de "123456789" e um
    # vetor de teste publico bem conhecido -- confirma que a
    # implementacao bate com o algoritmo padrao usado pelo Pix/EMV.
    assert pix._crc16("123456789") == "29B1"


def test_gerar_copia_cola_estrutura_basica(monkeypatch):
    monkeypatch.setattr(pix, "PIX_CHAVE", "39390354000125")
    monkeypatch.setattr(pix, "PIX_NOME_RECEBEDOR", "NOVE DE JULHO")
    monkeypatch.setattr(pix, "PIX_CIDADE", "NATAL")

    codigo = pix.gerar_copia_cola(150.0, "PEDIDO123")

    assert codigo.startswith("000201")  # Payload Format Indicator
    assert "010212" in codigo  # Point of Initiation Method = 12
    assert "0014BR.GOV.BCB.PIX" in codigo  # GUI do Pix
    assert "0114" + "39390354000125" in codigo  # chave Pix (14 digitos)
    assert "5303986" in codigo  # moeda BRL
    assert "5406150.00" in codigo  # valor com 2 casas decimais
    assert "5802BR" in codigo  # pais
    assert "5913NOVE DE JULHO" in codigo  # nome do recebedor
    assert "6005NATAL" in codigo  # cidade
    assert "0509PEDIDO123" in codigo  # txid
    assert codigo.endswith(codigo[-4:])  # CRC de 4 caracteres hex no final
    assert len(codigo) - 4 == len(codigo[:-4])


def test_gerar_copia_cola_crc_bate_com_o_payload(monkeypatch):
    monkeypatch.setattr(pix, "PIX_CHAVE", "39390354000125")
    monkeypatch.setattr(pix, "PIX_NOME_RECEBEDOR", "NOVE DE JULHO")
    monkeypatch.setattr(pix, "PIX_CIDADE", "NATAL")

    codigo = pix.gerar_copia_cola(25.90, "ABC123")
    payload_sem_crc = codigo[:-4]
    crc_esperado = pix._crc16(payload_sem_crc)
    assert codigo[-4:] == crc_esperado


def test_gerar_copia_cola_txid_padrao_quando_nao_informado(monkeypatch):
    monkeypatch.setattr(pix, "PIX_CHAVE", "39390354000125")
    monkeypatch.setattr(pix, "PIX_NOME_RECEBEDOR", "NOVE DE JULHO")
    monkeypatch.setattr(pix, "PIX_CIDADE", "NATAL")

    codigo = pix.gerar_copia_cola(10.0)
    assert "0503***" in codigo


def test_gerar_copia_cola_sanitiza_acentos_e_caracteres_invalidos(monkeypatch):
    monkeypatch.setattr(pix, "PIX_CHAVE", "39390354000125")
    monkeypatch.setattr(pix, "PIX_NOME_RECEBEDOR", "Nove de Julho Ltda.")
    monkeypatch.setattr(pix, "PIX_CIDADE", "São Gonçalo do Amarante")

    codigo = pix.gerar_copia_cola(10.0)
    # sem acento, maiusculo, sem pontuacao -- so letras/numeros/espaco
    assert "NOVE DE JULHO LTDA" in codigo
    assert "6015SAO GONCALO DO" in codigo  # truncado em 15 caracteres


def test_gerar_qr_data_uri_retorna_png_base64():
    codigo = pix.gerar_copia_cola(10.0, "X")
    data_uri = pix.gerar_qr_data_uri(codigo)
    assert data_uri.startswith("data:image/png;base64,")
    assert len(data_uri) > 100
