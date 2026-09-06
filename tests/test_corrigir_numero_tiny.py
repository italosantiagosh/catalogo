from __future__ import annotations

import importlib

import pytest

import services.pedidos as pedidos


@pytest.fixture
def db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(pedidos, "DB_PATH", db_path)
    return db_path


def _pedido_exemplo(**overrides):
    base = dict(
        itens=[{"chave_preco": "16mm", "quantidade": 1, "descricao": "São José — Modelo 1"}],
        subtotal=60.0, frete_descricao="Loggi", frete_preco=10.0,
        cliente={"nome": "Cliente", "tipo_pessoa": "fisica", "documento": "11144477735",
                 "telefone": "84999999999", "email": "a@a.com"},
        endereco={"cep": "59000000", "logradouro": "Rua", "numero": "1", "complemento": "",
                  "bairro": "C", "cidade": "Natal", "uf": "RN"},
    )
    base.update(overrides)
    return base


def _importar_script(db_path, monkeypatch):
    monkeypatch.setenv("PEDIDOS_DB_PATH", db_path)
    import scripts.corrigir_numero_tiny as script
    importlib.reload(script)
    return script


def test_corrige_numero_tiny_do_pedido(db, monkeypatch, capsys):
    criado = pedidos.criar_pedido(**_pedido_exemplo())
    pedidos.marcar_tiny_sincronizado(criado["token"], numero_pedido="1140", erro=None)

    script = _importar_script(db, monkeypatch)
    monkeypatch.setattr("sys.argv", ["corrigir_numero_tiny.py", criado["codigo"], "1119"])
    script.main()

    pedido = pedidos.obter_pedido(criado["token"])
    assert pedido["tiny_numero_pedido"] == "1119"
    assert pedido["tiny_erro"] is None
    assert "1140" in capsys.readouterr().out


def test_codigo_inexistente_nao_quebra(db, monkeypatch, capsys):
    pedidos.inicializar_db()
    script = _importar_script(db, monkeypatch)
    monkeypatch.setattr("sys.argv", ["corrigir_numero_tiny.py", "NAOEXISTE", "1119"])
    with pytest.raises(SystemExit):
        script.main()
    assert "Nenhum pedido encontrado" in capsys.readouterr().out


def test_uso_incorreto_mostra_ajuda(db, monkeypatch, capsys):
    script = _importar_script(db, monkeypatch)
    monkeypatch.setattr("sys.argv", ["corrigir_numero_tiny.py"])
    with pytest.raises(SystemExit):
        script.main()
    assert "Uso:" in capsys.readouterr().out
