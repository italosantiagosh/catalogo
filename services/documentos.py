"""
Validacao de CPF/CNPJ (digito verificador, algoritmo modulo-11 publicado
pela Receita Federal) -- so confere se o numero e´ MATEMATICAMENTE
valido (bate o digito verificador), NAO confirma que o documento existe
de verdade cadastrado na Receita (isso exigiria uma consulta paga a uma
API externa, fora do escopo daqui -- ver conversa "verificar CPF/CNPJ
pra saber se e´ existente. Pra nao ter dado errado", que na pratica e´
sobre pegar erro de digitacao, nao autenticidade de cadastro).

Usado tanto no servidor (app.py -- nunca confia so na validacao do
navegador) quanto reaproveitado como referencia pra mesma logica em
JS (ver static/js/carrinho_pagina.js:cpfValido/cnpjValido).
"""

from __future__ import annotations

import re


def _so_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def cpf_valido(cpf: str) -> bool:
    cpf = _so_digitos(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
        digito = ((soma * 10) % 11) % 10
        if digito != int(cpf[i]):
            return False
    return True


def cnpj_valido(cnpj: str) -> bool:
    cnpj = _so_digitos(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    d1 = 11 - (soma1 % 11)
    d1 = 0 if d1 >= 10 else d1
    if d1 != int(cnpj[12]):
        return False
    soma2 = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    d2 = 11 - (soma2 % 11)
    d2 = 0 if d2 >= 10 else d2
    if d2 != int(cnpj[13]):
        return False
    return True


def documento_valido(tipo_pessoa: str, documento: str) -> bool:
    """Atalho pra validar de acordo com o tipo de pessoa ja escolhido no
    formulario -- fisica usa CPF (11 digitos), juridica usa CNPJ (14)."""
    if tipo_pessoa == "juridica":
        return cnpj_valido(documento)
    return cpf_valido(documento)


# DDDs realmente atribuidos pela Anatel (67 no total) -- lista publica,
# estavel (novo DDD e´ raro e sempre noticiado). Faixas como 20, 23,
# 25-26, 29, 36, 39, 50, 52, 56-60, 70, 72, 76, 78, 80, 90 NUNCA foram
# atribuidas, entao numero com esses DDDs e´ garantido invalido -- pega
# muito erro de digitacao que so checar "tem 11 digitos" nao pegaria.
_DDDS_VALIDOS = frozenset(
    {
        11, 12, 13, 14, 15, 16, 17, 18, 19,
        21, 22, 24, 27, 28,
        31, 32, 33, 34, 35, 37, 38,
        41, 42, 43, 44, 45, 46, 47, 48, 49,
        51, 53, 54, 55,
        61, 62, 63, 64, 65, 66, 67, 68, 69,
        71, 73, 74, 75, 77, 79,
        81, 82, 83, 84, 85, 86, 87, 88, 89,
        91, 92, 93, 94, 95, 96, 97, 98, 99,
    }
)


def telefone_valido(telefone: str) -> bool:
    """So confere FORMATO (DDD real + 8 digitos fixo/9 celular) -- NAO
    confirma que o numero existe/recebe chamada de verdade nem que tem
    WhatsApp (isso exigiria uma API paga de verificacao, fora do escopo
    aqui, mesmo raciocinio de documento_valido acima). Pega os erros
    mais comuns: poucos/muitos digitos, DDD que nunca existiu, celular
    sem o 9 na frente (obrigatorio desde 2016 -- ver conversa, usuario
    relatou problema com numero invalido no site antigo)."""
    digitos = _so_digitos(telefone)
    if len(digitos) not in (10, 11):
        return False
    ddd = int(digitos[:2])
    if ddd not in _DDDS_VALIDOS:
        return False
    if len(digitos) == 11 and digitos[2] != "9":
        return False
    return True


def numero_whatsapp(telefone: str) -> str:
    """Numero so com digitos, com o "55" (Brasil) na frente -- formato
    que a URL https://wa.me/<numero> espera (ver
    templates/admin_pedido_detalhe.html)."""
    digitos = _so_digitos(telefone)
    if digitos and not digitos.startswith("55"):
        digitos = f"55{digitos}"
    return digitos
