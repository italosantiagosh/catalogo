from __future__ import annotations

import json
from unittest.mock import Mock, patch

import services.tiny as tiny


def _pedido_exemplo(**overrides):
    base = dict(
        codigo="ABC123",
        itens=[{"chave_preco": "16mm", "quantidade": 10, "descricao": "São José — Modelo 1", "valor_unitario": 5.0}],
        subtotal=50.0,
        frete_descricao="Correios PAC — R$ 10,00",
        frete_preco=10.0,
        total=60.0,
        cliente_nome="Maria Teste",
        cliente_tipo_pessoa="fisica",
        cliente_documento="12345678900",
        cliente_telefone="84999999999",
        cliente_email="maria@example.com",
        endereco_cep="59000000",
        endereco_destinatario_nome="",
        endereco_destinatario_tipo_pessoa="",
        endereco_destinatario_documento="",
        endereco_logradouro="Rua Teste",
        endereco_numero="100",
        endereco_complemento="",
        endereco_bairro="Centro",
        endereco_cidade="Natal",
        endereco_uf="RN",
        forma_pagamento="pix",
        transaction_nsu="tx-abc",
    )
    base.update(overrides)
    return base


def _resposta_ok(numero=1001, id_=555):
    resposta = Mock()
    resposta.raise_for_status = Mock()
    resposta.json.return_value = {
        "retorno": {
            "status_processamento": 3,
            "status": "OK",
            "registros": [{"registro": {"status": "OK", "id": id_, "numero": numero}}],
        }
    }
    return resposta


def test_sem_token_devolve_erro(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "")
    resultado = tiny.criar_pedido_tiny(_pedido_exemplo())
    assert "erro" in resultado


def test_monta_payload_com_cliente_itens_e_numero_pedido_ecommerce(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        resultado = tiny.criar_pedido_tiny(_pedido_exemplo())

    assert resultado == {"ok": True, "numero": 1001, "id": 555}

    corpo_enviado = post_mock.call_args.kwargs["data"]
    assert corpo_enviado["token"] == "segredo123"
    assert corpo_enviado["formato"] == "json"
    pedido_json = json.loads(corpo_enviado["pedido"])["pedido"]

    assert pedido_json["cliente"]["nome"] == "Maria Teste"
    assert pedido_json["cliente"]["tipo_pessoa"] == "F"
    assert pedido_json["cliente"]["cpf_cnpj"] == "12345678900"
    assert pedido_json["cliente"]["cep"] == "59000000"
    # codigo/descricao mandados pra Tiny sao os SKUs reais das variacoes
    # que a usuaria ja usa ha anos (ver conversa: o travessão especifico
    # por santo/modelo quebrava a NF-e) -- santo/modelo continuam so no
    # proprio "descricao" do item guardado no pedido do site (nao
    # mandado pra Tiny), aqui so confere o codigo.
    assert pedido_json["itens"][0]["item"]["descricao"] == "Medalha Personalizada - 1,6cm"
    assert pedido_json["itens"][0]["item"]["codigo"] == "LCEHXXXNP"
    assert pedido_json["itens"][0]["item"]["quantidade"] == "10"
    assert pedido_json["itens"][0]["item"]["valor_unitario"] == "5.00"
    assert pedido_json["numero_pedido_ecommerce"] == "ABC123"
    assert pedido_json["forma_pagamento"] == "pix"
    assert "Pedido site #ABC123" in pedido_json["obs"]
    assert "tx-abc" in pedido_json["obs"]


def test_item_sem_produto_do_catalogo_usa_codigo_agregado(monkeypatch):
    """Sem produtoId/modeloId (medalha personalizada com foto), usa o
    SKU real da variacao "Medalha Personalizada" que a usuaria ja usa
    ha anos na Tiny -- ver services/tiny.py:_CODIGO_MATERIAL_TINY."""
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(
            itens=[{"chave_preco": "16mm", "quantidade": 10, "descricao": "Personalizada", "valor_unitario": 5.0}]
        ))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["itens"][0]["item"]["codigo"] == "LCEHXXXNP"
    assert pedido_json["itens"][0]["item"]["descricao"] == "Medalha Personalizada - 1,6cm"


