from __future__ import annotations

import pytest

import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


# ---- produtos (URLs /<slug>/p da plataforma antiga -- ver auditoria
# Search Console/conversa) ----

def test_produto_legado_com_prefixo_e_sufixo_redireciona_301(client):
    resposta = client.get("/medalha-de-sao-joao-paulo-ii-modelo-1/p")
    assert resposta.status_code == 301
    assert resposta.headers["Location"] == "/produto/sao-joao-paulo-ii"


def test_produto_legado_chaveiro_com_1_lado_redireciona(client):
    resposta = client.get("/chaveiro-de-santa-teresa-davila-1-lado/p")
    assert resposta.status_code == 301
    assert resposta.headers["Location"] == "/produto/santa-teresa-davila"


def test_produto_legado_pingente_folheado_a_ouro_redireciona(client):
    resposta = client.get("/pingente-de-santa-rita-de-cassia-folheado-a-ouro/p")
    assert resposta.status_code == 301
    assert resposta.headers["Location"] == "/produto/santa-rita-de-cassia"


def test_produto_legado_cadeia_de_consagracao_inox_redireciona(client):
    resposta = client.get("/cadeia-de-consagracao-inox-de-nossa-senhora-aparecida-modelo-1/p")
    assert resposta.status_code == 301
    assert resposta.headers["Location"] == "/produto/nossa-senhora-aparecida"


@pytest.mark.parametrize(
    ("slug_legado", "produto_id_atual"),
    [
        ("medalha-do-ressuscitado-que-passou-pela-cruz", "ressuscitado"),
        ("medalha-da-serva-de-deus-clare-crocker", "irma-clare"),
        ("medalha-de-beato-carlo-acutis-modelo-1", "carlo-acutis"),
        ("medalha-de-beato-pier-giorgio-frassati", "sao-pier-giorgio-frassati"),
        ("medalha-de-nossa-senhora-da-ternura", "nossa-senhora-mae-da-ternura"),
        ("medalha-de-santa-gemma-galgani", "santa-gemma"),
        ("medalha-de-santa-gianna-beretta-molla-modelo-1", "santa-gianna"),
        ("medalha-de-santa-teresa-benedita-da-cruz-edith-stein", "edith-stein"),
        ("medalha-de-sao-josemaria-escriva", "sao-jose-maria-escriva"),
        ("medalha-de-sao-luiz-e-santa-zelia-pais-de-teresinha-modelo-1", "pais-de-teresinha"),
        ("medalha-de-sao-miguel-arcanjo-modelo-1", "sao-miguel"),
        ("medalha-do-divino-semeador", "jesus-semeador"),
    ],
)
def test_produto_legado_com_alias_manual_redireciona(client, slug_legado, produto_id_atual):
    resposta = client.get(f"/{slug_legado}/p")
    assert resposta.status_code == 301
    assert resposta.headers["Location"] == f"/produto/{produto_id_atual}"


def test_produto_legado_descontinuado_devolve_404(client):
    """Sem produto correspondente hoje (peca saiu do catalogo) -- melhor
    404 do que arriscar redirecionar pro produto errado."""
    resposta = client.get("/medalha-de-nossa-senhora-das-lagrimas/p")
    assert resposta.status_code == 404


def test_produto_legado_slug_desconhecido_devolve_404(client):
    resposta = client.get("/coisa-que-nunca-existiu/p")
    assert resposta.status_code == 404


# ---- personalizada (3 URLs da plataforma antiga) ----

@pytest.mark.parametrize(
    ("slug_legado", "formato_esperado"),
    [
        ("medalha-de-santo-personalizada-de-1-lado", "medalha"),
        ("medalha-personalizada-de-2-lados", "medalha_2lados"),
        ("chaveiro-personalizado-de-2-lados", "chaveiro_2lados"),
    ],
)
def test_personalizada_legado_redireciona_com_formato(client, slug_legado, formato_esperado):
    resposta = client.get(f"/{slug_legado}/p")
    assert resposta.status_code == 301
    assert resposta.headers["Location"] == f"/personalizada?formato={formato_esperado}"


# ---- atendimento (slugs renomeados na migracao) ----

@pytest.mark.parametrize(
    ("slug_legado", "slug_atual"),
    [
        ("politicas-de-pagamento", "formas-de-pagamento"),
        ("politica-de-cookies", "termos-e-privacidade"),
        ("termos-de-uso-e-politica-de-privacidade", "termos-e-privacidade"),
        ("politica-de-devolucao-e-reembolso", "trocas-e-devolucao"),
    ],
)
def test_atendimento_legado_redireciona(client, slug_legado, slug_atual):
    resposta = client.get(f"/atendimento/{slug_legado}")
    assert resposta.status_code == 301
    assert resposta.headers["Location"] == f"/atendimento/{slug_atual}"


def test_atendimento_precos_de_atacado_redireciona_pro_catalogo(client):
    resposta = client.get("/atendimento/precos-de-atacado")
    assert resposta.status_code == 301
    assert resposta.headers["Location"] == "/catalogo"


def test_atendimento_quem_somos_continua_funcionando_direto(client):
    """Slug que nao mudou na migracao -- serve a pagina normal, sem
    redirecionar."""
    resposta = client.get("/atendimento/quem-somos")
    assert resposta.status_code == 200
