from __future__ import annotations

import io
import json

import pytest

import services.imagens_personalizadas as imagens_personalizadas
import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
    monkeypatch.setattr(imagens_personalizadas, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _preparar_admin(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")


def test_form_exige_autenticacao(client):
    resposta = client.get("/admin/pedidos/novo-manual")
    assert resposta.status_code == 401


def test_form_mostra_pagina_quando_autenticado(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.get("/admin/pedidos/novo-manual", auth=("admin", "segredo123"))
    assert resposta.status_code == 200
    assert "Registrar pedido manual".encode() in resposta.data


def test_criar_exige_autenticacao(client):
    resposta = client.post("/admin/pedidos/novo-manual", data={})
    assert resposta.status_code == 401


def test_cria_pedido_abaixo_do_minimo_sem_bloquear(client, monkeypatch):
    """ver conversa: pedido negociado de R$ 28,00, abaixo do mínimo de
    R$ 30 do checkout normal -- o admin precisa conseguir registrar
    mesmo assim."""
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Medalha São José 12mm"], "quantidade": ["4"], "valor_unitario": ["7,00"]},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302
    token = resposta.headers["Location"].rsplit("/", 1)[-1]
    pedido = pedidos.obter_pedido(token)
    assert pedido["status"] == "whatsapp"
    assert pedido["subtotal"] == 28.0
    assert pedido["total"] == 28.0
    assert pedido["itens"][0]["produtoNome"] == "Medalha São José 12mm"
    assert pedido["itens"][0]["quantidade"] == 4


def test_cria_pedido_com_varios_itens_soma_o_total(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={
            "descricao": ["Medalha São José 12mm", "Chaveiro Santa Rita"],
            "quantidade": ["2", "1"],
            "valor_unitario": ["5,00", "18,00"],
        },
        auth=("admin", "segredo123"),
    )
    token = resposta.headers["Location"].rsplit("/", 1)[-1]
    pedido = pedidos.obter_pedido(token)
    assert pedido["subtotal"] == 28.0
    assert len(pedido["itens"]) == 2


def test_form_tem_campo_de_email_do_cliente(client, monkeypatch):
    """Ver conversa: o e-mail so precisa estar disponivel aqui (quando o
    admin cadastra o pedido), nao no botao do cliente no carrinho."""
    _preparar_admin(monkeypatch)
    resposta = client.get("/admin/pedidos/novo-manual", auth=("admin", "segredo123"))
    assert b'name="cliente_email"' in resposta.data


def test_cria_pedido_com_email_do_cliente(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={
            "descricao": ["Medalha São José 12mm"], "quantidade": ["4"], "valor_unitario": ["7,00"],
            "cliente_email": "cliente@exemplo.com",
        },
        auth=("admin", "segredo123"),
    )
    token = resposta.headers["Location"].rsplit("/", 1)[-1]
    pedido = pedidos.obter_pedido(token)
    assert pedido["cliente_email"] == "cliente@exemplo.com"


def test_cria_pedido_sem_email_nao_bloqueia(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Medalha São José 12mm"], "quantidade": ["4"], "valor_unitario": ["7,00"]},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302
    token = resposta.headers["Location"].rsplit("/", 1)[-1]
    pedido = pedidos.obter_pedido(token)
    assert pedido["cliente_email"] == ""


def test_ignora_linha_sem_descricao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={
            "descricao": ["Medalha São José 12mm", ""],
            "quantidade": ["4", "1"],
            "valor_unitario": ["7,00", "5,00"],
        },
        auth=("admin", "segredo123"),
    )
    token = resposta.headers["Location"].rsplit("/", 1)[-1]
    pedido = pedidos.obter_pedido(token)
    assert len(pedido["itens"]) == 1


def test_sem_nenhum_item_valido_400(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": [""], "quantidade": ["1"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400


def test_quantidade_invalida_400(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Item"], "quantidade": ["abc"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400


def test_quantidade_zero_400(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Item"], "quantidade": ["0"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400


def test_fluxo_completo_ate_confirmar_venda(client, monkeypatch):
    """Prova ponta a ponta que o pedido manual abaixo do minimo segue
    pro MESMO fluxo ja existente de confirmar venda de lead do
    WhatsApp, sem precisar de nenhuma mudanca la´."""
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Medalha São José 12mm"], "quantidade": ["4"], "valor_unitario": ["7,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]

    resposta = client.post(
        f"/admin/pedidos/{token}/confirmar-venda",
        data={
            "cliente_nome": "Maria Teste",
            "endereco_cep": "59000000",
            "endereco_logradouro": "Rua Teste",
            "endereco_numero": "100",
            "endereco_bairro": "Centro",
            "endereco_cidade": "Natal",
            "endereco_uf": "RN",
            "forma_pagamento": "Pix (combinado no WhatsApp)",
            "valor_pago": "28,00",
        },
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302
    pedido = pedidos.obter_pedido(token)
    assert pedido["status"] == "pago"
    assert pedido["total"] == 28.0


def test_editar_formato_do_item_corrige_chave_preco_pra_tiny(client, monkeypatch):
    """ver conversa: item do pedido manual entra com chave_preco=""
    (ninguem digita isso na mao), e sem uma chave valida de
    services/pricing.py:CHAVES_PRECO a Tiny recebe codigo/descricao em
    branco pro produto (ver services/tiny.py:_chave_material). Aqui o
    admin escolhe o formato/tamanho de verdade e a chave passa a bater
    com o que o carrinho normal do site geraria."""
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Medalha São José"], "quantidade": ["4"], "valor_unitario": ["7,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]
    pedido = pedidos.obter_pedido(token)
    assert pedido["itens"][0]["chave_preco"] == ""

    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/editar-formato",
        data={"produto_nome": "São José", "formato": "medalha", "tamanho": "12mm"},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302
    pedido = pedidos.obter_pedido(token)
    item = pedido["itens"][0]
    assert item["chave_preco"] == "12mm"
    assert item["formato"] == "medalha"
    assert item["produtoNome"] == "São José"
    assert "1,2 cm" in item["detalhe"]


def test_editar_formato_entremeio_exige_cor(client, monkeypatch):
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Entremeio Santa Rita"], "quantidade": ["1"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]

    sem_cor = client.post(
        f"/admin/pedidos/{token}/itens/0/editar-formato",
        data={"produto_nome": "Santa Rita", "formato": "entremeio"},
        auth=("admin", "segredo123"),
    )
    assert sem_cor.status_code == 400

    com_cor = client.post(
        f"/admin/pedidos/{token}/itens/0/editar-formato",
        data={"produto_nome": "Santa Rita", "formato": "entremeio", "cor": "ouro_velho"},
        auth=("admin", "segredo123"),
    )
    assert com_cor.status_code == 302
    item = pedidos.obter_pedido(token)["itens"][0]
    assert item["chave_preco"] == "entremeio"
    assert item["cor"] == "ouro_velho"


def test_editar_formato_indice_invalido_404(client, monkeypatch):
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Item"], "quantidade": ["1"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]
    resposta = client.post(
        f"/admin/pedidos/{token}/itens/9/editar-formato",
        data={"produto_nome": "X", "formato": "chaveiro"},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 404


def test_editar_formato_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Item"], "quantidade": ["1"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]
    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/editar-formato",
        data={"produto_nome": "X", "formato": "chaveiro"},
    )
    assert resposta.status_code == 401


def test_editar_imagem_do_item_normaliza_caminho_cru_pro_formato_resolvido(client, monkeypatch):
    """ver conversa 2026-09-18: colar o caminho "cru" igual ao
    produtos.json (sem /static/ na frente) deixou a foto em branco na
    primeira tentativa -- o pedido guarda o caminho RESOLVIDO
    (item.imagem e´ renderizado direto em templates/pedido.html, sem
    passar por url_for de novo). Essa rota normaliza sozinha."""
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Medalha São José"], "quantidade": ["1"], "valor_unitario": ["7,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]
    itens = pedidos.obter_pedido(token)["itens"]
    itens[0]["imagem"] = "/static/img/produtos/sao_jose_terror_dos_demonios_modelo_1_medalha.jpg"
    with pedidos._conexao() as conexao:
        conexao.execute("UPDATE pedidos SET itens = ? WHERE token = ?", (json.dumps(itens), token))

    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/editar-imagem",
        data={"imagem": "img/produtos/sao_jose_terror_dos_demonios_modelo_2_medalha.jpg"},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302
    item = pedidos.obter_pedido(token)["itens"][0]
    assert item["imagem"].startswith("/static/img/produtos/sao_jose_terror_dos_demonios_modelo_2_medalha.jpg")
    # nao mexe em quantidade/valor cobrado do cliente
    assert item["quantidade"] == 1


def test_editar_imagem_do_item_aceita_caminho_ja_resolvido_sem_duplicar_prefixo(client, monkeypatch):
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Item"], "quantidade": ["1"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]
    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/editar-imagem",
        data={"imagem": "/static/img/produtos/sao_jose_terror_dos_demonios_modelo_2_medalha.jpg"},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302
    item = pedidos.obter_pedido(token)["itens"][0]
    assert item["imagem"] == "/static/img/produtos/sao_jose_terror_dos_demonios_modelo_2_medalha.jpg"


def test_editar_imagem_exige_caminho_nao_vazio(client, monkeypatch):
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Item"], "quantidade": ["1"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]
    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/editar-imagem",
        data={"imagem": ""},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400


def test_editar_imagem_indice_invalido_404(client, monkeypatch):
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Item"], "quantidade": ["1"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]
    resposta = client.post(
        f"/admin/pedidos/{token}/itens/9/editar-imagem",
        data={"imagem": "img/produtos/x.jpg"},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 404


def test_editar_imagem_exige_autenticacao(client, monkeypatch):
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Item"], "quantidade": ["1"], "valor_unitario": ["5,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]
    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/editar-imagem",
        data={"imagem": "img/produtos/x.jpg"},
    )
    assert resposta.status_code == 401


def _criar_pedido_com_item_personalizada(client, monkeypatch, *, duas_faces=False):
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Personalizada"], "quantidade": ["1"], "valor_unitario": ["20,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]
    itens = pedidos.obter_pedido(token)["itens"]
    itens[0]["produtoNome"] = "Personalizada"
    itens[0]["semImagem"] = True
    if duas_faces:
        itens[0]["duasFaces"] = True
    with pedidos._conexao() as conexao:
        conexao.execute("UPDATE pedidos SET itens = ? WHERE token = ?", (json.dumps(itens), token))
    return token


def test_enviar_foto_do_item_anexa_imagem_sem_gerar_simulacao(client, monkeypatch):
    """ver conversa 2026-09-20: o admin quer só subir a foto (já cortada
    1:1 por quem fez o pedido, ou corrigida na mão fora do site) -- sem
    gastar memória do Render gerando compose_medal/preview. A rota salva
    o arquivo enviado como veio, em DUAS linhas/tokens diferentes (mesmos
    bytes) -- uma pra `imagem`, outra pra `imagemRecorte` -- ver conversa
    2026-09-22: tokens iguais fazia a limpeza de recortes derrubar a
    imagem exibida na página de acompanhamento junto (bug real)."""
    token = _criar_pedido_com_item_personalizada(client, monkeypatch)

    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/enviar-foto",
        data={"imagem": (io.BytesIO(b"conteudo-fake-da-foto"), "foto.jpg")},
        content_type="multipart/form-data",
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302
    item = pedidos.obter_pedido(token)["itens"][0]
    assert item["semImagem"] is False
    assert item["imagem"]
    assert item["imagemRecorte"]
    assert item["imagemRecorte"] != item["imagem"]

    for campo in ("imagem", "imagemRecorte"):
        servida = client.get(item[campo])
        assert servida.status_code == 200
        assert servida.data == b"conteudo-fake-da-foto"


def test_enviar_foto_sobrevive_a_limpeza_de_recortes_antigos(client, monkeypatch):
    """ver conversa 2026-09-22: bug real reportado -- apagar o recorte
    velho/usado (purgar_recortes_usados_antigos) NÃO pode derrubar a
    imagem mostrada na página de acompanhamento (`imagem`), porque essa
    função promete nunca mexer na preview. Só funciona se os dois
    campos usarem tokens DIFERENTES (ver fix acima)."""
    token = _criar_pedido_com_item_personalizada(client, monkeypatch)
    client.post(
        f"/admin/pedidos/{token}/itens/0/enviar-foto",
        data={"imagem": (io.BytesIO(b"conteudo-fake-da-foto"), "foto.jpg")},
        content_type="multipart/form-data",
        auth=("admin", "segredo123"),
    )
    item = pedidos.obter_pedido(token)["itens"][0]

    from datetime import datetime, timedelta, timezone
    passado = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    with imagens_personalizadas._conexao() as conexao:
        conexao.execute("UPDATE imagens_personalizadas SET criado_em = ?", (passado,))

    imagens_personalizadas.purgar_recortes_usados_antigos(dias=30)

    servida = client.get(item["imagem"])
    assert servida.status_code == 200
    assert servida.data == b"conteudo-fake-da-foto"


def test_enviar_foto_marca_imagem_usada_pra_sobreviver_a_limpeza_7_dias(client, monkeypatch):
    """ver conversa 2026-09-22: faltava marcar_imagem_usada -- o job
    diario purgar_imagens_antigas(dias=7) apagava a foto anexada aqui
    depois de uma semana (usada_em_pedido nunca virava 1), quebrando a
    imagem do pedido de verdade (link de acompanhamento e "Repetir
    esse pedido")."""
    token = _criar_pedido_com_item_personalizada(client, monkeypatch)
    client.post(
        f"/admin/pedidos/{token}/itens/0/enviar-foto",
        data={"imagem": (io.BytesIO(b"conteudo-fake-da-foto"), "foto.jpg")},
        content_type="multipart/form-data",
        auth=("admin", "segredo123"),
    )
    item = pedidos.obter_pedido(token)["itens"][0]
    token_imagem = item["imagem"].rsplit("/", 1)[-1]

    with imagens_personalizadas._conexao() as conexao:
        linha = conexao.execute(
            "SELECT usada_em_pedido FROM imagens_personalizadas WHERE token = ?", (token_imagem,)
        ).fetchone()
    assert linha["usada_em_pedido"] == 1

    removidas = imagens_personalizadas.purgar_imagens_antigas(dias=0)
    assert removidas == 0
    assert imagens_personalizadas.obter_imagem(token_imagem) is not None


def test_enviar_foto_lado_especifico_preserva_o_outro_lado(client, monkeypatch):
    token = _criar_pedido_com_item_personalizada(client, monkeypatch, duas_faces=True)
    itens = pedidos.obter_pedido(token)["itens"]
    itens[0]["imagemLado2"] = "/imagem-personalizada/ja-existente"
    itens[0]["imagemRecorteLado2"] = "/imagem-personalizada/ja-existente"
    with pedidos._conexao() as conexao:
        conexao.execute("UPDATE pedidos SET itens = ? WHERE token = ?", (json.dumps(itens), token))

    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/enviar-foto",
        data={"lado": "1", "imagem": (io.BytesIO(b"foto-do-lado-1"), "lado1.png")},
        content_type="multipart/form-data",
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 302
    item = pedidos.obter_pedido(token)["itens"][0]
    assert item["imagemLado1"]
    assert item["imagemRecorteLado1"]
    assert item["imagemRecorteLado1"] != item["imagemLado1"]
    # lado 2 nao foi mexido
    assert item["imagemLado2"] == "/imagem-personalizada/ja-existente"


def test_enviar_foto_lado_invalido_400(client, monkeypatch):
    token = _criar_pedido_com_item_personalizada(client, monkeypatch, duas_faces=True)
    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/enviar-foto",
        data={"lado": "3", "imagem": (io.BytesIO(b"x"), "foto.jpg")},
        content_type="multipart/form-data",
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400


def test_enviar_foto_lado_em_item_de_1_lado_400(client, monkeypatch):
    token = _criar_pedido_com_item_personalizada(client, monkeypatch, duas_faces=False)
    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/enviar-foto",
        data={"lado": "1", "imagem": (io.BytesIO(b"x"), "foto.jpg")},
        content_type="multipart/form-data",
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400


def test_enviar_foto_sem_arquivo_400(client, monkeypatch):
    token = _criar_pedido_com_item_personalizada(client, monkeypatch)
    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/enviar-foto",
        data={},
        content_type="multipart/form-data",
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400


def test_enviar_foto_extensao_invalida_400(client, monkeypatch):
    token = _criar_pedido_com_item_personalizada(client, monkeypatch)
    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/enviar-foto",
        data={"imagem": (io.BytesIO(b"x"), "foto.exe")},
        content_type="multipart/form-data",
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 400


def test_enviar_foto_indice_invalido_404(client, monkeypatch):
    token = _criar_pedido_com_item_personalizada(client, monkeypatch)
    resposta = client.post(
        f"/admin/pedidos/{token}/itens/9/enviar-foto",
        data={"imagem": (io.BytesIO(b"x"), "foto.jpg")},
        content_type="multipart/form-data",
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 404


def test_enviar_foto_exige_autenticacao(client, monkeypatch):
    token = _criar_pedido_com_item_personalizada(client, monkeypatch)
    resposta = client.post(
        f"/admin/pedidos/{token}/itens/0/enviar-foto",
        data={"imagem": (io.BytesIO(b"x"), "foto.jpg")},
        content_type="multipart/form-data",
    )
    assert resposta.status_code == 401


def test_item_manual_aparece_no_csv_de_producao(client, monkeypatch):
    """ver conversa: item manual nao tem produtoNome vindo do catalogo,
    precisa cair no CSV mesmo assim usando a descricao digitada."""
    _preparar_admin(monkeypatch)
    criado = client.post(
        "/admin/pedidos/novo-manual",
        data={"descricao": ["Medalha São José 12mm"], "quantidade": ["4"], "valor_unitario": ["7,00"]},
        auth=("admin", "segredo123"),
    )
    token = criado.headers["Location"].rsplit("/", 1)[-1]
    resposta = client.get(f"/admin/pedidos/{token}/csv", auth=("admin", "segredo123"))
    assert resposta.status_code == 200
    texto = resposta.data.decode("utf-8-sig")
    assert "Medalha São José 12mm" in texto