def test_item_sem_produto_do_catalogo_entremeio_prata_e_ouro_velho_viram_codigos_diferentes(monkeypatch):
    """Confirma que a cor do entremeio ainda diferencia o codigo/descricao
    (SKUs reais das variacoes "Entremeio Personalizado de 1 lado")."""
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    itens = [
        {"chave_preco": "entremeio", "quantidade": 5, "descricao": "Entremeio · Prata",
         "valor_unitario": 3.0, "cor": "prata"},
        {"chave_preco": "entremeio", "quantidade": 7, "descricao": "Entremeio · Ouro velho",
         "valor_unitario": 3.0, "cor": "ouro_velho"},
    ]
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(itens=itens))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["itens"][0]["item"]["codigo"] == "XQWBRR2FK"
    assert pedido_json["itens"][0]["item"]["descricao"] == "Entremeio Personalizado de 1 lado - Prata"
    assert pedido_json["itens"][1]["item"]["codigo"] == "KY5EZHCF5"
    assert pedido_json["itens"][1]["item"]["descricao"] == "Entremeio Personalizado de 1 lado - Ouro velho"


def test_item_do_catalogo_tambem_usa_codigo_agregado_por_material(monkeypatch):
    """Ver conversa: a nota fiscal quebrava ("A descrição do produto
    está em branco, incompleta ou contém caracteres inválidos" -- o
    travessão da descricao especifica por santo/modelo nao e´ valido
    pro XML da NF-e) e ficava enorme (uma linha por santo+modelo).
    Revertido pra codigo/descricao agregados por material SEMPRE,
    mesmo com produtoId/modeloId preenchidos (produto real do
    catalogo) -- santo/modelo continuam so no painel/pedido do
    cliente, nunca mandados pra Tiny."""
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    itens = [
        {"chave_preco": "16mm", "quantidade": 10, "descricao": "Anunciação — Modelo 1", "valor_unitario": 5.0,
         "produtoId": "anunciacao", "modeloId": "1"},
    ]
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(itens=itens))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["itens"][0]["item"]["codigo"] == "LCEHXXXNP"
    assert pedido_json["itens"][0]["item"]["descricao"] == "Medalha Personalizada - 1,6cm"


def test_item_do_catalogo_entremeio_e_chaveiro_tambem_usam_codigo_agregado(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    itens = [
        {"chave_preco": "entremeio", "quantidade": 5, "descricao": "Anunciação — Entremeio · Ouro velho",
         "valor_unitario": 3.0, "cor": "ouro_velho", "produtoId": "anunciacao", "modeloId": "1"},
        {"chave_preco": "chaveiro", "quantidade": 2, "descricao": "Anunciação — Chaveiro",
         "valor_unitario": 8.0, "produtoId": "anunciacao", "modeloId": "1"},
    ]
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(itens=itens))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["itens"][0]["item"]["codigo"] == "KY5EZHCF5"
    assert pedido_json["itens"][0]["item"]["descricao"] == "Entremeio Personalizado de 1 lado - Ouro velho"
    assert pedido_json["itens"][1]["item"]["codigo"] == "Chaveiro"
    assert pedido_json["itens"][1]["item"]["descricao"] == "Chaveiro Personalizado"


def test_medalha_2lados_usa_codigo_por_tamanho_e_cor(monkeypatch):
    """SKUs reais das variacoes "Medalha Personalizada de 2 lados"
    (Tamanho x Cor) mandados pela usuaria, ver services/tiny.py:
    _CODIGO_MATERIAL_TINY."""
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    itens = [
        {"chave_preco": "medalha_2lados", "quantidade": 20, "descricao": "Medalha 2 lados · Prata · 1,8 cm",
         "valor_unitario": 6.0, "cor": "prata", "tamanho": "18mm"},
        {"chave_preco": "medalha_2lados", "quantidade": 10, "descricao": "Medalha 2 lados · Prata · 1,4 cm",
         "valor_unitario": 6.0, "cor": "prata", "tamanho": "14mm"},
        {"chave_preco": "medalha_2lados", "quantidade": 5, "descricao": "Medalha 2 lados · Ouro velho · 1,8 cm",
         "valor_unitario": 6.0, "cor": "ouro_velho", "tamanho": "18mm"},
        {"chave_preco": "medalha_2lados", "quantidade": 5, "descricao": "Medalha 2 lados · Ouro velho · 1,4 cm",
         "valor_unitario": 6.0, "cor": "ouro_velho", "tamanho": "14mm"},
    ]
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(itens=itens))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    codigos = [i["item"]["codigo"] for i in pedido_json["itens"]]
    descricoes = [i["item"]["descricao"] for i in pedido_json["itens"]]
    assert codigos == ["2A6RZ54SH", "SLEK863TR", "8SSCLZ3UK", "8CDKFLKH2"]
    assert descricoes == [
        "Medalha Personalizada de 2 lados - 1,8cm - Prata",
        "Medalha Personalizada de 2 lados - 1,4cm - Prata",
        "Medalha Personalizada de 2 lados - 1,8cm - Ouro velho",
        "Medalha Personalizada de 2 lados - 1,4cm - Ouro velho",
    ]


