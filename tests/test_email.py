from __future__ import annotations

from unittest.mock import Mock, patch

import services.email as email


def _pedido_exemplo(**overrides):
    base = dict(
        codigo="ABC123",
        itens=[{"chave_preco": "16mm", "quantidade": 10, "descricao": "São José — Modelo 1"}],
        subtotal=50.0,
        frete_descricao="Correios PAC — R$ 10,00",
        frete_preco=10.0,
        total=60.0,
        cliente_nome="Maria Teste",
        cliente_email="maria@example.com",
    )
    base.update(overrides)
    return base


def test_sem_api_key_devolve_erro(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "")
    resultado = email.enviar_confirmacao_pedido(_pedido_exemplo(), "https://site/pedido/token")
    assert "erro" in resultado


def test_pedido_sem_email_devolve_erro(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resultado = email.enviar_confirmacao_pedido(_pedido_exemplo(cliente_email=""), "https://site/pedido/token")
    assert "erro" in resultado


def test_envia_com_payload_correto(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "EMAIL_REMETENTE", "9djulho@gmail.com")
    monkeypatch.setattr(email, "EMAIL_REMETENTE_NOME", "Nove de Julho")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        resultado = email.enviar_confirmacao_pedido(_pedido_exemplo(), "https://site/pedido/token")

    assert resultado == {"ok": True}
    corpo = post_mock.call_args.kwargs["json"]
    assert corpo["sender"] == {"name": "Nove de Julho", "email": "9djulho@gmail.com"}
    assert corpo["to"] == [{"email": "maria@example.com", "name": "Maria Teste"}]
    assert "ABC123" in corpo["subject"]
    assert "https://site/pedido/token" in corpo["htmlContent"]
    assert "R$ 60,00" in corpo["htmlContent"]
    assert "produção" in corpo["htmlContent"]
    assert post_mock.call_args.kwargs["headers"]["api-key"] == "segredo"


def test_com_previsao_de_entrega_mostra_aviso_de_transportadora(monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    pedido = _pedido_exemplo(pago_em=datetime(2024, 11, 4, tzinfo=timezone.utc).isoformat(), frete_prazo_dias=7)
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(pedido, "https://site/pedido/token")

    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert "entrega prevista" in corpo
    assert "prazo de entrega é uma estimativa da transportadora" in corpo


def test_nome_do_cliente_com_html_e_escapado(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    pedido = _pedido_exemplo(cliente_nome='<img src=x onerror=alert(1)>', frete_descricao='<script>x</script>')
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(pedido, "https://site/pedido/token")

    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert "<img src=x onerror" not in corpo
    assert "<script>" not in corpo
    assert "&lt;img" in corpo


def test_erro_de_rede(monkeypatch):
    import requests

    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    with patch("services.email.requests.post", side_effect=requests.RequestException("timeout")):
        resultado = email.enviar_confirmacao_pedido(_pedido_exemplo(), "https://site/pedido/token")
    assert "erro" in resultado


def test_link_de_acompanhamento_tem_utm_de_email(monkeypatch):
    """Ver conversa: sem isso o GA4 nao separa venda vinda de e-mail de
    trafego direto -- mesmo nome de campanha usado na tag do Brevo."""
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(_pedido_exemplo(), "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert "https://site/pedido/token?utm_source=email&utm_medium=email&utm_campaign=confirmacao_pedido" in corpo


def test_link_com_query_string_usa_e_comercial_no_utm(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_lembrete_carrinho_abandonado(
            {"nome": "Maria", "email": "maria@example.com", "itens": []},
            "https://site/carrinho?restaurar=abc123",
        )
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert "https://site/carrinho?restaurar=abc123&utm_source=email&utm_medium=email&utm_campaign=lembrete_carrinho_abandonado" in corpo


def test_link_nota_fiscal_externo_nao_recebe_utm(monkeypatch):
    """Link de terceiro (nota fiscal emitida por outro servico) nunca
    ganha UTM -- so links do proprio site."""
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    pedido = _pedido_exemplo(link_nota_fiscal="https://nfe.exemplo.com/danfe/123")
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_nota_fiscal_disponivel(pedido, "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert 'href="https://nfe.exemplo.com/danfe/123"' in corpo
    assert "https://site/pedido/token?utm_source=email" in corpo


def test_notificacao_venda_nao_leva_utm(monkeypatch):
    """E-mail interno pro dono da loja, nao pro cliente -- nao faz
    sentido medir "canal de origem" de um clique do proprio admin."""
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "EMAIL_NOTIFICACAO_VENDA", "loja@example.com")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_notificacao_venda(_pedido_exemplo(), "https://site/admin/pedidos/token")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert "utm_source" not in corpo


def test_todo_email_mostra_o_logo_no_cabecalho(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(_pedido_exemplo(), "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert '<img src="https://lojanovedejulho.com.br/static/img/logo-icone.png"' in corpo


def test_sem_canonical_domain_nao_mostra_cabecalho_quebrado(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "CANONICAL_DOMAIN", "")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(_pedido_exemplo(), "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert "<img" not in corpo


def test_item_com_imagem_mostra_miniatura_no_email(monkeypatch):
    """Ver conversa: mesmo no plano gratuito do Brevo isso funciona --
    e´ so um <img src="URL completa"> no HTML, o e-mail busca direto no
    site, nao precisa o Brevo hospedar nada."""
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    pedido = _pedido_exemplo(
        itens=[{
            "chave_preco": "16mm", "quantidade": 2, "descricao": "São José — Modelo 1",
            "imagem": "/static/img/produtos/sao_jose_modelo_1_medalha.jpg",
        }]
    )
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(pedido, "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert '<img src="https://lojanovedejulho.com.br/static/img/produtos/sao_jose_modelo_1_medalha.jpg"' in corpo


def test_item_sem_imagem_nao_quebra_e_nao_mostra_img(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(_pedido_exemplo(), "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert corpo.count("<img") == 1  # so o logo do cabecalho, nenhuma miniatura de item


def test_item_com_placeholder_sem_foto_nao_mostra_img(monkeypatch):
    """Peca personalizada sem foto enviada ainda usa um icone generico
    (sem-foto.svg) -- mostrar isso como "foto do produto" confundiria
    mais do que ajudaria."""
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    pedido = _pedido_exemplo(
        itens=[{"chave_preco": "16mm", "quantidade": 1, "descricao": "Personalizada", "imagem": "/static/img/sem-foto.svg"}]
    )
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(pedido, "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert corpo.count("<img") == 1  # so o logo do cabecalho, nenhuma miniatura de item


def test_item_sem_canonical_domain_nao_mostra_img_quebrada(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "CANONICAL_DOMAIN", "")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    pedido = _pedido_exemplo(
        itens=[{
            "chave_preco": "16mm", "quantidade": 2, "descricao": "São José — Modelo 1",
            "imagem": "/static/img/produtos/sao_jose_modelo_1_medalha.jpg",
        }]
    )
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(pedido, "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert "<img" not in corpo


def test_item_imagem_ja_absoluta_nao_duplica_dominio(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    pedido = _pedido_exemplo(
        itens=[{
            "chave_preco": "16mm", "quantidade": 1, "descricao": "São José",
            "imagem": "https://outrocdn.com/foto.jpg",
        }]
    )
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(pedido, "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert '<img src="https://outrocdn.com/foto.jpg"' in corpo


def test_carrinho_abandonado_mostra_miniatura(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "CANONICAL_DOMAIN", "lojanovedejulho.com.br")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    carrinho = {
        "nome": "Maria", "email": "maria@example.com",
        "itens": [{"produtoNome": "São José", "quantidade": 1, "imagem": "/static/img/produtos/sao_jose.jpg"}],
    }
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_lembrete_carrinho_abandonado(carrinho, "https://site/carrinho?restaurar=abc")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert '<img src="https://lojanovedejulho.com.br/static/img/produtos/sao_jose.jpg"' in corpo


def test_upsell_de_cruz_manda_mensagem_de_whatsapp_com_quantidade(monkeypatch):
    """Ver conversa "upsell de cruz durante producao" -- e-mail novo
    oferece cruz (peca pronta) pra quem comprou entremeio sem cruz,
    combinado pelo WhatsApp em vez de link pro catalogo."""
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "WHATSAPP_NUMBER", "5584999999999")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        resultado = email.enviar_oportunidade_upsell(_pedido_exemplo(), 12)

    assert resultado == {"ok": True}
    corpo = post_mock.call_args.kwargs["json"]
    assert "cruz" in corpo["subject"].lower()
    assert "12 entremeios" in corpo["htmlContent"]
    assert "https://wa.me/5584999999999?text=" in corpo["htmlContent"]
    assert "retirada no local" in corpo["htmlContent"].lower()


def test_notificacao_venda_nao_manda_name_vazio_pro_brevo(monkeypatch):
    """Ver conversa: o Brevo devolvia 400 Bad Request pra esse e-mail
    especifico -- causa era "name": "" no destinatario (aviso interno
    pra loja nao tem nome de cliente pra usar, so o e-mail)."""
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "EMAIL_NOTIFICACAO_VENDA", "loja@example.com")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        resultado = email.enviar_notificacao_venda(_pedido_exemplo(), "https://site/admin/pedidos/token")

    assert resultado == {"ok": True}
    corpo = post_mock.call_args.kwargs["json"]
    assert corpo["to"] == [{"email": "loja@example.com"}]


def test_link_pagamento_sem_api_key_devolve_erro(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "")
    resultado = email.enviar_link_pagamento(
        _pedido_exemplo(), "https://checkout.infinitepay.io/abc", "https://site/pedido/token"
    )
    assert "erro" in resultado


def test_link_pagamento_envia_com_payload_correto(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        resultado = email.enviar_link_pagamento(
            _pedido_exemplo(), "https://checkout.infinitepay.io/abc", "https://site/pedido/token"
        )

    assert resultado == {"ok": True}
    corpo = post_mock.call_args.kwargs["json"]
    assert "ABC123" in corpo["subject"]
    assert "https://checkout.infinitepay.io/abc" in corpo["htmlContent"]
    assert "https://site/pedido/token" in corpo["htmlContent"]


def test_link_de_acompanhamento_e_um_botao_nao_link_cru(monkeypatch):
    """Ver conversa: link repetido como texto cru pesa mal em filtro de
    spam e passa despercebido no celular -- vira um botao com fundo."""
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_confirmacao_pedido(_pedido_exemplo(), "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert "background-color:#14335c" in corpo
    assert "Clique aqui e acompanhe" in corpo
    assert corpo.count("https://site/pedido/token") == 1  # nao repete a URL como texto visivel


def test_lembrete_sem_api_key_devolve_erro(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "")
    resultado = email.enviar_lembrete_pedido_pendente(
        _pedido_exemplo(), "https://checkout.infinitepay.io/novo", "https://site/pedido/token"
    )
    assert "erro" in resultado


def test_lembrete_envia_com_payload_correto(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        resultado = email.enviar_lembrete_pedido_pendente(
            _pedido_exemplo(), "https://checkout.infinitepay.io/novo", "https://site/pedido/token"
        )

    assert resultado == {"ok": True}
    corpo = post_mock.call_args.kwargs["json"]
    assert "ainda não foi pago" in corpo["subject"]
    assert "https://checkout.infinitepay.io/novo" in corpo["htmlContent"]


def test_pedido_enviado_com_link_de_rastreio(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        resultado = email.enviar_pedido_enviado(
            _pedido_exemplo(), "BR123456789BR", "https://rastreio.exemplo/BR123", "https://site/pedido/token"
        )

    assert resultado == {"ok": True}
    corpo = post_mock.call_args.kwargs["json"]
    assert "enviado" in corpo["subject"].lower()
    assert "BR123456789BR" in corpo["htmlContent"]
    assert "https://rastreio.exemplo/BR123" in corpo["htmlContent"]


def test_pedido_enviado_sem_link_de_rastreio(monkeypatch):
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        email.enviar_pedido_enviado(_pedido_exemplo(), "BR123456789BR", "", "https://site/pedido/token")
    corpo = post_mock.call_args.kwargs["json"]
    assert "BR123456789BR" in corpo["htmlContent"]


def test_pedido_enviado_com_retirada_no_local_manda_botao_de_whatsapp(monkeypatch):
    """Pedido de retirada no local nao tem transportadora/rastreio --
    o e-mail generico de "enviado" nao faz sentido, precisa avisar que
    ja´ esta´ pronto com um botao de WhatsApp pra combinar (ver
    conversa)."""
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "WHATSAPP_NUMBER", "5584999999999")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        resultado = email.enviar_pedido_enviado(
            _pedido_exemplo(frete_descricao="Retirada no local"), "", "", "https://site/pedido/token"
        )

    assert resultado == {"ok": True}
    corpo = post_mock.call_args.kwargs["json"]
    assert "pronto para retirada" in corpo["subject"].lower()
    assert "pronto pra" in corpo["htmlContent"].lower()
    assert "https://wa.me/5584999999999?text=" in corpo["htmlContent"]
    assert "ABC123" in corpo["htmlContent"]


def test_pedido_cancelado_oferece_3_jeitos_de_reaproveitar_o_pedido(monkeypatch):
    """ver conversa: reaproveita o MESMO pedido -- Pix/cartao, boleto ou
    WhatsApp -- em vez de so linkar de volta pro catalogo."""
    monkeypatch.setattr(email, "BREVO_API_KEY", "segredo")
    monkeypatch.setattr(email, "WHATSAPP_NUMBER", "5584999999999")
    resposta_mock = Mock()
    resposta_mock.raise_for_status = Mock()
    with patch("services.email.requests.post", return_value=resposta_mock) as post_mock:
        resultado = email.enviar_pedido_cancelado(
            _pedido_exemplo(),
            "https://site/pedido/token/reativar-pix",
            "https://site/pedido/token/reativar-boleto",
        )

    assert resultado == {"ok": True}
    corpo = post_mock.call_args.kwargs["json"]["htmlContent"]
    assert "https://site/pedido/token/reativar-pix" in corpo
    assert "https://site/pedido/token/reativar-boleto" in corpo
    assert "https://wa.me/5584999999999?text=" in corpo
    assert "ABC123" in corpo


