from __future__ import annotations

from unittest.mock import patch

from services.liturgia_ics import gerar_ics_liturgia_outubro
from services.liturgia_pdf import DIAS_OUTUBRO_2026
from app import app


def test_gera_um_evento_por_dia_de_outubro():
    ics = gerar_ics_liturgia_outubro("https://lojanovedejulho.com.br")
    assert ics.count("BEGIN:VEVENT") == len(DIAS_OUTUBRO_2026) == 31
    assert ics.startswith("BEGIN:VCALENDAR\r\n")
    assert ics.rstrip().endswith("END:VCALENDAR")


def test_datas_de_inicio_e_fim_sao_dia_inteiro_consecutivo():
    ics = gerar_ics_liturgia_outubro("https://lojanovedejulho.com.br")
    assert "DTSTART;VALUE=DATE:20261001" in ics
    assert "DTEND;VALUE=DATE:20261002" in ics
    assert "DTSTART;VALUE=DATE:20261012" in ics
    assert "DTEND;VALUE=DATE:20261013" in ics


def _desdobrar(ics: str) -> str:
    """RFC 5545: linha de continuacao comeca com um espaco que precisa
    ser removido pra reconstituir o texto original antes de comparar
    substring (ver services/liturgia_ics.py:_dobrar_linha)."""
    return ics.replace("\r\n ", "")


def test_escapa_caracteres_especiais_da_descricao():
    ics = _desdobrar(gerar_ics_liturgia_outubro("https://lojanovedejulho.com.br"))
    assert "confiança simples" in ics
    assert "\\," in ics


def test_links_de_medalha_e_novena_aparecem_na_descricao():
    ics = _desdobrar(gerar_ics_liturgia_outubro("https://lojanovedejulho.com.br"))
    assert "https://lojanovedejulho.com.br/produto/santa-teresinha" in ics
    assert "https://lojanovedejulho.com.br/blog/novena-de-santa-teresinha" in ics


def test_titulo_do_evento_comeca_pelo_nome_nao_pelo_grau():
    """Ver conversa 2026-09-24: o app de calendario trunca o titulo na
    visao de mes -- "MEMÓRIA OBRIGATÓRIA..." cortado nao ajuda, o nome
    do santo precisa vir primeiro."""
    ics = _desdobrar(gerar_ics_liturgia_outubro("https://lojanovedejulho.com.br"))
    assert "SUMMARY:Santa Teresinha do Menino Jesus e da Sagrada Face (Memória obrigatória)" in ics
    assert "SUMMARY:Nossa Senhora Aparecida\\, padroeira do Brasil (Solenidade)" in ics


def test_cor_liturgica_aparece_na_descricao():
    ics = _desdobrar(gerar_ics_liturgia_outubro("https://lojanovedejulho.com.br"))
    assert "Cor litúrgica: Branco" in ics
    assert "Cor litúrgica: Vermelho" in ics
    assert "Cor litúrgica: Verde" in ics


def test_rota_ics_serve_com_content_type_correto():
    client = app.test_client()
    resposta = client.get("/ebook/liturgia-do-mes.ics")
    assert resposta.status_code == 200
    assert resposta.headers["Content-Type"] == "text/calendar; charset=utf-8"
    assert resposta.data.count(b"BEGIN:VEVENT") == 31


def test_landing_linka_direto_pro_ics_sem_o_truque_quebrado_do_google():
    """Ver conversa 2026-09-24: o link calendar.google.com/calendar/render
    ?cid=... deu erro no celular do usuario -- trocado pelo link direto
    pro .ics, que o proprio navegador/SO sabe abrir em qualquer app de
    calendario (Google, Apple, Outlook)."""
    resposta = app.test_client().get("/liturgia-do-mes")
    assert b"calendar.google.com/calendar/render" not in resposta.data
    assert b"/ebook/liturgia-do-mes.ics" in resposta.data


def test_api_liturgia_inscrever_inscreve_e_manda_o_ebook_por_email():
    """Ver conversa 2026-09-24: "fica o botão, mas não é enviado por
    e-mail" -- a inscricao pela landing agora tambem manda os links de
    verdade por e-mail, alem de revelar o botao na propria pagina."""
    client = app.test_client()
    with patch("app.inscrever_newsletter", return_value={"ok": True}) as mock_inscrever, \
         patch("app.enviar_ebook_liturgia_mensal", return_value={"ok": True}) as mock_email:
        resposta = client.post("/api/liturgia/inscrever", json={"email": "maria@example.com"})

    assert resposta.status_code == 200
    mock_inscrever.assert_called_once_with("maria@example.com")
    assert mock_email.call_count == 1
    args = mock_email.call_args.args
    assert args[0] == "maria@example.com"
    assert args[2].endswith("/ebook/liturgia-do-mes.pdf")
    assert args[3].endswith("/ebook/liturgia-do-mes.ics")


def test_api_liturgia_inscrever_nao_manda_email_se_inscricao_falhar():
    client = app.test_client()
    with patch("app.inscrever_newsletter", return_value={"erro": "E-mail inválido."}), \
         patch("app.enviar_ebook_liturgia_mensal") as mock_email:
        resposta = client.post("/api/liturgia/inscrever", json={"email": "invalido"})

    assert resposta.status_code == 400
    mock_email.assert_not_called()
