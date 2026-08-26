from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from webpush.vapid import VAPID

import services.push as push
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(push, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _preparar_admin(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASSWORD", "segredo123")


def _chaves_vapid_de_teste():
    priv_pem, pub_pem, _ = VAPID.generate_keys()
    return priv_pem.decode(), pub_pem.decode()


def test_sw_js_servido_na_raiz(client):
    resposta = client.get("/sw.js")
    assert resposta.status_code == 200
    assert "self.addEventListener('push'" in resposta.get_data(as_text=True)


def test_inscrever_exige_autenticacao(client):
    resposta = client.post("/admin/push/inscrever", json={"endpoint": "https://x", "keys": {"p256dh": "a", "auth": "b"}})
    assert resposta.status_code == 401


def test_inscrever_salva_subscription(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post(
        "/admin/push/inscrever",
        json={"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": {"p256dh": "chave-p256dh", "auth": "chave-auth"}},
        auth=("admin", "segredo123"),
    )
    assert resposta.status_code == 200
    inscricoes = push.listar_subscriptions()
    assert len(inscricoes) == 1
    assert inscricoes[0]["endpoint"] == "https://fcm.googleapis.com/fcm/send/abc"


def test_inscrever_dados_invalidos_400(client, monkeypatch):
    _preparar_admin(monkeypatch)
    resposta = client.post("/admin/push/inscrever", json={"endpoint": ""}, auth=("admin", "segredo123"))
    assert resposta.status_code == 400


def test_desinscrever_remove_subscription(client, monkeypatch):
    _preparar_admin(monkeypatch)
    client.post(
        "/admin/push/inscrever",
        json={"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": {"p256dh": "a", "auth": "b"}},
        auth=("admin", "segredo123"),
    )
    assert len(push.listar_subscriptions()) == 1

    resposta = client.post(
        "/admin/push/desinscrever", json={"endpoint": "https://fcm.googleapis.com/fcm/send/abc"}, auth=("admin", "segredo123")
    )
    assert resposta.status_code == 200
    assert len(push.listar_subscriptions()) == 0


def test_enviar_notificacao_sem_vapid_nao_faz_nada(client, monkeypatch):
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY_PEM", "")
    monkeypatch.setattr(push, "VAPID_PUBLIC_KEY_PEM", "")
    push.salvar_subscription(endpoint="https://x", p256dh="a", auth="b")
    with patch("services.push.requests.post") as mock_post:
        push.enviar_notificacao(titulo="Teste", corpo="Corpo", url="https://x/y")
    mock_post.assert_not_called()


def test_enviar_notificacao_manda_pra_todas_as_inscricoes(client, monkeypatch):
    priv_pem, pub_pem = _chaves_vapid_de_teste()
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY_PEM", priv_pem)
    monkeypatch.setattr(push, "VAPID_PUBLIC_KEY_PEM", pub_pem)
    monkeypatch.setattr(push, "VAPID_SUBSCRIBER_EMAIL", "loja@example.com")

    # duas inscricoes com chaves de cliente validas (par EC real) --
    # senao a criptografia real da lib rejeita a chave publica
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    import base64

    def _p256dh_valido():
        chave = ec.generate_private_key(ec.SECP256R1())
        bruto = chave.public_key().public_bytes(
            encoding=serialization.Encoding.X962, format=serialization.PublicFormat.UncompressedPoint
        )
        return base64.urlsafe_b64encode(bruto).decode().rstrip("=")

    auth = base64.urlsafe_b64encode(b"0123456789abcdef").decode().rstrip("=")
    push.salvar_subscription(endpoint="https://fcm.googleapis.com/fcm/send/1", p256dh=_p256dh_valido(), auth=auth)
    push.salvar_subscription(endpoint="https://fcm.googleapis.com/fcm/send/2", p256dh=_p256dh_valido(), auth=auth)

    resposta_ok = Mock(status_code=201)
    with patch("services.push.requests.post", return_value=resposta_ok) as mock_post:
        push.enviar_notificacao(titulo="🎉 Nova venda!", corpo="Pedido #ABC123", url="https://site/admin/x")

    assert mock_post.call_count == 2
    for chamada in mock_post.call_args_list:
        assert chamada.kwargs["headers"]["content-encoding"] == "aes128gcm"


def test_enviar_notificacao_remove_inscricao_expirada(client, monkeypatch):
    priv_pem, pub_pem = _chaves_vapid_de_teste()
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY_PEM", priv_pem)
    monkeypatch.setattr(push, "VAPID_PUBLIC_KEY_PEM", pub_pem)
    monkeypatch.setattr(push, "VAPID_SUBSCRIBER_EMAIL", "loja@example.com")

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    import base64

    chave = ec.generate_private_key(ec.SECP256R1())
    bruto = chave.public_key().public_bytes(
        encoding=serialization.Encoding.X962, format=serialization.PublicFormat.UncompressedPoint
    )
    p256dh = base64.urlsafe_b64encode(bruto).decode().rstrip("=")
    auth = base64.urlsafe_b64encode(b"0123456789abcdef").decode().rstrip("=")
    push.salvar_subscription(endpoint="https://fcm.googleapis.com/fcm/send/expirada", p256dh=p256dh, auth=auth)

    resposta_410 = Mock(status_code=410)
    with patch("services.push.requests.post", return_value=resposta_410):
        push.enviar_notificacao(titulo="Teste", corpo="Corpo", url="https://x/y")

    assert push.listar_subscriptions() == []


def test_admin_pedidos_mostra_botao_so_com_vapid_configurado(client, monkeypatch):
    _preparar_admin(monkeypatch)

    monkeypatch.setattr(push, "VAPID_PUBLIC_KEY_PEM", "")
    corpo_sem = client.get("/admin/pedidos", auth=("admin", "segredo123")).get_data(as_text=True)
    assert 'id="btn-ativar-notificacoes"' not in corpo_sem

    _, pub_pem = _chaves_vapid_de_teste()
    monkeypatch.setattr(push, "VAPID_PUBLIC_KEY_PEM", pub_pem)
    corpo_com = client.get("/admin/pedidos", auth=("admin", "segredo123")).get_data(as_text=True)
    assert 'id="btn-ativar-notificacoes"' in corpo_com
