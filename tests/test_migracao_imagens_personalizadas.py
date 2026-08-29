from __future__ import annotations

import base64
import importlib

import pytest

import services.imagens_personalizadas as imagens_personalizadas
import services.pedidos as pedidos


@pytest.fixture
def db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(pedidos, "DB_PATH", db_path)
    monkeypatch.setattr(imagens_personalizadas, "DB_PATH", db_path)
    return db_path


def _corpo_valido(**overrides):
    base = dict(
        subtotal=5.0, frete_descricao="PAC", frete_preco=10.0,
        cliente={"nome": "Maria", "tipo_pessoa": "fisica", "documento": "11144477735",
                 "telefone": "84999999999", "email": "a@a.com"},
        endereco={"cep": "59000000", "logradouro": "Rua", "numero": "1", "complemento": "",
                  "bairro": "C", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def _importar_script(db_path, monkeypatch):
    monkeypatch.setenv("PEDIDOS_DB_PATH", db_path)
    import scripts.migrar_imagens_personalizadas_antigas as script
    importlib.reload(script)
    return script


def test_migra_pedido_com_data_uri_para_url_duravel(db, monkeypatch):
    dados_originais = b"conteudo-fake-png"
    data_uri = f"data:image/png;base64,{base64.b64encode(dados_originais).decode()}"

    criado = pedidos.criar_pedido(
        itens=[{"chave_preco": "16mm", "quantidade": 1, "descricao": "Personalizada",
                "imagem": data_uri, "imagemRecorte": data_uri}],
        **_corpo_valido(),
    )

    script = _importar_script(db, monkeypatch)
    script.main()

    migrado = pedidos.obter_pedido(criado["token"])
    item = migrado["itens"][0]
    assert item["imagem"].startswith("/imagem-personalizada/")
    assert item["imagemRecorte"].startswith("/imagem-personalizada/")

    token_recorte = item["imagemRecorte"].rsplit("/", 1)[-1]
    dados, mimetype, _nome = imagens_personalizadas.obter_imagem(token_recorte)
    assert dados == dados_originais
    assert mimetype == "image/png"


def test_migracao_e_idempotente(db, monkeypatch):
    data_uri = f"data:image/png;base64,{base64.b64encode(b'x').decode()}"
    criado = pedidos.criar_pedido(
        itens=[{"chave_preco": "16mm", "quantidade": 1, "descricao": "Personalizada",
                "imagem": data_uri, "imagemRecorte": data_uri}],
        **_corpo_valido(),
    )
    script = _importar_script(db, monkeypatch)
    script.main()
    url_apos_primeira = pedidos.obter_pedido(criado["token"])["itens"][0]["imagemRecorte"]

    script.main()
    url_apos_segunda = pedidos.obter_pedido(criado["token"])["itens"][0]["imagemRecorte"]
    assert url_apos_primeira == url_apos_segunda


def test_nao_mexe_em_pedido_sem_foto(db, monkeypatch):
    criado = pedidos.criar_pedido(
        itens=[{"chave_preco": "16mm", "quantidade": 1, "descricao": "São José — Modelo 1"}],
        **_corpo_valido(),
    )
    script = _importar_script(db, monkeypatch)
    script.main()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["itens"][0].get("imagem", "") == ""
