(function () {
  // Carrossel de 3 slides do banner principal da home (ver conversa
  // 2026-09-22) -- so existe na home, entao no-op silencioso se o
  // elemento nao estiver na pagina. Troca automatica a cada 6s, pausa
  // ao passar o mouse/focar (pra nao trocar embaixo de quem ta lendo
  // ou navegando por teclado), e os pontinhos deixam pular pra um
  // slide especifico na hora. Slides NAO sao clicaveis (so imagem +
  // texto, sem link) -- a navegacao de verdade e´ a linha de botoes
  // reais logo abaixo (.hero-acoes-linha).
  //
  // Deslizar no celular (touchstart/touchend, ver conversa) troca de
  // slide com LOOP nos dois sentidos: deslizar pra esquerda no ultimo
  // slide volta pro primeiro, deslizar pra direita no primeiro vai pro
  // ultimo -- mesmo espirito do "proximo"/"%" abaixo, so que pro lado
  // contrario tambem.
  const wrap = document.querySelector('[data-hero-carrossel]');
  if (!wrap) return;

  const slides = Array.from(wrap.querySelectorAll('.hero-slide'));
  const dots = Array.from(wrap.querySelectorAll('.hero-dot'));
  if (slides.length < 2) return;

  const INTERVALO_MS = 6000;
  let indiceAtual = 0;
  let timer = null;

  function mostrar(indice) {
    slides[indiceAtual].classList.remove('hero-slide-ativo');
    dots[indiceAtual]?.classList.remove('hero-dot-ativo');
    dots[indiceAtual]?.removeAttribute('aria-current');
    indiceAtual = indice;
    slides[indiceAtual].classList.add('hero-slide-ativo');
    dots[indiceAtual]?.classList.add('hero-dot-ativo');
    dots[indiceAtual]?.setAttribute('aria-current', 'true');
  }

  function proximo() {
    mostrar((indiceAtual + 1) % slides.length);
  }

  function anterior() {
    mostrar((indiceAtual - 1 + slides.length) % slides.length);
  }

  function iniciarAutoplay() {
    parar();
    timer = setInterval(proximo, INTERVALO_MS);
  }

  function parar() {
    if (timer) clearInterval(timer);
    timer = null;
  }

  dots.forEach((dot, indice) => {
    dot.addEventListener('click', () => {
      mostrar(indice);
      iniciarAutoplay();
    });
  });

  wrap.addEventListener('mouseenter', parar);
  wrap.addEventListener('mouseleave', iniciarAutoplay);
  wrap.addEventListener('focusin', parar);
  wrap.addEventListener('focusout', iniciarAutoplay);

  const LIMIAR_DESLIZE_PX = 40;
  let inicioX = null;

  wrap.addEventListener('touchstart', (evento) => {
    inicioX = evento.touches[0].clientX;
    parar();
  }, { passive: true });

  wrap.addEventListener('touchend', (evento) => {
    if (inicioX === null) return;
    const deltaX = evento.changedTouches[0].clientX - inicioX;
    inicioX = null;
    if (deltaX <= -LIMIAR_DESLIZE_PX) {
      proximo();
    } else if (deltaX >= LIMIAR_DESLIZE_PX) {
      anterior();
    }
    iniciarAutoplay();
  }, { passive: true });

  iniciarAutoplay();
})();
