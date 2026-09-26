// Efeito "reveal" ao rolar: blocos abaixo da dobra aparecem com fade +
// leve subida quando entram na tela (ver .reveal em style.css).
//
// Seguro por construcao:
// - a classe .reveal so e´ posta AQUI, pelo JS -- sem JS (ou se esse
//   arquivo falhar) nada fica escondido;
// - so marca o que ainda esta ABAIXO da tela no carregamento, entao o
//   conteudo da primeira dobra nunca pisca/some;
// - quem pediu "reduzir movimento" no sistema nao recebe o efeito.
(function () {
  if (!('IntersectionObserver' in window)) return;
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  // blocos inteiros + cards em grade (esses com atraso escalonado)
  const SELETOR_BLOCOS = [
    'main > section',
    '.descricao-produto',
    '.relacionados',
    '.avaliacoes-produto',
    '.prova-social',
    '.nossa-historia',
  ].join(',');
  const SELETOR_CARDS = '.destaque-card, .modelo-card, .avaliacao-card, .prova-social-card';

  const alturaTela = window.innerHeight;
  const abaixoDaDobra = (el) => el.getBoundingClientRect().top > alturaTela * 0.92;

  const observador = new IntersectionObserver((entradas) => {
    entradas.forEach((entrada) => {
      if (!entrada.isIntersecting) return;
      const el = entrada.target;
      el.classList.add('reveal-visivel');
      observador.unobserve(el);
      // terminou de aparecer: devolve o elemento ao estado normal, pra
      // o transform do reveal nao brigar com o hover dos cards
      const limpar = () => {
        el.classList.remove('reveal', 'reveal-visivel');
        el.style.removeProperty('--reveal-atraso');
      };
      el.addEventListener('transitionend', function aoTerminar(ev) {
        if (ev.target !== el || ev.propertyName !== 'opacity') return;
        el.removeEventListener('transitionend', aoTerminar);
        limpar();
      });
      // rede de seguranca se o transitionend nao vier (aba em segundo
      // plano etc.): 0,6s de animacao + ate 0,3s de atraso
      setTimeout(limpar, 1200);
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

  const marcar = (el, atraso) => {
    if (el.classList.contains('reveal') || !abaixoDaDobra(el)) return;
    el.classList.add('reveal');
    if (atraso) el.style.setProperty('--reveal-atraso', atraso + 'ms');
    observador.observe(el);
  };

  document.querySelectorAll(SELETOR_BLOCOS).forEach((el) => marcar(el, 0));

  // cards: atraso de 60ms por posicao dentro da mesma grade, limitado
  // a 5 posicoes (grade grande nao pode demorar pra aparecer inteira)
  const porPai = new Map();
  document.querySelectorAll(SELETOR_CARDS).forEach((card) => {
    const i = porPai.get(card.parentElement) || 0;
    porPai.set(card.parentElement, i + 1);
    // card dentro de bloco que ja vai animar inteiro: nao anima de novo
    if (card.closest('.reveal')) return;
    marcar(card, Math.min(i % 6, 5) * 60);
  });
})();
