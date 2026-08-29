from __future__ import annotations

from services.documentos import cnpj_valido, cpf_valido, documento_valido, numero_whatsapp, telefone_valido


def test_cpf_valido_aceita_documento_conhecido():
    assert cpf_valido("111.444.777-35") is True
    assert cpf_valido("11144477735") is True


def test_cpf_invalido_digito_verificador_errado():
    assert cpf_valido("111.444.777-36") is False


def test_cpf_invalido_todos_digitos_iguais():
    assert cpf_valido("111.111.111-11") is False


def test_cpf_invalido_tamanho_errado():
    assert cpf_valido("123456789") is False
    assert cpf_valido("") is False


def test_cnpj_valido_aceita_documento_conhecido():
    assert cnpj_valido("11.222.333/0001-81") is True
    assert cnpj_valido("11222333000181") is True


def test_cnpj_invalido_digito_verificador_errado():
    assert cnpj_valido("11.222.333/0001-82") is False


def test_cnpj_invalido_todos_digitos_iguais():
    assert cnpj_valido("11.111.111/1111-11") is False


def test_cnpj_invalido_tamanho_errado():
    assert cnpj_valido("123456") is False


def test_documento_valido_escolhe_algoritmo_pelo_tipo_pessoa():
    assert documento_valido("fisica", "111.444.777-35") is True
    assert documento_valido("juridica", "111.444.777-35") is False
    assert documento_valido("juridica", "11.222.333/0001-81") is True


def test_telefone_valido_aceita_celular_com_9():
    assert telefone_valido("(84) 99999-9999") is True
    assert telefone_valido("84999999999") is True


def test_telefone_valido_aceita_fixo_sem_9():
    assert telefone_valido("(84) 3333-4444") is True


def test_telefone_invalido_ddd_inexistente():
    # 20, 23, 36, 60 nunca foram atribuidos pela Anatel
    assert telefone_valido("20999999999") is False
    assert telefone_valido("60333333333") is False


def test_telefone_invalido_celular_sem_o_9_na_frente():
    assert telefone_valido("84899999999") is False  # 11 digitos mas sem o 9 obrigatorio


def test_telefone_invalido_tamanho_errado():
    assert telefone_valido("849999999") is False  # 9 digitos, nem fixo nem celular
    assert telefone_valido("") is False


def test_numero_whatsapp_adiciona_55_quando_falta():
    assert numero_whatsapp("(84) 99999-9999") == "5584999999999"


def test_numero_whatsapp_nao_duplica_55_ja_presente():
    assert numero_whatsapp("5584999999999") == "5584999999999"
