from __future__ import annotations

import pytest

import services.pedidos as pedidos
from app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(pedidos, "DB_PATH", str(tmp_path / "pedidos.db"))
    app.config["TESTING"] = True
    return app.test_client()


def _criar_pedido_para(documento: str, email: str = "maria@example.com") -> dict:
    return pedidos.criar_pedido(
        itens=[{"chave_preco": "16mm", "quantidade": 10, "descricao": "São José — Modelo 1"}],
        subtotal=50.0,
        frete_descricao="Correios PAC — R$ 10,00",
        frete_preco=10.0,
        cliente={"nome": "Maria Teste", "tipo_pessoa": "fisica", "documento": documento,
                 "telefone": "84999999999", "email": email},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )


def test_meus_pedidos_mostra_formulario_de_cpf_por_padrao(client):
    resposta = client.get("/meus-pedidos")
    assert resposta.status_code == 200
    assert b"Seu CPF" in resposta.data


def test_enviar_codigo_com_cpf_invalido_volta_pro_formulario_com_erro(client):
    resposta = client.post("/meus-pedidos/enviar-codigo", data={"documento": "123"}, follow_redirects=True)
    assert resposta.status_code == 200
    assert "inválido".encode() in resposta.data or "invalido".encode() in resposta.data


def test_fluxo_completo_cpf_codigo_lista_e_sair(client, monkeypatch):
    monkeypatch.setattr(pedidos.secrets, "randbelow", lambda n: 123456)
    pedido = _criar_pedido_para("111.444.777-35")

    resposta = client.post(
        "/meus-pedidos/enviar-codigo", data={"documento": "111.444.777-35"}, follow_redirects=True
    )
    assert resposta.status_code == 200
    assert b"6 d\xc3\xadgitos" in resposta.data or b"codigo" in resposta.data.lower()

    # codigo errado -- continua pedindo o codigo, com aviso de erro
    errado = client.post("/meus-pedidos/verificar", data={"codigo": "000000"}, follow_redirects=True)
    assert errado.status_code == 200
    assert "incorreto".encode() in errado.data or "vencido".encode() in errado.data

    certo = client.post("/meus-pedidos/verificar", data={"codigo": "123456"}, follow_redirects=True)
    assert certo.status_code == 200
    assert pedido["codigo"].encode() in certo.data

    # sessao verificada -- recarregar a pagina mostra a lista direto
    de_novo = client.get("/meus-pedidos")
    assert pedido["codigo"].encode() in de_novo.data

    sair = client.post("/meus-pedidos/sair", follow_redirects=True)
    assert b"Seu CPF" in sair.data


def test_verificar_sem_pedido_de_codigo_pendente_volta_pro_formulario(client):
    resposta = client.post("/meus-pedidos/verificar", data={"codigo": "123456"}, follow_redirects=True)
    assert resposta.status_code == 200
    assert b"Seu CPF" in resposta.data


def test_cpf_sem_pedido_nenhum_nao_revela_isso_na_resposta(client):
    """CPF matematicamente valido mas que nunca comprou nada -- a resposta
    tem que ser IGUAL a de um CPF que comprou (sempre segue pro passo do
    codigo), senao da pra usar esse formulario pra descobrir se alguem
    e´ cliente daqui so tentando o CPF da pessoa."""
    resposta = client.post(
        "/meus-pedidos/enviar-codigo", data={"documento": "111.444.777-35"}, follow_redirects=True
    )
    assert resposta.status_code == 200
    assert b"Seu CPF" not in resposta.data
    assert b"c\xc3\xb3digo" in resposta.data.lower() or b"codigo" in resposta.data.lower()
