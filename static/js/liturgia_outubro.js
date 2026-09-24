// Landing /liturgia-de-outubro: cadastra na mesma newsletter do rodape
// (ver app.py:api_newsletter) e so revela o link de download do PDF
// depois do cadastro dar certo -- o e-book em si nao tem protecao real
// (mesma logica do /catalogo.pdf, ja publico), o "gate" aqui e so nao
// deixar o botao de baixar visivel pra quem nao passou pelo formulario.
(function () {
  const form = document.getElementById('form-ebook-liturgia');
  if (!form) return;

  const campoEmail = document.getElementById('ebook-email');
  const feedback = document.getElementById('ebook-form-feedback');
  const botao = form.querySelector('button[type="submit"]');
  const blocoDownload = document.getElementById('ebook-download');

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
      const resposta = await fetch('/api/newsletter', {
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
