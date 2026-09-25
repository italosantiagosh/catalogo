// Comportamento COMPARTILHADO das paginas de "peca exclusiva do varejo"
// (colares.html/colares.js, pulseiras.html/pulseiras.js -- ver conversa
// 2026-09-25: "não tem como fazer no mesmo estilo [da Parresia]...
// sendo que melhor") -- carrossel de fotos com bolinhas, zoom ao tocar
// na foto, e o formulario de avaliacao (pode ter mais de uma peca por
// pagina no futuro -- Nossa Senhora/Sao Jose ainda pendentes de foto,
// ver services/colares.py -- por isso tudo aqui usa querySelectorAll
// em vez de getElementById, ao contrario do avaliacoes.js generico
// (que so espera 1 formulario por pagina, ver templates/produto.html).
(function () {
  // ---- carrossel: bolinha ativa acompanha o scroll, toque na bolinha rola ----
  document.querySelectorAll('[data-peca-carrossel]').forEach((carrossel) => {
    const trilho = carrossel.querySelector('.peca-carrossel-trilho');
    const pontos = carrossel.querySelectorAll('.ponto');
    if (!trilho || pontos.length === 0) return;

    trilho.addEventListener('scroll', () => {
      const indice = Math.round(trilho.scrollLeft / trilho.clientWidth);
      pontos.forEach((ponto, i) => ponto.classList.toggle('ativo', i === indice));
    });

    pontos.forEach((ponto, i) => {
      ponto.addEventListener('click', () => {
        trilho.scrollTo({ left: trilho.clientWidth * i, behavior: 'smooth' });
      });
    });
  });

  // ---- zoom: toca na foto, abre maior no mesmo modal usado nos avisos do carrinho ----
  const zoomModal = document.getElementById('peca-zoom-modal');
  const zoomImg = document.getElementById('peca-zoom-img');
  const zoomFechar = document.getElementById('peca-zoom-fechar');
  if (zoomModal && zoomImg) {
    document.querySelectorAll('[data-peca-zoom]').forEach((img) => {
      img.addEventListener('click', () => {
        zoomImg.src = img.src;
        zoomImg.alt = img.alt;
        zoomModal.hidden = false;
      });
    });
    const fecharZoom = () => { zoomModal.hidden = true; };
    if (zoomFechar) zoomFechar.addEventListener('click', fecharZoom);
    zoomModal.addEventListener('click', (evento) => {
      if (evento.target === zoomModal) fecharZoom();
    });
  }

  // ---- avaliacao: mesma logica do static/js/avaliacoes.js, so que pra
  // varios formularios na mesma pagina (um por peca) em vez de 1 so ----
  document.querySelectorAll('.btn-abrir-avaliacao').forEach((botaoAbrir) => {
    botaoAbrir.addEventListener('click', () => {
      const form = document.getElementById(botaoAbrir.dataset.alvo);
      if (!form) return;
      form.hidden = false;
      botaoAbrir.hidden = true;
    });
  });

  document.querySelectorAll('[data-peca-avaliacao]').forEach((form) => {
    const estrelasWrap = form.querySelector('.aval-estrelas-input');
    const notaInput = form.querySelector('input[name="nota"]');
    const erroEl = form.querySelector('.erro');
    const btnEnviar = form.querySelector('button[type="submit"]');
    const inputFoto = form.querySelector('input[type="file"]');
    const nomeArquivoDiv = form.querySelector('.aval-nome-arquivo');
    const sucessoEl = form.nextElementSibling;

    if (inputFoto && nomeArquivoDiv) {
      inputFoto.addEventListener('change', () => {
        nomeArquivoDiv.textContent = inputFoto.files.length > 0 ? inputFoto.files[0].name : '';
      });
    }

    if (estrelasWrap) {
      estrelasWrap.querySelectorAll('button').forEach((botao) => {
        botao.addEventListener('click', () => {
          const nota = botao.dataset.nota;
          notaInput.value = nota;
          estrelasWrap.querySelectorAll('button').forEach((b) => {
            b.classList.toggle('ativa', Number(b.dataset.nota) <= Number(nota));
          });
        });
      });
    }

    form.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      if (erroEl) erroEl.hidden = true;

      if (!notaInput.value) {
        if (erroEl) {
          erroEl.hidden = false;
          erroEl.textContent = 'Escolha uma nota de 1 a 5 estrelas.';
        }
        return;
      }

      btnEnviar.disabled = true;
      const textoOriginalBtn = btnEnviar.textContent;
      btnEnviar.textContent = 'Enviando...';
      try {
        const dados = new FormData(form);
        const resposta = await fetch('/api/avaliacoes', { method: 'POST', body: dados });
        const corpo = await resposta.json();
        if (!resposta.ok || corpo.erro) {
          if (erroEl) {
            erroEl.hidden = false;
            erroEl.textContent = corpo.erro || 'Não foi possível enviar sua avaliação agora.';
          }
          return;
        }
        form.hidden = true;
        if (sucessoEl && sucessoEl.classList.contains('aval-sucesso')) sucessoEl.hidden = false;
      } catch (e) {
        if (erroEl) {
          erroEl.hidden = false;
          erroEl.textContent = 'Não foi possível enviar sua avaliação agora.';
        }
      } finally {
        btnEnviar.disabled = false;
        btnEnviar.textContent = textoOriginalBtn;
      }
    });
  });
})();
