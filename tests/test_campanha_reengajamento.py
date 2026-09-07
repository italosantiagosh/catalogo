from __future__ import annotations

import services.campanha_reengajamento as campanha
import services.pedidos as pedidos


def _isolar_db(monkeypatch, tmp_path):
    caminho = str(tmp_path / "pedidos.db")
    monkeypatch.setattr(pedidos, "DB_PATH", caminho)
    monkeypatch.setattr(campanha, "DB_PATH", caminho)


def test_email_valido():
    assert campanha.email_valido("maria@example.com")
    assert not campanha.email_valido("")
    assert not campanha.email_valido("sem-arroba")
    assert not campanha.email_valido("sem-dominio@")


def test_importa_e_dedupe_por_email(monkeypatch, tmp_path):
    _isolar_db(monkeypatch, tmp_path)
    resultado = campanha.importar_contatos(
        [
            {"nome": "Maria Silva", "email": "MARIA@example.com"},
            {"nome": "Maria da Silva", "email": "maria@example.com"},  # mesmo e-mail, so caixa diferente
            {"nome": "João Souza", "email": "joao@example.com"},
            {"nome": "Sem e-mail", "email": ""},
        ]
    )
    assert resultado == {
        "recebidos": 4,
        "invalidos": 1,
        "unicos": 2,
        "ja_e_cliente_site_novo": 0,
        "novos_candidatos": 2,
    }
    pendentes = {c["email"]: c["nome"] for c in campanha.listar_pendentes(10)}
    assert pendentes == {"maria@example.com": "Maria da Silva", "joao@example.com": "João Souza"}


def test_ignora_quem_ja_comprou_no_site_novo(monkeypatch, tmp_path):
    _isolar_db(monkeypatch, tmp_path)
    pedidos.criar_pedido(
        itens=[{"chave_preco": "16mm", "quantidade": 10}],
        subtotal=50.0,
        frete_descricao="Correios PAC",
        frete_preco=10.0,
        cliente={"nome": "Maria Cliente", "tipo_pessoa": "fisica", "documento": "11144477735",
                 "telefone": "84999999999", "email": "maria@example.com"},
        endereco={"cep": "59000000", "logradouro": "Rua Teste", "numero": "100", "complemento": "",
                  "bairro": "Centro", "cidade": "Natal", "uf": "RN"},
    )

    resultado = campanha.importar_contatos(
        [
            {"nome": "Maria Silva", "email": "maria@example.com"},  # ja e cliente do site novo
            {"nome": "João Souza", "email": "joao@example.com"},
        ]
    )
    assert resultado["ja_e_cliente_site_novo"] == 1
    assert resultado["novos_candidatos"] == 1
    pendentes = [c["email"] for c in campanha.listar_pendentes(10)]
    assert pendentes == ["joao@example.com"]


def test_reimportar_a_mesma_planilha_nao_duplica_nem_reseta_status(monkeypatch, tmp_path):
    _isolar_db(monkeypatch, tmp_path)
    contatos = [{"nome": "Maria Silva", "email": "maria@example.com"}]
    campanha.importar_contatos(contatos)
    campanha.marcar_enviado("maria@example.com", erro=None)

    resultado = campanha.importar_contatos(contatos)
    assert resultado["novos_candidatos"] == 0  # ja existia, INSERT OR IGNORE nao mexeu
    assert campanha.contagem_por_status() == {"pendente": 0, "enviado": 1, "erro": 0}


def test_marcar_enviado_com_erro(monkeypatch, tmp_path):
    _isolar_db(monkeypatch, tmp_path)
    campanha.importar_contatos([{"nome": "Maria Silva", "email": "maria@example.com"}])
    campanha.marcar_enviado("maria@example.com", erro="Não foi possível enviar o e-mail agora.")
    assert campanha.contagem_por_status() == {"pendente": 0, "enviado": 0, "erro": 1}


def test_listar_pendentes_respeita_o_limite(monkeypatch, tmp_path):
    _isolar_db(monkeypatch, tmp_path)
    campanha.importar_contatos([{"nome": f"Cliente {i}", "email": f"cliente{i}@example.com"} for i in range(5)])
    assert len(campanha.listar_pendentes(2)) == 2
    assert len(campanha.listar_pendentes(10)) == 5
