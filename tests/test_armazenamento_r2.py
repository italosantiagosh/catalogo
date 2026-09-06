from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import config
import services.armazenamento_r2 as armazenamento_r2


@pytest.fixture(autouse=True)
def _resetar_cliente_cache():
    """O cliente boto3 fica em cache no modulo (_cliente_cache) -- reseta
    entre testes pra cada teste poder mockar boto3.client de novo sem
    pegar o cliente de um teste anterior."""
    armazenamento_r2._cliente_cache = None
    yield
    armazenamento_r2._cliente_cache = None


def test_configurado_falso_sem_credenciais(monkeypatch):
    monkeypatch.setattr(config, "R2_ACCOUNT_ID", "")
    monkeypatch.setattr(config, "R2_ACCESS_KEY_ID", "")
    monkeypatch.setattr(config, "R2_SECRET_ACCESS_KEY", "")
    assert armazenamento_r2.configurado() is False


def test_configurado_verdadeiro_com_credenciais(monkeypatch):
    monkeypatch.setattr(config, "R2_ACCOUNT_ID", "conta123")
    monkeypatch.setattr(config, "R2_ACCESS_KEY_ID", "chave")
    monkeypatch.setattr(config, "R2_SECRET_ACCESS_KEY", "segredo")
    assert armazenamento_r2.configurado() is True


def test_subir_chama_put_object_com_bucket_e_content_type(monkeypatch):
    monkeypatch.setattr(config, "R2_ACCOUNT_ID", "conta123")
    monkeypatch.setattr(config, "R2_ACCESS_KEY_ID", "chave")
    monkeypatch.setattr(config, "R2_SECRET_ACCESS_KEY", "segredo")
    monkeypatch.setattr(config, "R2_BUCKET_NAME", "meu-bucket")

    cliente_fake = MagicMock()
    with patch("boto3.client", return_value=cliente_fake) as boto3_client:
        armazenamento_r2.subir("token-1", b"conteudo", "image/png")

    boto3_client.assert_called_once()
    assert boto3_client.call_args.args[0] == "s3"
    assert boto3_client.call_args.kwargs["endpoint_url"] == "https://conta123.r2.cloudflarestorage.com"
    cliente_fake.put_object.assert_called_once_with(
        Bucket="meu-bucket", Key="token-1", Body=b"conteudo", ContentType="image/png"
    )


def test_baixar_devolve_bytes_do_body(monkeypatch):
    monkeypatch.setattr(config, "R2_ACCOUNT_ID", "conta123")
    monkeypatch.setattr(config, "R2_ACCESS_KEY_ID", "chave")
    monkeypatch.setattr(config, "R2_SECRET_ACCESS_KEY", "segredo")
    monkeypatch.setattr(config, "R2_BUCKET_NAME", "meu-bucket")

    cliente_fake = MagicMock()
    cliente_fake.get_object.return_value = {"Body": MagicMock(read=lambda: b"dados-baixados")}
    with patch("boto3.client", return_value=cliente_fake):
        resultado = armazenamento_r2.baixar("token-1")

    assert resultado == b"dados-baixados"
    cliente_fake.get_object.assert_called_once_with(Bucket="meu-bucket", Key="token-1")


def test_apagar_lista_vazia_nao_chama_cliente(monkeypatch):
    with patch("boto3.client") as boto3_client:
        armazenamento_r2.apagar([])
    boto3_client.assert_not_called()


def test_apagar_chama_delete_objects_em_lotes_de_mil(monkeypatch):
    monkeypatch.setattr(config, "R2_ACCOUNT_ID", "conta123")
    monkeypatch.setattr(config, "R2_ACCESS_KEY_ID", "chave")
    monkeypatch.setattr(config, "R2_SECRET_ACCESS_KEY", "segredo")
    monkeypatch.setattr(config, "R2_BUCKET_NAME", "meu-bucket")

    cliente_fake = MagicMock()
    chaves = [f"token-{i}" for i in range(1500)]
    with patch("boto3.client", return_value=cliente_fake):
        armazenamento_r2.apagar(chaves)

    assert cliente_fake.delete_objects.call_count == 2
    primeiro_lote = cliente_fake.delete_objects.call_args_list[0].kwargs["Delete"]["Objects"]
    assert len(primeiro_lote) == 1000
    segundo_lote = cliente_fake.delete_objects.call_args_list[1].kwargs["Delete"]["Objects"]
    assert len(segundo_lote) == 500
