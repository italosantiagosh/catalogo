// Landing /liturgia-de-outubro: cadastra na mesma newsletter do rodape
// e MANDA POR E-MAIL os links de verdade (PDF + calendario), ver
// app.py:api_liturgia_inscrever -- so entao revela o link de download
// na propria pagina. O e-book em si nao tem protecao real (mesma
// logica do /catalogo.pdf, ja publico), o "gate" aqui e so nao deixar
// o botao de baixar visivel pra quem nao passou pelo formulario.
(function () {
  const form = document.getElementById('form-ebook-liturgia');
  if (!form) return;

  const campoEmail = document.getElementById('ebook-email');
  const feedback = document.getElementById('ebook-form-feedback');
  const botao = form.querySelector('button[type="submit"]');
  const blocoDownload = document.getElementById('ebook-download');

  // Pre-preenche o e-mail vindo do botao do convite por e-mail (ver
  // services/email.py:_corpo_html_convite_liturgia_mensal) -- a pessoa
  // ainda precisa clicar "Quero o e-book" aqui no site (nao inscreve
  // sozinho so por causa do link), so evita ter que redigitar.
  const parametros = new URLSearchParams(window.location.search);
  const emailPreenchido = parametros.get('email');
  if (emailPreenchido) {
    campoEmail.value = emailPreenchido;
  }

  function mostrarFeedback(texto, ehErro) {
    feedback.textContent = texto;
    feedback.hidden = false;
    feedback.classList.toggle('ebook-form-feedback-erro', !!ehErro);
  }

  form.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const email = campoEmail.value.trim();
    if (!email) return;

    botao.disabled = true;
    try {
      const resposta = await fetch('/api/liturgia/inscrever', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const dados = await resposta.json();
      if (resposta.ok) {
        rastrearEventoGA4('ebook_liturgia_lead', {});
        form.hidden = true;
        blocoDownload.hidden = false;
      } else {
        mostrarFeedback(dados.erro || 'Não foi possível agora, tenta de novo.', true);
      }
    } catch (e) {
      mostrarFeedback('Não foi possível agora, tenta de novo.', true);
    } finally {
      botao.disabled = false;
    }
  });
})();