def test_entremeio_2lados_usa_codigo_por_cor(monkeypatch):
    """SKUs reais das variacoes "Entremeio Personalizado de 2 lados"
    (so Cor, sem tamanho -- mesma base do entremeio de 1 lado)."""
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    itens = [
        {"chave_preco": "entremeio_2lados", "quantidade": 8, "descricao": "Entremeio 2 lados · Prata",
         "valor_unitario": 6.0, "cor": "prata"},
        {"chave_preco": "entremeio_2lados", "quantidade": 4, "descricao": "Entremeio 2 lados · Ouro velho",
         "valor_unitario": 6.0, "cor": "ouro_velho"},
    ]
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(itens=itens))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["itens"][0]["item"]["codigo"] == "62LWPVMNR"
    assert pedido_json["itens"][0]["item"]["descricao"] == "Entremeio Personalizado de 2 lados - Prata"
    assert pedido_json["itens"][1]["item"]["codigo"] == "5TQHLBKE2"
    assert pedido_json["itens"][1]["item"]["descricao"] == "Entremeio Personalizado de 2 lados - Ouro velho"


def test_sem_endereco_de_entrega_diferente_nao_manda_bloco(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo())
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert "endereco_entrega" not in pedido_json


def test_endereco_de_entrega_diferente_monta_bloco_endereco_entrega(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(
            endereco_destinatario_nome="Ana Coordenadora",
            endereco_destinatario_cep="59100000",
            endereco_destinatario_logradouro="Rua da Livraria",
            endereco_destinatario_numero="200",
            endereco_destinatario_complemento="Sala 2",
            endereco_destinatario_bairro="Cidade Alta",
            endereco_destinatario_cidade="Natal",
            endereco_destinatario_uf="RN",
        ))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["endereco_entrega"]["nome_destinatario"] == "Ana Coordenadora"
    assert pedido_json["endereco_entrega"]["endereco"] == "Rua da Livraria"
    assert pedido_json["endereco_entrega"]["cep"] == "59100000"


def test_endereco_de_entrega_diferente_manda_cpf_cnpj_do_destinatario(monkeypatch):
    """Ver conversa: usuario relatou que o CPF do destinatario so ia
    pras observacoes/nota, nunca pro campo estruturado de CPF do
    endereco de entrega na Tiny."""
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(
            endereco_destinatario_nome="Ana Coordenadora",
            endereco_destinatario_documento="98765432100",
            endereco_destinatario_cep="59100000",
            endereco_destinatario_logradouro="Rua da Livraria",
            endereco_destinatario_numero="200",
            endereco_destinatario_complemento="Sala 2",
            endereco_destinatario_bairro="Cidade Alta",
            endereco_destinatario_cidade="Natal",
            endereco_destinatario_uf="RN",
        ))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["endereco_entrega"]["cpf_cnpj"] == "98765432100"


def test_endereco_de_entrega_diferente_manda_telefone_do_destinatario_quando_preenchido(monkeypatch):
    """Ver conversa: campo opcional pra transportadora/Tiny conseguirem
    contato com quem recebe, quando diferente de quem fecha a compra."""
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(
            endereco_destinatario_nome="Ana Coordenadora",
            endereco_destinatario_documento="98765432100",
            endereco_destinatario_cep="59100000",
            endereco_destinatario_logradouro="Rua da Livraria",
            endereco_destinatario_numero="200",
            endereco_destinatario_complemento="Sala 2",
            endereco_destinatario_bairro="Cidade Alta",
            endereco_destinatario_cidade="Natal",
            endereco_destinatario_uf="RN",
            endereco_destinatario_telefone="84988887777",
        ))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["endereco_entrega"]["fone"] == "84988887777"


