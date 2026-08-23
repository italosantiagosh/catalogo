"""
Configuracao central do catalogo -- valores que nao devem ficar
espalhados pelo codigo.
"""

import os

# Numero de WhatsApp para onde os pedidos sao enviados (ETAPA 9). So a
# constante por enquanto -- os botoes de finalizar pedido/tirar duvida
# ainda nao existem.
WHATSAPP_NUMBER = "5584981276650"

# Frete (calculadora do carrinho, ver services/frete.py). O token da
# Frenet e uma credencial -- NUNCA gravar o valor aqui nem em nenhum
# outro arquivo do repositorio; configurar como variavel de ambiente
# FRENET_TOKEN no servidor (Render: Settings > Environment) e, para
# rodar local, exportar no shell antes de `flask run`.
FRENET_TOKEN = os.environ.get("FRENET_TOKEN", "")

# CEP de onde os pedidos sao despachados -- usado como origem em toda
# cotacao de frete. Nao e segredo, pode ficar no codigo -- variavel de
# ambiente so se precisar sobrescrever sem redeploy.
CEP_ORIGEM = os.environ.get("CEP_ORIGEM", "59088-040")

# Token de acesso pessoal do Melhor Envio -- usado so pra cotar Azul
# Express com a tarifa contratada pelo usuario ali (nao pra gerar
# etiqueta/frete de verdade). Mesma regra do FRENET_TOKEN: NUNCA
# gravar o valor aqui, so variavel de ambiente MELHOR_ENVIO_TOKEN no
# servidor. Esse token em especial tem escopos bem mais amplos que o
# necessario (inclui shipping-generate, products-write, users-write
# etc.) -- o codigo aqui so chama o endpoint de cotacao
# (shipping-calculate), mas se puder gerar um token so com esse
# escopo no painel do Melhor Envio, e mais seguro trocar por um mais
# restrito.
MELHOR_ENVIO_TOKEN = os.environ.get("MELHOR_ENVIO_TOKEN", "")
