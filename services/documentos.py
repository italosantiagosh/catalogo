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