def test_endereco_de_entrega_diferente_sem_telefone_do_destinatario_nao_manda_fone(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(
            endereco_destinatario_nome="Ana Coordenadora",
            endereco_destinatario_documento="98765432100",
            endereco_destinatario_cep="59100000",
            endereco_destinatario_logradouro="Rua da Livraria",
            endereco_destinatario_numero="200",
            endereco_destinatario_complemento="Sala 2",
            endereco_destinatario_bairro="Cidade Alta",
            endereco_destinatario_cidade="Natal",
            endereco_destinatario_uf="RN",
        ))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert "fone" not in pedido_json["endereco_entrega"]


def test_cliente_manda_email_e_celular_pra_tiny(monkeypatch):
    """Ver conversa: usuario relatou que email e celular ficavam vazios
    no cadastro do cliente na Tiny -- "fone" ja´ e´ confirmado, "celular"
    e "email" replicam o mesmo telefone/e-mail do pedido."""
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(
            cliente_telefone="84999999999", cliente_email="maria@example.com"
        ))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["cliente"]["fone"] == "84999999999"
    assert pedido_json["cliente"]["celular"] == "84999999999"
    assert pedido_json["cliente"]["email"] == "maria@example.com"


def test_destinatario_diferente_entra_nas_observacoes(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(
            endereco_destinatario_nome="João Receptor", endereco_destinatario_documento="98765432100"
        ))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert "João Receptor" in pedido_json["obs"]
    assert "98765432100" in pedido_json["obs"]


def test_tipo_pessoa_juridica_mapeia_para_j(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(cliente_tipo_pessoa="juridica"))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["cliente"]["tipo_pessoa"] == "J"


def test_inscricao_estadual_vai_pro_campo_ie(monkeypatch):
    """Ver conversa: usuaria relatou que a Inscricao Estadual nao
    estava indo pra Tiny -- o campo nunca era mandado no corpo do
    pedido.incluir.php, so ficava guardado no banco do site."""
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(
            cliente_tipo_pessoa="juridica", cliente_inscricao_estadual="123.456.789",
        ))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["cliente"]["ie"] == "123.456.789"
    assert pedido_json["cliente"]["contribuinte"] == "1"


def test_ie_isento_manda_contribuinte_2_sem_campo_ie(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(
            cliente_tipo_pessoa="juridica", cliente_ie_isento=1, cliente_inscricao_estadual="",
        ))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["cliente"]["contribuinte"] == "2"
    assert "ie" not in pedido_json["cliente"]


def test_ie_nao_contribuinte_manda_contribuinte_9(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(
            cliente_tipo_pessoa="juridica", cliente_ie_nao_contribuinte=1,
            cliente_inscricao_estadual="123.456.789",
        ))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert pedido_json["cliente"]["ie"] == "123.456.789"
    assert pedido_json["cliente"]["contribuinte"] == "9"


def test_pessoa_fisica_nunca_manda_ie_ou_contribuinte(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(cliente_tipo_pessoa="fisica"))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert "ie" not in pedido_json["cliente"]
    assert "contribuinte" not in pedido_json["cliente"]


def test_juridica_sem_ie_preenchida_nao_manda_ie_nem_contribuinte(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(cliente_tipo_pessoa="juridica"))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert "ie" not in pedido_json["cliente"]
    assert "contribuinte" not in pedido_json["cliente"]


