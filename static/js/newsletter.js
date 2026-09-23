// Inscricao na newsletter do rodape (novenas, historias de santos,
// produtos novos e novidades -- ver templates/base.html e
// app.py:api_newsletter). So existe um formulario, no rodape, presente
// em toda pagina -- entao nao precisa de guarda de "elemento nao
// existe" alem do basico.
(function () {
  const form = document.getElementById('form-newsletter');
  if (!form) return;

  const campoEmail = document.getElementById('newsletter-email');
  const feedback = document.getElementById('newsletter-feedback');
  const botao = form.querySelector('button[type="submit"]');

  function mostrarFeedback(texto, ehErro) {
    feedback.textContent = texto;
    feedback.hidden = false;
    feedback.classList.toggle('rodape-newsletter-feedback-erro', !!ehErro);
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
        mostrarFeedback('Inscrito! Já vai começar a receber nossos e-mails. ✝️', false);
        rastrearEventoGA4('newsletter_inscricao', {});
        form.reset();
      } else {
        mostrarFeedback(dados.erro || 'Não foi possível inscrever agora, tenta de novo.', true);
      }
    } catch (e) {
      mostrarFeedback('Não foi possível inscrever agora, tenta de novo.', true);
    } finally {
      botao.disabled = false;
    }
  });
})();
