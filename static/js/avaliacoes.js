(function () {
  const form = document.getElementById('form-avaliacao');
  if (!form) return;

  const btnAbrir = document.getElementById('btn-abrir-avaliacao');
  const estrelasWrap = document.getElementById('aval-estrelas');
  const notaInput = document.getElementById('aval-nota');
  const erroEl = document.getElementById('aval-erro');
  const sucessoEl = document.getElementById('aval-sucesso');
  const btnEnviar = document.getElementById('btn-enviar-avaliacao');

  btnAbrir.addEventListener('click', () => {
    form.hidden = false;
    btnAbrir.hidden = true;
  });

  estrelasWrap.querySelectorAll('button').forEach((botao) => {
    botao.addEventListener('click', () => {
      const nota = botao.dataset.nota;
      notaInput.value = nota;
      estrelasWrap.querySelectorAll('button').forEach((b) => {
        b.classList.toggle('ativa', Number(b.dataset.nota) <= Number(nota));
      });
    });
  });

  form.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    erroEl.hidden = true;

    if (!notaInput.value) {
      erroEl.hidden = false;
      erroEl.textContent = 'Escolha uma nota de 1 a 5 estrelas.';
      return;
    }

    btnEnviar.disabled = true;
    btnEnviar.textContent = 'Enviando...';
    try {
      const dados = new FormData(form);
      const resposta = await fetch('/api/avaliacoes', { method: 'POST', body: dados });
      const corpo = await resposta.json();
      if (!resposta.ok || corpo.erro) {
        erroEl.hidden = false;
        erroEl.textContent = corpo.erro || 'Não foi possível enviar sua avaliação agora.';
        return;
      }
      form.hidden = true;
      sucessoEl.hidden = false;
    } catch (e) {
      erroEl.hidden = false;
      erroEl.textContent = 'Não foi possível enviar sua avaliação agora.';
    } finally {
      btnEnviar.disabled = false;
      btnEnviar.textContent = 'Enviar avaliação';
    }
  });
})();
