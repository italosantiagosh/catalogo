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

# Pix (recebimento, ver services/pix.py). A chave Pix NAO e uma
# credencial no sentido de senha/token -- e feita pra ser publicada e
# escaneada por qualquer cliente (mesmo principio de um QR impresso
# numa maquininha de cartao): so permite que mandem dinheiro pra
# conta, nao da acesso a nada. Por isso fica direto no codigo, como o
# CEP_ORIGEM -- variavel de ambiente so se quiser trocar sem redeploy.
# Nome e cidade aparecem pro cliente no app do banco ao escanear;
# CIDADE foi assumida como Natal/RN a partir do CEP_ORIGEM (faixa
# 590xx-599xx) -- confirme/corrija se estiver errado.
PIX_CHAVE = os.environ.get("PIX_CHAVE", "39390354000125")
PIX_NOME_RECEBEDOR = os.environ.get("PIX_NOME_RECEBEDOR", "NOVE DE JULHO")
PIX_CIDADE = os.environ.get("PIX_CIDADE", "NATAL")
