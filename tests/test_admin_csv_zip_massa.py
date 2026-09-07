from __future__ import annotations

import io
import zipfile
from unittest.mock import patch

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


def _criar_pedido(client, **overrides) -> str:
    with patch("app.criar_link_pagamento", return_value={"url": "https://checkout.infinitepay.io/abc"}):
        criado = client.post("/api/pedido/criar", json=_corpo_valido(**overrides)).get_json()
    return criado["token"]


# ---- CSV total ----


def test_csv_total_exige_autenticacao(client):
    resposta = client.post("/admin/pedidos/csv-total", data={"tokens": ["x"]})
    assert resposta.status_code == 401


def test_csv_total_sem_selecao_redireciona_sem_gerar_arquivo(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post("/admin/pedidos/csv-total", data={}, auth=("admin", "segredo123"))
    assert resposta.status_code == 302


def test_csv_total_junta_pedidos_sem_separador_quando_variacao_diferente(client, monkeypatch):
    _preparar_admin(monkeypatch)
    token1 = _criar_pedido(
        client, itens=[{"chave_preco": "12mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"}]
    )
    token2 = _criar_pedido(
        client, itens=[{"chave_preco": "16mm", "quantidade": 10, "produtoNome": "Santa Rita", "modeloNome": "Modelo 1"}]
    )
    resposta = client.post(
        "/admin/pedidos/csv-total", data={"tokens": [token1, token2]}, auth=("admin", "segredo123")
    )
    assert resposta.status_code == 200
    texto = resposta.data.decode("utf-8-sig")
    linhas = [l for l in texto.strip().splitlines()]
    assert linhas[0] == "Produto;Modelo;Variação;Quantidade"
    assert "São José" in linhas[1] and ";12;" in linhas[1]
    assert "Santa Rita" in linhas[2] and ";16;" in linhas[2]
    assert "Nove de Julho" not in texto  # variacoes diferentes, sem precisar de separador


def test_csv_total_insere_linha_separadora_quando_variacao_repete(client, monkeypatch):
    _preparar_admin(monkeypatch)
    token1 = _criar_pedido(
        client, itens=[{"chave_preco": "12mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"}]
    )
    token2 = _criar_pedido(
        client, itens=[{"chave_preco": "12mm", "quantidade": 10, "produtoNome": "Santa Rita", "modeloNome": "Modelo 1"}]
    )
    resposta = client.post(
        "/admin/pedidos/csv-total", data={"tokens": [token1, token2]}, auth=("admin", "segredo123")
    )
    texto = resposta.data.decode("utf-8-sig")
    linhas = texto.strip().splitlines()
    assert linhas[0] == "Produto;Modelo;Variação;Quantidade"
    assert "São José" in linhas[1]
    assert linhas[2] == "Nove de Julho;1;12;1"
    assert "Santa Rita" in linhas[3]


def test_csv_total_separa_por_tamanho_compartilhado_mesmo_fora_das_bordas(client, monkeypatch):
    """ver conversa: o programa de produção monta uma folha POR TAMANHO,
    então o que importa é se os 2 pedidos compartilham um tamanho em
    QUALQUER posição -- não só se a última linha de um bate com a
    primeira do outro."""
    _preparar_admin(monkeypatch)
    token1 = _criar_pedido(
        client,
        itens=[
            {"chave_preco": "12mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"},
            {"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"},
        ],
    )
    token2 = _criar_pedido(
        client,
        itens=[
            {"chave_preco": "12mm", "quantidade": 10, "produtoNome": "Santa Rita", "modeloNome": "Modelo 1"},
            {"chave_preco": "chaveiro", "quantidade": 10, "produtoNome": "Santa Rita", "modeloNome": "Modelo 1"},
        ],
    )
    resposta = client.post(
        "/admin/pedidos/csv-total", data={"tokens": [token1, token2]}, auth=("admin", "segredo123")
    )
    texto = resposta.data.decode("utf-8-sig")
    # ultima linha do pedido1 e´ 16, primeira do pedido2 e´ 12 -- bordas
    # diferentes, mas os 2 pedidos COMPARTILHAM o tamanho 12 (1a linha
    # do pedido1, nao a ultima)
    assert "Nove de Julho;1;12;1" in texto
    assert "Nove de Julho;1;16;1" not in texto  # 16 so aparece no pedido1
    assert "Nove de Julho;1;29;1" not in texto  # 29 (chaveiro) so aparece no pedido2


def test_csv_total_pula_pedido_do_meio_sem_aquele_tamanho(client, monkeypatch):
    """ver conversa: pedido1 tem 12+16+29, pedido2 so´ tem 12, pedido3
    so´ tem 16 -- na folha do 16, pedido1 fica colado no pedido3
    (pedido2 nao entra ali), entao precisa de separador de 16 mesmo
    pedido3 nao sendo o vizinho direto de pedido1."""
    _preparar_admin(monkeypatch)
    token1 = _criar_pedido(
        client,
        itens=[
            {"chave_preco": "12mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"},
            {"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"},
            {"chave_preco": "chaveiro", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"},
        ],
    )
    token2 = _criar_pedido(
        client, itens=[{"chave_preco": "12mm", "quantidade": 10, "produtoNome": "Santa Rita", "modeloNome": "Modelo 1"}]
    )
    token3 = _criar_pedido(
        client, itens=[{"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São Judas", "modeloNome": "Modelo 1"}]
    )
    resposta = client.post(
        "/admin/pedidos/csv-total", data={"tokens": [token1, token2, token3]}, auth=("admin", "segredo123")
    )
    linhas = resposta.data.decode("utf-8-sig").strip().splitlines()
    indice_sao_jose_16 = next(i for i, l in enumerate(linhas) if "São José" in l and ";16;" in l)
    indice_sep_12 = linhas.index("Nove de Julho;1;12;1")
    indice_sep_16 = linhas.index("Nove de Julho;1;16;1")
    indice_santa_rita = next(i for i, l in enumerate(linhas) if "Santa Rita" in l)
    indice_sao_judas = next(i for i, l in enumerate(linhas) if "São Judas" in l)
    # os 2 separadores ficam logo apos o bloco do pedido1 (antes do pedido2 comecar)
    assert indice_sao_jose_16 < indice_sep_12 < indice_santa_rita
    assert indice_sao_jose_16 < indice_sep_16 < indice_santa_rita
    assert indice_sep_12 < indice_santa_rita < indice_sao_judas
    assert "Nove de Julho;1;29;1" not in linhas  # 29 nunca ganha separador


def test_csv_total_nao_separa_tamanho_29_mesmo_compartilhado(client, monkeypatch):
    _preparar_admin(monkeypatch)
    token1 = _criar_pedido(
        client, itens=[{"chave_preco": "chaveiro", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"}]
    )
    token2 = _criar_pedido(
        client, itens=[{"chave_preco": "chaveiro", "quantidade": 10, "produtoNome": "Santa Rita", "modeloNome": "Modelo 1"}]
    )
    resposta = client.post(
        "/admin/pedidos/csv-total", data={"tokens": [token1, token2]}, auth=("admin", "segredo123")
    )
    texto = resposta.data.decode("utf-8-sig")
    assert "Nove de Julho" not in texto


def test_csv_total_insere_separador_pra_cada_tamanho_compartilhado(client, monkeypatch):
    _preparar_admin(monkeypatch)
    token1 = _criar_pedido(
        client,
        itens=[
            {"chave_preco": "12mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"},
            {"chave_preco": "16mm", "quantidade": 10, "produtoNome": "São José", "modeloNome": "Modelo 1"},
        ],
    )
    token2 = _criar_pedido(
        client,
        itens=[
            {"chave_preco": "16mm", "quantidade": 10, "produtoNome": "Santa Rita", "modeloNome": "Modelo 1"},
            {"chave_preco": "12mm", "quantidade": 10, "produtoNome": "Santa Rita", "modeloNome": "Modelo 1"},
        ],
    )
    resposta = client.post(
        "/admin/pedidos/csv-total", data={"tokens": [token1, token2]}, auth=("admin", "segredo123")
    )
    linhas = resposta.data.decode("utf-8-sig").strip().splitlines()
    assert "Nove de Julho;1;12;1" in linhas
    assert "Nove de Julho;1;16;1" in linhas
    assert linhas.index("Nove de Julho;1;12;1") < linhas.index("Nove de Julho;1;16;1")


def test_csv_total_ignora_token_inexistente(client, monkeypatch):
    _preparar_admin(monkeypatch)
    token1 = _criar_pedido(client)
    resposta = client.post(
        "/admin/pedidos/csv-total", data={"tokens": [token1, "token-que-nao-existe"]}, auth=("admin", "segredo123")
    )
    assert resposta.status_code == 200
    linhas = resposta.data.decode("utf-8-sig").strip().splitlines()
    assert len(linhas) == 2  # cabecalho + 1 linha do pedido valido


# ---- Zip com personalizadas ----


def _criar_pedido_com_personalizada(client) -> str:
    token_imagem = imagens_personalizadas.salvar_imagem(b"fake-png-bytes", "image/png", "recorte.png", tipo="recorte")
    return _criar_pedido(
        client,
        itens=[{
            "chave_preco": "16mm", "quantidade": 10, "produtoNome": "Personalizada", "modeloNome": "Personalizada",
            "imagemRecorte": f"/imagem-personalizada/{token_imagem}",
        }],
    )


def test_zip_personalizadas_exige_autenticacao(client):
    resposta = client.post("/admin/pedidos/zip-personalizadas", data={"tokens": ["x"]})
    assert resposta.status_code == 401


def test_zip_personalizadas_sem_imagens_redireciona_sem_gerar_arquivo(client, monkeypatch):
    _preparar_admin(monkeypatch)
    token = _criar_pedido(client)  # pedido do catalogo, sem personalizada
    resposta = client.post(
        "/admin/pedidos/zip-personalizadas", data={"tokens": [token]}, auth=("admin", "segredo123")
    )
    assert resposta.status_code == 302


def test_zip_personalizadas_inclui_recortes_dos_pedidos_selecionados(client, monkeypatch):
    _preparar_admin(monkeypatch)
    token1 = _criar_pedido_com_personalizada(client)
    token2 = _criar_pedido_com_personalizada(client)
    resposta = client.post(
        "/admin/pedidos/zip-personalizadas", data={"tokens": [token1, token2]}, auth=("admin", "segredo123")
    )
    assert resposta.status_code == 200
    assert resposta.mimetype == "application/zip"
    arquivo = zipfile.ZipFile(io.BytesIO(resposta.data))
    nomes = sorted(arquivo.namelist())
    assert nomes == ["personalizada_modelo_1.png", "personalizada_modelo_2.png"]
    assert arquivo.read("personalizada_modelo_1.png") == b"fake-png-bytes"
