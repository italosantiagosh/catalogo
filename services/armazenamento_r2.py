"""
Cliente fino pro Cloudflare R2 (compativel com a API S3) -- usado por
services/imagens_personalizadas.py pra guardar a previa e o recorte das
medalhas personalizadas fora do disco de 1GB do Render (ver conversa:
cliente que manda 20-40 fotos por pedido enchia o disco rapido, e a
decisao foi guardar tudo pra sempre em objeto externo em vez de apagar
depois de um tempo).

Sem as credenciais configuradas (R2_ACCOUNT_ID/ACCESS_KEY/SECRET em
config.py), `configurado()` devolve False e quem chama (services/
imagens_personalizadas.py) cai de volta pro BLOB no SQLite local --
assim continua funcionando em dev/teste sem precisar de conta nenhuma.
"""

from __future__ import annotations

import boto3
from botocore.config import Config

import config

_cliente_cache = None


def configurado() -> bool:
    return bool(config.R2_ACCOUNT_ID and config.R2_ACCESS_KEY_ID and config.R2_SECRET_ACCESS_KEY)


def _cliente():
    global _cliente_cache
    if _cliente_cache is None:
        _cliente_cache = boto3.client(
            "s3",
            endpoint_url=f"https://{config.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=config.R2_ACCESS_KEY_ID,
            aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _cliente_cache


def subir(chave: str, dados: bytes, mimetype: str) -> None:
    _cliente().put_object(Bucket=config.R2_BUCKET_NAME, Key=chave, Body=dados, ContentType=mimetype)


def baixar(chave: str) -> bytes:
    resposta = _cliente().get_object(Bucket=config.R2_BUCKET_NAME, Key=chave)
    return resposta["Body"].read()


def apagar(chaves: list[str]) -> None:
    """Apaga em lote (ate 1000 chaves por chamada, limite da API S3) --
    chave que nao existe no bucket e´ simplesmente ignorada, nao gera
    erro (seguro chamar mesmo pra token que nunca foi de fato subido
    pro R2, ex: linha antiga migrada so parcialmente)."""
    if not chaves:
        return
    cliente = _cliente()
    for inicio in range(0, len(chaves), 1000):
        lote = chaves[inicio:inicio + 1000]
        cliente.delete_objects(
            Bucket=config.R2_BUCKET_NAME, Delete={"Objects": [{"Key": chave} for chave in lote]}
        )
