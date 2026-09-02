from __future__ import annotations

from unittest.mock import patch

import pytest

import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _corpo_valido(**overrides):
    base = dict(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"}],
        frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0},
        cliente={"nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "11144477735",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def test_criar_pedido_frete_manipulado_e_bloqueado(client):
    corpo = _corpo_valido(frete={"texto": "Correios PAC — R$ 25,50", "preco": 0.01})
    with patch("app.calcular_frete", return_value={
        "frete_gratis": False,
        "opcoes": [{"transportadora": "Correios", "servico": "PAC", "preco": 25.5, "prazo_dias": 6}],
    }):
        resposta = client.post("/api/pedido/criar", json=corpo)
    assert resposta.status_code == 400
    assert "frete" in resposta.get_json()["erro"].lower()


def test_criar_pedido_frete_real_passa(client):
    with patch("app.calcular_frete", return_value={
        "frete_gratis": False,
        "opcoes": [{"transportadora": "Correios", "servico": "PAC", "preco": 25.5, "prazo_dias": 6}],
    }), patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        corpo = _corpo_valido(frete={"texto": "Correios PAC — R$ 25,50", "preco": 25.5})
        resposta = client.post("/api/pedido/criar", json=corpo)
    assert resposta.status_code == 200


def test_criar_pedido_com_desconto_de_frete_atacado_passa(client):
    """Ver conversa: 20 medalhas ja e´ atacado -> desconto no frete.
    O preco final (ja com o desconto abatido) tem que ser aceito na
    reconferencia do checkout, nao barrado como "frete mudou"."""
    corpo = _corpo_valido(
        itens=[{"chave_preco": "16mm", "quantidade": 20, "produtoNome": "São José", "modeloNome": "Modelo 1"}],
        frete={"texto": "Correios PAC — R$ 2,80", "preco": 2.80},
    )
    with patch("app.calcular_frete", return_value={
        "frete_gratis": False,
        "desconto_atacado_reais": 7.20,
        "opcoes": [{
            "transportadora": "Correios", "servico": "PAC", "prazo_dias": 6,
            "preco_original": 10.0, "preco_final": 2.80, "gratis": False,
        }],
    }) as mock_frete, patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        resposta = client.post("/api/pedido/criar", json=corpo)
    assert resposta.status_code == 200
    # o desconto calculado (calculo["desconto_frete_atacado"]) precisa
    # ter sido passado adiante pra calcular_frete
    assert mock_frete.call_args.args[-1] == 7.20


def test_criar_pedido_frete_indisponivel_nao_bloqueia_venda(client):
    """Fail-open: se a cotacao de frete falhar (rede fora, token nao
    configurado) na hora do checkout, o pedido segue confiando no
    preco que o navegador mandou -- um problema temporario nunca deve
    impedir uma venda de verdade (ver conversa)."""
    with patch("app.calcular_frete", return_value={"frete_gratis": False, "opcoes": [], "erro": "fora do ar"}), \
         patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        resposta = client.post("/api/pedido/criar", json=_corpo_valido())
    assert resposta.status_code == 200


def test_criar_pedido_retirada_ignora_preco_de_frete_mandado(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        corpo = _corpo_valido(frete={"texto": "Retirada no local", "preco": 999.0})
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["frete_preco"] == 0.0


def test_criar_pedido_com_cpf_invalido_400(client):
    corpo = _corpo_valido(cliente={
        "nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "11111111111",
        "telefone": "84999999999", "email": "maria@example.com",
    })
    resposta = client.post("/api/pedido/criar", json=corpo)
    assert resposta.status_code == 400
    assert "CPF" in resposta.get_json()["erro"]


def test_criar_pedido_com_cnpj_invalido_400(client):
    corpo = _corpo_valido(cliente={
        "nome": "Loja Teste", "tipo_pessoa": "juridica", "documento": "11222333000182",
        "telefone": "84999999999", "email": "loja@example.com",
    })
    resposta = client.post("/api/pedido/criar", json=corpo)
    assert resposta.status_code == 400
    assert "CNPJ" in resposta.get_json()["erro"]


def test_criar_pedido_com_cnpj_valido_e_ie_isento(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        corpo = _corpo_valido(cliente={
            "nome": "Loja Teste", "tipo_pessoa": "juridica", "documento": "11222333000181",
            "telefone": "84999999999", "email": "loja@example.com",
            "ie_isento": True, "inscricao_estadual": "123456",  # deve ser ignorado, isento nao guarda numero
        })
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["cliente_ie_isento"] == 1
    assert pedido["cliente_inscricao_estadual"] == ""


def test_criar_pedido_com_cnpj_valido_e_inscricao_estadual(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        corpo = _corpo_valido(cliente={
            "nome": "Loja Teste", "tipo_pessoa": "juridica", "documento": "11222333000181",
            "telefone": "84999999999", "email": "loja@example.com",
            "inscricao_estadual": "123.456.789", "ie_nao_contribuinte": True,
        })
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["cliente_inscricao_estadual"] == "123.456.789"
    assert pedido["cliente_ie_isento"] == 0
    assert pedido["cliente_ie_nao_contribuinte"] == 1


def test_criar_pedido_com_destinatario_cpf_invalido_400(client):
    corpo = _corpo_valido(endereco={
        "cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
        "bairro": "Centro", "cidade": "Natal", "uf": "RN",
        "destinatario_nome": "Joao", "destinatario_tipo_pessoa": "fisica", "destinatario_documento": "11111111111",
        "destinatario_cep": "59000000", "destinatario_logradouro": "Rua X", "destinatario_numero": "1",
        "destinatario_bairro": "Centro", "destinatario_cidade": "Natal", "destinatario_uf": "RN",
    })
    resposta = client.post("/api/pedido/criar", json=corpo)
    assert resposta.status_code == 400
    assert "CPF" in resposta.get_json()["erro"]


def test_admin_detalhe_mostra_documento_e_ie(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    corpo = _corpo_valido(cliente={
        "nome": "Loja Teste", "tipo_pessoa": "juridica", "documento": "11222333000181",
        "telefone": "84999999999", "email": "loja@example.com",
        "inscricao_estadual": "123456", "ie_nao_contribuinte": True,
    })
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    detalhe = client.get(f"/admin/pedidos/{criado['token']}", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "CNPJ: 11222333000181" in detalhe
    assert "IE: 123456" in detalhe
    assert "não contribuinte de ICMS" in detalhe


def test_criar_pedido_com_link_mockado(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}) as mock_link:
        resposta = client.post("/api/pedido/criar", json=_corpo_valido())
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["url"] == "https://checkout.infinitepay.io/abc"
    assert len(dados["token"]) > 20
    assert len(dados["codigo"]) == 6

    corpo_infinitepay = mock_link.call_args.kwargs
    assert corpo_infinitepay["order_nsu"] == dados["token"]
    # subtotal (10x R$5,00 = R$50) + frete R$10 = 1 item de produto + 1 de frete
    descricoes = [item["description"] for item in corpo_infinitepay["itens_pagamento"]]
    assert "Correios PAC — R$ 10,00" in descricoes
    assert any("São José" in d for d in descricoes)
    assert corpo_infinitepay["redirect_url"].endswith(f"/pedido/{dados['token']}?obrigado=1")


def test_item_medalha_guarda_tamanho_na_descricao_e_detalhe(client):
    corpo = _corpo_valido(itens=[{
        "chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1",
        "formato": "medalha", "tamanho": "16mm", "imagem": "/static/img/produtos/sao-jose-1.jpg",
    }])
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    pedido = pedidos.obter_pedido(criado["token"])
    item = pedido["itens"][0]
    assert item["detalhe"] == "Medalha · 1,6 cm"
    assert "1,6 cm" in item["descricao"]
    assert item["imagem"] == "/static/img/produtos/sao-jose-1.jpg"


def test_item_personalizada_guarda_imagem_de_recorte_1x1(client, monkeypatch):
    """O recorte 1:1 (sem a moldura) precisa sobreviver no pedido pra
    a producao baixar no painel, sem depender do cliente reenviar a
    foto pelo WhatsApp (ver conversa)."""
    _preparar_admin_env(monkeypatch)
    corpo = _corpo_valido(itens=[{
        "chave_preco": "16mm", "quantidade": 10, "produtoNome": "Personalizada",
        "formato": "medalha", "tamanho": "16mm",
        "imagem": "data:image/png;base64,AAAA", "imagemRecorte": "data:image/png;base64,BBBB",
    }])
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    pedido = pedidos.obter_pedido(criado["token"])
    item = pedido["itens"][0]
    assert item["imagemRecorte"] == "data:image/png;base64,BBBB"

    detalhe = client.get(f"/admin/pedidos/{criado['token']}", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "data:image/png;base64,BBBB" in detalhe
    assert "Baixar imagem 1:1" in detalhe


def test_item_duas_faces_guarda_as_duas_fotos_separadas(client, monkeypatch):
    """medalha_2lados/entremeio_2lados mandam lado1/lado2 em vez de
    imagem/imagemRecorte direto no item (ver static/js/personalizada.js)
    -- os dois precisam sobreviver no pedido, cada um na sua chave, pra
    producao/admin verem as duas fotos (ver conversa)."""
    _preparar_admin_env(monkeypatch)
    corpo = _corpo_valido(itens=[{
        "chave_preco": "medalha_2lados", "quantidade": 20, "produtoNome": "Personalizada",
        "formato": "medalha_2lados", "cor": "prata",
        "duasFaces": True,
        "lado1": {"origem": "upload", "imagem": "data:image/png;base64,LADO1PREVIA", "imagemRecorte": "data:image/png;base64,LADO1RECORTE"},
        "lado2": {"origem": "sem_foto", "imagem": "/static/img/sem-foto.svg"},
    }], frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0})
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    pedido = pedidos.obter_pedido(criado["token"])
    item = pedido["itens"][0]
    assert item["duasFaces"] is True
    assert item["imagemLado1"] == "data:image/png;base64,LADO1PREVIA"
    assert item["imagemRecorteLado1"] == "data:image/png;base64,LADO1RECORTE"
    assert item["imagemLado2"] == "/static/img/sem-foto.svg"
    assert item["imagemRecorteLado2"] == ""
    # fallback pra qualquer lugar que so saiba mostrar "imagem" (unica)
    assert item["imagem"] == "data:image/png;base64,LADO1PREVIA"
    assert item["detalhe"] == "Medalha 2 lados · Prata"

    detalhe = client.get(f"/admin/pedidos/{criado['token']}", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "Baixar lado 1 (imagem 1:1)" in detalhe
    # lado 2 nao tem imagemRecorte (foi "enviar depois") -- nao deve
    # aparecer link de download quebrado pra ele
    assert "Baixar lado 2 (imagem 1:1)" not in detalhe

    pagina_cliente = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "data:image/png;base64,LADO1PREVIA" in pagina_cliente
    assert "sem-foto.svg" in pagina_cliente


def _preparar_admin_env(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")


def test_item_entremeio_guarda_cor_na_descricao_e_detalhe(client):
    corpo = _corpo_valido(itens=[{
        "chave_preco": "entremeio", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1",
        "formato": "entremeio", "cor": "ouro_velho",
    }])
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    pedido = pedidos.obter_pedido(criado["token"])
    item = pedido["itens"][0]
    assert item["detalhe"] == "Entremeio · Ouro velho"
    assert "Ouro velho" in item["descricao"]
    assert item["cor"] == "ouro_velho"


def test_item_chaveiro_detalhe_simples(client):
    corpo = _corpo_valido(itens=[{
        "chave_preco": "chaveiro", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1",
        "formato": "chaveiro",
    }])
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["itens"][0]["detalhe"] == "Chaveiro"


def test_admin_csv_exige_autenticacao(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    resposta = client.get(f"/admin/pedidos/{criado['token']}/csv")
    assert resposta.status_code == 401


def test_admin_csv_conteudo(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    corpo = _corpo_valido(itens=[{
        "chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1",
        "formato": "medalha", "tamanho": "16mm",
    }])
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    resposta = client.get(f"/admin/pedidos/{criado['token']}/csv", auth=("admin", "segredo123"))
    assert resposta.status_code == 200
    assert resposta.mimetype == "text/csv"
    corpo_csv = resposta.get_data().decode("utf-8-sig")
    assert "Produto;Modelo;Variação;Quantidade" in corpo_csv
    # Ver conversa: "Modelo 1" vira so "1" e o tamanho da medalha vira
    # so "16" (em vez do texto por extenso "Medalha · 1,6 cm"), pra
    # bater com como o usuario le a planilha de producao.
    assert "São José;1;16;10" in corpo_csv


def test_admin_csv_chaveiro_e_entremeio(client, monkeypatch):
    """Chaveiro vira "(chaveiro)" no CSV; entremeio mantem o detalhe por
    extenso (unico jeito de a producao ver a cor -- ver conversa)."""
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    corpo = _corpo_valido(itens=[
        {
            "chave_preco": "chaveiro", "quantidade": 5, "produtoNome": "São José", "modeloNome": "Modelo 2",
            "formato": "chaveiro",
        },
        {
            "chave_preco": "entremeio", "quantidade": 8, "produtoNome": "São José", "modeloNome": "Modelo 3",
            "formato": "entremeio", "cor": "ouro_velho",
        },
    ])
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    resposta = client.get(f"/admin/pedidos/{criado['token']}/csv", auth=("admin", "segredo123"))
    corpo_csv = resposta.get_data().decode("utf-8-sig")
    assert "São José;2;(chaveiro);5" in corpo_csv
    assert "São José;3;Entremeio · Ouro velho;8" in corpo_csv


def test_criar_pedido_envia_email_com_link_uma_vez(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}), \
         patch("app.enviar_link_pagamento", return_value={"ok": True}) as mock_email:
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    assert mock_email.call_count == 1
    url_pagamento_enviada = mock_email.call_args.args[1]
    assert url_pagamento_enviada == "https://checkout.infinitepay.io/abc"

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_pedido_criado_enviado"] == 1


def test_criar_pedido_com_erro_no_email_nao_impede_criacao(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}), \
         patch("app.enviar_link_pagamento", return_value={"erro": "falha no envio"}):
        resposta = client.post("/api/pedido/criar", json=_corpo_valido())
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados["url"] == "https://checkout.infinitepay.io/abc"

    pedido = pedidos.obter_pedido(dados["token"])
    assert pedido["email_pedido_criado_erro"] == "falha no envio"


def test_novo_link_gera_outro_link_pro_pedido_pendente(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/primeiro"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/segundo"}) as mock_link:
        resposta = client.post(f"/api/pedido/{criado['token']}/novo-link")
    assert resposta.status_code == 200
    assert resposta.get_json()["url"] == "https://checkout.infinitepay.io/segundo"
    assert mock_link.call_args.kwargs["order_nsu"] == criado["token"]


def test_novo_link_pedido_inexistente_404(client):
    resposta = client.post("/api/pedido/token-que-nao-existe/novo-link")
    assert resposta.status_code == 404


def test_novo_link_pedido_ja_pago_400(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    with patch("app.criar_pedido_tiny", return_value={"erro": "não configurado"}), \
         patch("app.enviar_confirmacao_pedido", return_value={"erro": "não configurado"}):
        client.post(
            "/webhook/infinitepay",
            json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
        )

    resposta = client.post(f"/api/pedido/{criado['token']}/novo-link")
    assert resposta.status_code == 400


def test_criar_pedido_com_destinatario_diferente(client):
    corpo = _corpo_valido(endereco={
        "cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
        "bairro": "Centro", "cidade": "Natal", "uf": "RN",
        "destinatario_nome": "Ana Coordenadora", "destinatario_tipo_pessoa": "fisica",
        "destinatario_documento": "98765432100",
    })
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()
    assert criado.get("token")

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["endereco_destinatario_nome"] == "Ana Coordenadora"
    assert pedido["endereco_destinatario_tipo_pessoa"] == "fisica"
    assert pedido["endereco_destinatario_documento"] == "98765432100"

    pagina = client.get(f"/pedido/{criado['token']}")
    assert "Ana Coordenadora" in pagina.get_data(as_text=True)


def test_criar_pedido_sem_destinatario_fica_vazio(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["endereco_destinatario_nome"] == ""


def test_criar_pedido_com_endereco_de_entrega_diferente(client):
    """Destinatario com endereco fisicamente diferente do principal --
    nao so outro nome na mesma casa (ver conversa: coordenadora recebe
    na casa dela, nota fiscal no nome/endereco da paroquia)."""
    corpo = _corpo_valido(endereco={
        "cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
        "bairro": "Centro", "cidade": "Natal", "uf": "RN",
        "destinatario_nome": "Ana Coordenadora", "destinatario_tipo_pessoa": "fisica",
        "destinatario_documento": "98765432100",
        "destinatario_cep": "59100000", "destinatario_logradouro": "Rua da Livraria",
        "destinatario_numero": "200", "destinatario_complemento": "Sala 2",
        "destinatario_bairro": "Cidade Alta", "destinatario_cidade": "Natal", "destinatario_uf": "RN",
    })
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()
    assert criado.get("token")

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["endereco_destinatario_cep"] == "59100000"
    assert pedido["endereco_destinatario_logradouro"] == "Rua da Livraria"
    assert pedido["endereco_destinatario_numero"] == "200"
    assert pedido["endereco_destinatario_complemento"] == "Sala 2"
    assert pedido["endereco_destinatario_bairro"] == "Cidade Alta"
    # endereco principal continua guardado, sem ser sobrescrito
    assert pedido["endereco_logradouro"] == "Rua Teste"

    pagina = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "Rua da Livraria" in pagina
    assert "Rua Teste" not in pagina  # a pagina mostra o endereco de entrega, nao o principal, quando os dois existem


def test_criar_pedido_endereco_de_entrega_incompleto_400(client):
    """Endereco de entrega e´ tudo ou nada -- preencher so uma parte
    (ex: so o CEP) nunca vira um pedido com etiqueta incompleta."""
    corpo = _corpo_valido(endereco={
        "cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
        "bairro": "Centro", "cidade": "Natal", "uf": "RN",
        "destinatario_nome": "Ana Coordenadora", "destinatario_tipo_pessoa": "fisica",
        "destinatario_documento": "98765432100",
        "destinatario_cep": "59100000",  # so o CEP, sem o resto
    })
    resposta = client.post("/api/pedido/criar", json=corpo)
    assert resposta.status_code == 400


def test_criar_pedido_com_telefone_do_destinatario(client):
    """Telefone de quem recebe (ver conversa) -- opcional, so pra
    transportadora/Tiny conseguirem contato se precisar."""
    corpo = _corpo_valido(endereco={
        "cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
        "bairro": "Centro", "cidade": "Natal", "uf": "RN",
        "destinatario_nome": "Ana Coordenadora", "destinatario_tipo_pessoa": "fisica",
        "destinatario_documento": "98765432100", "destinatario_telefone": "84988887777",
    })
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()
    assert criado.get("token")
    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["endereco_destinatario_telefone"] == "84988887777"


def test_criar_pedido_sem_telefone_do_destinatario_fica_vazio(client):
    corpo = _corpo_valido(endereco={
        "cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
        "bairro": "Centro", "cidade": "Natal", "uf": "RN",
        "destinatario_nome": "Ana Coordenadora", "destinatario_tipo_pessoa": "fisica",
        "destinatario_documento": "98765432100",
    })
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()
    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["endereco_destinatario_telefone"] == ""


def test_criar_pedido_telefone_do_destinatario_invalido_400(client):
    corpo = _corpo_valido(endereco={
        "cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
        "bairro": "Centro", "cidade": "Natal", "uf": "RN",
        "destinatario_nome": "Ana Coordenadora", "destinatario_tipo_pessoa": "fisica",
        "destinatario_documento": "98765432100", "destinatario_telefone": "20999999999",  # DDD 20 nunca existiu
    })
    resposta = client.post("/api/pedido/criar", json=corpo)
    assert resposta.status_code == 400


def test_criar_pedido_carrinho_vazio_400(client):
    resposta = client.post("/api/pedido/criar", json=_corpo_valido(itens=[]))
    assert resposta.status_code == 400


def test_criar_pedido_abaixo_do_minimo_400(client):
    resposta = client.post("/api/pedido/criar", json=_corpo_valido(
        itens=[{"chave_preco": "16mm", "quantidade": 1, "produtoNome": "São José"}]
    ))
    assert resposta.status_code == 400


def test_criar_pedido_sem_frete_400(client):
    resposta = client.post("/api/pedido/criar", json=_corpo_valido(frete={}))
    assert resposta.status_code == 400


def test_criar_pedido_sem_cliente_400(client):
    resposta = client.post("/api/pedido/criar", json=_corpo_valido(cliente={"nome": "Maria"}))
    assert resposta.status_code == 400


def test_criar_pedido_telefone_invalido_400(client):
    """Ver conversa: usuario relatou problema com telefone invalido no
    site antigo -- servidor confere formato (DDD real + 9 obrigatorio
    no celular), nunca confia so no navegador."""
    corpo = _corpo_valido(cliente={
        "nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": "11144477735",
        "telefone": "20999999999", "email": "maria@example.com",  # DDD 20 nunca existiu
    })
    resposta = client.post("/api/pedido/criar", json=corpo)
    assert resposta.status_code == 400
    assert "Telefone" in resposta.get_json()["erro"]


def test_criar_pedido_sem_endereco_400(client):
    resposta = client.post("/api/pedido/criar", json=_corpo_valido(endereco={"cep": "59000000"}))
    assert resposta.status_code == 400


def test_criar_pedido_whatsapp_entra_como_lead_sem_link_de_pagamento(client):
    """Ver conversa: pedido fechado pelo WhatsApp deve aparecer no painel
    admin (status "whatsapp"), sem exigir cliente/endereco (o WhatsApp
    nunca coletou isso) e sem gerar link de pagamento nenhum."""
    resposta = client.post("/api/pedido/criar-whatsapp", json={
        "itens": [{"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"}],
        "frete": {},
        "cep_informado": "59000-000",
    })
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert len(dados["codigo"]) == 6

    pedidos_whatsapp = pedidos.listar_pedidos(status="whatsapp")
    assert len(pedidos_whatsapp) == 1
    pedido = pedidos_whatsapp[0]
    assert pedido["codigo"] == dados["codigo"]
    assert pedido["cliente_nome"] == ""
    assert "59000-000" in pedido["frete_descricao"]


def test_criar_pedido_whatsapp_carrinho_vazio_400(client):
    resposta = client.post("/api/pedido/criar-whatsapp", json={"itens": []})
    assert resposta.status_code == 400


def test_criar_pedido_whatsapp_notifica_push_sem_falar_em_venda(client):
    """Pedido via WhatsApp ainda nao e´ venda confirmada (so um lead) --
    a notificacao avisa que o pedido foi EMITIDO, nao que foi vendido
    (ver conversa)."""
    with patch("app.enviar_notificacao_push") as push_mock:
        client.post("/api/pedido/criar-whatsapp", json={
            "itens": [{"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"}],
            "frete": {},
        })
    push_mock.assert_called_once()
    kwargs = push_mock.call_args.kwargs
    assert kwargs["titulo"] == "🎉 Você tem um pedido via WhatsApp"
    assert "icone-whatsapp.png" in kwargs["icone"]


def test_criar_pedido_erro_da_infinitepay_502(client):
    with patch("app.criar_link_pagamento", return_value={"erro": "falhou"}):
        resposta = client.post("/api/pedido/criar", json=_corpo_valido())
    assert resposta.status_code == 502


def test_pagina_de_pedido_mostra_status_pendente(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    pagina = client.get(f"/pedido/{criado['token']}")
    assert pagina.status_code == 200
    corpo = pagina.get_data(as_text=True)
    assert criado["codigo"] in corpo
    assert "Aguardando confirmação" in corpo


def test_pagina_de_pedido_inexistente_404(client):
    resposta = client.get("/pedido/token-que-nao-existe")
    assert resposta.status_code == 404


def test_webhook_confirma_pagamento_e_pedido_passa_a_pago(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    resposta_webhook = client.post(
        "/webhook/infinitepay",
        json={
            "order_nsu": criado["token"],
            "amount": 6000,
            "paid_amount": 6000,  # R$50 (produtos) + R$10 (frete) = R$60 -> 6000 centavos
            "capture_method": "pix",
            "installments": None,
            "transaction_nsu": "tx-abc",
        },
    )
    assert resposta_webhook.status_code == 200

    pagina = client.get(f"/pedido/{criado['token']}")
    corpo = pagina.get_data(as_text=True)
    assert "Pagamento confirmado" in corpo


def test_obrigado_aparece_so_com_query_param_e_pedido_pago(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix", "transaction_nsu": "tx-abc"},
    )

    com_param = client.get(f"/pedido/{criado['token']}?obrigado=1").get_data(as_text=True)
    assert "Obrigado pela sua compra!" in com_param

    sem_param = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "Obrigado pela sua compra!" not in sem_param


def test_obrigado_nao_aparece_se_pedido_nao_esta_pago(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    corpo = client.get(f"/pedido/{criado['token']}?obrigado=1").get_data(as_text=True)
    assert "Obrigado pela sua compra!" not in corpo


def test_webhook_confirma_pagamento_dispara_notificacao_de_venda_uma_vez(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    corpo_webhook = {
        "order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix", "transaction_nsu": "tx-abc",
    }
    with patch("app.enviar_notificacao_venda", return_value={"ok": True}) as mock_notificacao:
        client.post("/webhook/infinitepay", json=corpo_webhook)
        # webhook repetido nao deve notificar de novo
        client.post("/webhook/infinitepay", json=corpo_webhook)

    assert mock_notificacao.call_count == 1
    assert mock_notificacao.call_args.args[0]["codigo"] == criado["codigo"]


def test_webhook_valor_insuficiente_nao_confirma(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    resposta_webhook = client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 100, "capture_method": "pix"},
    )
    assert resposta_webhook.status_code == 200

    pagina = client.get(f"/pedido/{criado['token']}")
    assert "Aguardando confirmação" in pagina.get_data(as_text=True)


def test_webhook_pedido_desconhecido_404(client):
    resposta = client.post("/webhook/infinitepay", json={"order_nsu": "nao-existe", "paid_amount": 100})
    assert resposta.status_code == 404


def test_webhook_tiny_captura_registra_e_devolve_ok(client, capsys):
    """Endpoint temporario (ver conversa) so pra ver no log o formato
    real que a Tiny manda -- nao processa nada, so precisa aceitar
    qualquer corpo e responder 200 (senao a Tiny pode desativar o
    webhook por falha repetida)."""
    resposta = client.post(
        "/webhook/tiny-captura/situacao-pedido", data='{"algumCampo": "algumValor"}',
        content_type="application/json",
    )
    assert resposta.status_code == 200
    saida = capsys.readouterr().out
    assert "[TINY WEBHOOK CAPTURA]" in saida
    assert "tipo=situacao-pedido" in saida
    assert "algumValor" in saida


def test_webhook_confirmado_sincroniza_com_a_tiny_uma_vez(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    corpo_webhook = {
        "order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix", "transaction_nsu": "tx-abc",
    }
    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 42, "id": 7}) as mock_tiny:
        client.post("/webhook/infinitepay", json=corpo_webhook)
        # webhook repetido (comum em integracoes de pagamento) nao deve
        # sincronizar com a Tiny de novo
        client.post("/webhook/infinitepay", json=corpo_webhook)

    assert mock_tiny.call_count == 1

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["tiny_sincronizado"] == 1
    assert pedido["tiny_numero_pedido"] == "42"


def test_webhook_falha_na_tiny_nao_impede_confirmacao_do_pagamento(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.criar_pedido_tiny", return_value={"erro": "CPF inválido"}):
        resposta_webhook = client.post(
            "/webhook/infinitepay",
            json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
        )
    assert resposta_webhook.status_code == 200

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "pago"
    assert pedido["tiny_sincronizado"] == 1
    assert pedido["tiny_erro"] == "CPF inválido"


def test_webhook_confirmado_envia_email_uma_vez(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    corpo_webhook = {"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"}
    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 1}), \
         patch("app.enviar_confirmacao_pedido", return_value={"ok": True}) as mock_email:
        client.post("/webhook/infinitepay", json=corpo_webhook)
        client.post("/webhook/infinitepay", json=corpo_webhook)

    assert mock_email.call_count == 1
    url_enviada = mock_email.call_args.args[1]
    assert criado["token"] in url_enviada

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["email_enviado"] == 1


def test_webhook_falha_no_email_nao_impede_confirmacao_do_pagamento(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 1}), \
         patch("app.enviar_confirmacao_pedido", return_value={"erro": "falha no envio"}):
        resposta_webhook = client.post(
            "/webhook/infinitepay",
            json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
        )
    assert resposta_webhook.status_code == 200

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "pago"
    assert pedido["email_enviado"] == 1
    assert pedido["email_erro"] == "falha no envio"


def test_webhook_confirmado_registra_falha_na_notificacao_de_venda(client):
    """Ate isso ser corrigido (ver conversa: usuario recebeu push mas
    nao e-mail, e nao havia como saber o motivo), uma falha aqui era
    engolida em silencio -- agora fica gravada no pedido, igual ja
    acontece com o e-mail de confirmacao pro cliente."""
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 1}), \
         patch("app.enviar_confirmacao_pedido", return_value={"ok": True}), \
         patch("app.enviar_notificacao_venda", return_value={"erro": "EMAIL_NOTIFICACAO_VENDA inválido"}):
        client.post(
            "/webhook/infinitepay",
            json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
        )

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["status"] == "pago"
    assert pedido["notificacao_venda_enviada"] == 1
    assert pedido["notificacao_venda_erro"] == "EMAIL_NOTIFICACAO_VENDA inválido"


def test_admin_reenvia_notificacao_de_venda(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")

    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    with patch("app.criar_pedido_tiny", return_value={"ok": True, "numero": 1}), \
         patch("app.enviar_confirmacao_pedido", return_value={"ok": True}), \
         patch("app.enviar_notificacao_venda", return_value={"erro": "falhou"}):
        client.post(
            "/webhook/infinitepay",
            json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
        )

    with patch("app.enviar_notificacao_venda", return_value={"ok": True}) as mock_reenvio:
        resposta = client.post(
            f"/admin/pedidos/{criado['token']}/reenviar-notificacao-venda", auth=("admin", "segredo123")
        )
    assert resposta.status_code in (302, 303)
    mock_reenvio.assert_called_once()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["notificacao_venda_erro"] is None


def test_webhook_confirma_pagamento_notifica_push_com_valor_e_icone_de_venda(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    with patch("app.enviar_notificacao_push") as push_mock:
        client.post(
            "/webhook/infinitepay",
            json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
        )
    push_mock.assert_called_once()
    kwargs = push_mock.call_args.kwargs
    assert kwargs["titulo"] == "🎉 Você vendeu R$ 60,00"
    assert "venda-icone.png" in kwargs["icone"]
    # nao especifica a forma de pagamento (pix/cartao/boleto) -- pedido
    # explicito do usuario (ver conversa).
    assert "pix" not in kwargs["titulo"].lower()
    assert "cart" not in kwargs["titulo"].lower()


def test_timeline_pedido_pendente_so_criado_e_pendente_marcados(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    from app import _timeline_do_pedido

    pedido = pedidos.obter_pedido(criado["token"])
    timeline = _timeline_do_pedido(pedido)
    assert [etapa["chave"] for etapa in timeline] == [
        "criado", "pendente", "pago", "faturado", "enviado", "entregue",
    ]
    assert [etapa["concluido"] for etapa in timeline] == [True, True, False, False, False, False]
    assert [etapa["atual"] for etapa in timeline] == [False, True, False, False, False, False]


def test_timeline_pedido_pago_avanca_dois_pontos(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
    )

    from app import _timeline_do_pedido

    pedido = pedidos.obter_pedido(criado["token"])
    timeline = _timeline_do_pedido(pedido)
    assert [etapa["concluido"] for etapa in timeline] == [True, True, True, False, False, False]
    assert [etapa["atual"] for etapa in timeline] == [False, False, True, False, False, False]


def test_timeline_pedido_cancelado_e_none(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    pedidos.cancelar_pedido(criado["token"])

    from app import _timeline_do_pedido

    pedido = pedidos.obter_pedido(criado["token"])
    assert _timeline_do_pedido(pedido) is None

    pagina = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "pedido-timeline" not in pagina


def test_pagina_de_pedido_mostra_timeline_com_pontos_preenchidos(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
    )

    corpo = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "Pedido criado" in corpo
    assert "Aguardando pagamento" in corpo
    assert "Pagamento confirmado" in corpo
    assert "Pedido faturado" in corpo
    assert "Pedido enviado" in corpo
    assert "Pedido entregue" in corpo
    assert corpo.count("pedido-timeline-etapa concluida") == 3
    assert 'pedido-timeline-etapa concluida atual' in corpo


def test_timeline_pedido_retirada_no_local_troca_rotulos(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post(
            "/api/pedido/criar",
            json=_corpo_valido(frete={"texto": "Retirada no local", "preco": 0}),
        ).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 5000, "capture_method": "pix"},
    )

    corpo = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "Pronto para retirada" in corpo
    assert "Retirado" in corpo
    assert "Pedido enviado" not in corpo
    assert "Pedido entregue" not in corpo


def test_somar_dias_uteis_pula_fim_de_semana():
    from datetime import datetime

    from services.pedidos import somar_dias_uteis

    # segunda-feira 04/11/2024 + 5 dias uteis -> pula o fim de semana,
    # cai na segunda seguinte (11/11)
    segunda = datetime(2024, 11, 4)
    resultado = somar_dias_uteis(segunda, 5)
    assert resultado.date().isoformat() == "2024-11-11"


def test_previsoes_sem_pagamento_e_none(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    from services.pedidos import previsoes_do_pedido

    pedido = pedidos.obter_pedido(criado["token"])
    previsoes = previsoes_do_pedido(pedido)
    assert previsoes["previsao_envio"] is None
    assert previsoes["previsao_entrega"] is None


def test_criar_pedido_guarda_prazo_do_frete(client):
    corpo = _corpo_valido(frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0, "prazo_dias": 7})
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["frete_prazo_dias"] == 7


def test_pagina_de_pedido_mostra_previsao_de_envio_e_entrega(client):
    corpo = _corpo_valido(frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0, "prazo_dias": 7})
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
    )

    corpo_html = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "Previsão de envio" in corpo_html
    assert "Previsão de entrega" in corpo_html


def test_admin_detalhe_mostra_prazos(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    corpo = _corpo_valido(frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0, "prazo_dias": 7})
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
    )

    detalhe = client.get(f"/admin/pedidos/{criado['token']}", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "Previsão de envio" in detalhe
    assert "Previsão de entrega" in detalhe

    lista = client.get("/admin/pedidos", auth=("admin", "segredo123")).get_data(as_text=True)
    assert "Enviar até" in lista


def test_pagina_de_pedido_mostra_aviso_de_transportadora_e_envio_antecipado(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    corpo = _corpo_valido(frete={"texto": "Correios PAC — R$ 10,00", "preco": 10.0, "prazo_dias": 7})
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix"},
    )
    # marca como enviado logo em seguida (bem antes da previsao de +5 dias
    # uteis de producao) -- deve contar como envio antecipado
    client.post(f"/admin/pedidos/{criado['token']}/status", data={"status": "enviado"}, auth=("admin", "segredo123"))

    corpo_html = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "saiu antes do prazo" in corpo_html
    assert "Prazo estimado pela transportadora" in corpo_html or "prazo de entrega é uma estimativa" in corpo_html


def test_pagina_de_pedido_retirada_nao_mostra_aviso_de_transportadora(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")
    corpo = _corpo_valido(frete={"texto": "Retirada no local", "preco": 0})
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=corpo).get_json()
    client.post(
        "/webhook/infinitepay",
        json={"order_nsu": criado["token"], "paid_amount": 5000, "capture_method": "pix"},
    )
    client.post(f"/admin/pedidos/{criado['token']}/status", data={"status": "enviado"}, auth=("admin", "segredo123"))

    corpo_html = client.get(f"/pedido/{criado['token']}").get_data(as_text=True)
    assert "prazo de entrega é uma estimativa" not in corpo_html
    assert "🏬 Pronto para retirada" in corpo_html


def test_webhook_e_idempotente_nao_reprocessa(client):
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido()).get_json()

    corpo_webhook = {
        "order_nsu": criado["token"], "paid_amount": 6000, "capture_method": "pix", "transaction_nsu": "primeiro",
    }
    client.post("/webhook/infinitepay", json=corpo_webhook)
    client.post("/webhook/infinitepay", json={**corpo_webhook, "transaction_nsu": "segundo"})

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["transaction_nsu"] == "primeiro"