def test_forma_pagamento_desconhecida_nao_e_enviada(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", return_value=_resposta_ok()) as post_mock:
        tiny.criar_pedido_tiny(_pedido_exemplo(forma_pagamento="boleto_bancario_desconhecido"))
    pedido_json = json.loads(post_mock.call_args.kwargs["data"]["pedido"])["pedido"]
    assert "forma_pagamento" not in pedido_json


def test_resposta_com_erro_da_tiny(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    resposta = Mock()
    resposta.raise_for_status = Mock()
    resposta.json.return_value = {
        "retorno": {
            "status_processamento": 3,
            "status": "Erro",
            "codigo_erro": 20,
            "erros": [{"erro": "CPF inválido"}],
        }
    }
    with patch("services.tiny.requests.post", return_value=resposta):
        resultado = tiny.criar_pedido_tiny(_pedido_exemplo())
    assert resultado == {"erro": "CPF inválido"}


def test_resposta_ok_com_registros_como_objeto_nao_lista(monkeypatch):
    """A Tiny as vezes manda `retorno.registros` como um objeto unico
    (`{"registro": {...}}`) em vez de lista -- confirmado com pedido de
    teste real. Sem tratar isso, `registros[0]` quebrava com KeyError."""
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    resposta = Mock()
    resposta.raise_for_status = Mock()
    resposta.json.return_value = {
        "retorno": {
            "status_processamento": 3,
            "status": "OK",
            "registros": {"registro": {"status": "OK", "id": 858847926, "numero": "1113"}},
        }
    }
    with patch("services.tiny.requests.post", return_value=resposta):
        resultado = tiny.criar_pedido_tiny(_pedido_exemplo())
    assert resultado == {"ok": True, "numero": "1113", "id": 858847926}


def test_resposta_com_erro_e_registros_como_objeto_nao_lista(monkeypatch):
    """Mesmo formato do teste acima, mas pro caso de erro (ex: pedido
    duplicado) -- a mensagem de erro real da Tiny vem dentro de
    registros.registro.erros, nao em retorno.erros direto."""
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    resposta = Mock()
    resposta.raise_for_status = Mock()
    resposta.json.return_value = {
        "retorno": {
            "status_processamento": 2,
            "status": "Erro",
            "registros": {
                "registro": {
                    "sequencia": "1",
                    "status": "Erro",
                    "codigo_erro": "30",
                    "erros": [{"erro": "Registro em duplicidade – Pedido de Venda já cadastrado"}],
                }
            },
        }
    }
    with patch("services.tiny.requests.post", return_value=resposta):
        resultado = tiny.criar_pedido_tiny(_pedido_exemplo())
    assert resultado == {"erro": "Registro em duplicidade – Pedido de Venda já cadastrado"}


def test_erro_de_rede(monkeypatch):
    import requests

    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.post", side_effect=requests.RequestException("timeout")):
        resultado = tiny.criar_pedido_tiny(_pedido_exemplo())
    assert "erro" in resultado


def test_buscar_contatos_sem_token_devolve_erro(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "")
    resultado = tiny.buscar_contatos_tiny("livraria")
    assert "erro" in resultado


def test_buscar_contatos_termo_vazio_devolve_lista_vazia(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    resultado = tiny.buscar_contatos_tiny("   ")
    assert resultado == {"ok": True, "contatos": []}


def test_buscar_contatos_monta_lista_a_partir_da_resposta(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    resposta = Mock()
    resposta.raise_for_status = Mock()
    resposta.json.return_value = {
        "retorno": {
            "status_processamento": 3,
            "status": "OK",
            "contatos": [
                {
                    "contato": {
                        "nome": "Livraria Shalom Natal",
                        "tipo_pessoa": "J",
                        "cpf_cnpj": "12345678000199",
                        "fone": "8433334444",
                        "email": "contato@livraria.com",
                        "cep": "59000000",
                        "endereco": "Av. Principal",
                        "numero": "500",
                        "complemento": "Loja 2",
                        "bairro": "Centro",
                        "cidade": "Natal",
                        "uf": "RN",
                    }
                }
            ],
        }
    }
    with patch("services.tiny.requests.get", return_value=resposta) as get_mock:
        resultado = tiny.buscar_contatos_tiny("livraria shalom")

    assert get_mock.call_args.kwargs["params"]["pesquisa"] == "livraria shalom"
    assert resultado["ok"] is True
    assert len(resultado["contatos"]) == 1
    contato = resultado["contatos"][0]
    assert contato["nome"] == "Livraria Shalom Natal"
    assert contato["tipo_pessoa"] == "juridica"
    assert contato["documento"] == "12345678000199"
    assert contato["logradouro"] == "Av. Principal"
    assert contato["cidade"] == "Natal"


def test_buscar_contatos_nenhum_encontrado_devolve_lista_vazia(monkeypatch):
    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    resposta = Mock()
    resposta.raise_for_status = Mock()
    resposta.json.return_value = {
        "retorno": {"status_processamento": 3, "status": "Erro", "codigo_erro": 20, "erros": [{"erro": "Nenhum registro encontrado"}]}
    }
    with patch("services.tiny.requests.get", return_value=resposta):
        resultado = tiny.buscar_contatos_tiny("ninguem")
    assert resultado == {"ok": True, "contatos": []}


def test_buscar_contatos_erro_de_rede(monkeypatch):
    import requests

    monkeypatch.setattr(tiny, "TINY_API_TOKEN", "segredo123")
    with patch("services.tiny.requests.get", side_effect=requests.RequestException("timeout")):
        resultado = tiny.buscar_contatos_tiny("livraria")
    assert "erro" in resultado
