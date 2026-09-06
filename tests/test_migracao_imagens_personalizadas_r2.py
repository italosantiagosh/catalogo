from __future__ import annotations

import importlib

import pytest

import config
import services.imagens_personalizadas as imagens_personalizadas


@pytest.fixture
def db(monkeypatch, tmp_path):
    db_path = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(imagens_personalizadas, "DB_PATH", db_path)
    return db_path


class _R2Fake:
    def __init__(self):
        self.objetos: dict[str, bytes] = {}

    def subir(self, chave, dados, mimetype):
        self.objetos[chave] = dados


@pytest.fixture
def r2_fake_desligado(monkeypatch):
    """R2 comeca DESLIGADO (credenciais vazias) -- assim salvar_imagem
    guarda o BLOB de verdade no SQLite, simulando imagens de antes
    dessa integracao existir."""
    monkeypatch.setattr(config, "R2_ACCOUNT_ID", "")
    monkeypatch.setattr(config, "R2_ACCESS_KEY_ID", "")
    monkeypatch.setattr(config, "R2_SECRET_ACCESS_KEY", "")


def _importar_script(monkeypatch, fake: _R2Fake):
    import scripts.migrar_imagens_personalizadas_para_r2 as script
    importlib.reload(script)
    monkeypatch.setattr(script.armazenamento_r2, "configurado", lambda: True)
    monkeypatch.setattr(script.armazenamento_r2, "subir", fake.subir)
    return script


def test_migra_blob_local_pro_r2_e_esvazia_a_coluna(db, monkeypatch, r2_fake_desligado):
    token = imagens_personalizadas.salvar_imagem(b"conteudo-antigo", "image/png", "antiga.png")

    fake = _R2Fake()
    script = _importar_script(monkeypatch, fake)
    script.main()

    assert fake.objetos[token] == b"conteudo-antigo"
    with imagens_personalizadas._conexao() as conexao:
        linha = conexao.execute(
            "SELECT dados FROM imagens_personalizadas WHERE token = ?", (token,)
        ).fetchone()
    assert linha["dados"] == b""


def test_migracao_e_idempotente(db, monkeypatch, r2_fake_desligado):
    token = imagens_personalizadas.salvar_imagem(b"conteudo-antigo", "image/png", "antiga.png")

    fake = _R2Fake()
    script = _importar_script(monkeypatch, fake)
    script.main()
    script.main()  # roda de novo -- nao deve tentar subir de novo nem quebrar

    assert list(fake.objetos.keys()) == [token]


def test_sem_r2_configurado_nao_faz_nada(db, monkeypatch, r2_fake_desligado):
    imagens_personalizadas.salvar_imagem(b"conteudo-antigo", "image/png", "antiga.png")

    import scripts.migrar_imagens_personalizadas_para_r2 as script
    importlib.reload(script)
    script.main()  # armazenamento_r2.configurado() ainda False -- so imprime e sai

    with imagens_personalizadas._conexao() as conexao:
        linhas = conexao.execute("SELECT dados FROM imagens_personalizadas").fetchall()
    assert all(linha["dados"] != b"" for linha in linhas)
