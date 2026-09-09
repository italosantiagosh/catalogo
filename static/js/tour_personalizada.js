(function () {
  // Tour guiado da /personalizada -- spotlight escurece a tela inteira
  // e abre um "buraco" so em volta do elemento do passo atual (ver
  // conversa). So roda no client, sem chamada nenhuma ao servidor --
  // nao tem custo de trafego/carga pro backend.
  //
  // 4 passos, seguindo a mesma numeracao do guia visual ja fixo no
  // topo da pagina. Passos 1-2 (formato/foto) ja estao visiveis na
  // primeira tela; passos 3-4 (recorte/previa) so existem depois que a
  // pessoa realmente sobe uma foto -- por isso usam um
  // MutationObserver nas views (#view-cropper/#view-preview*) em vez
  // de aparecer tudo de uma vez.
  //
  // "Pular tutorial" ou terminar o passo 4 grava uma flag no
  // localStorage: nao aparece mais nesse navegador depois disso (ver
  // conversa -- quem ja sabe usar nao precisa ver de novo a cada
  // pedido novo).
  const CHAVE_TOUR_VISTO = 'catalogo_medalhas_tour_personalizada_visto';
  if (localStorage.getItem(CHAVE_TOUR_VISTO)) return;

  const secFormatos = document.getElementById('sel-formatos');
  const dropzone = document.getElementById('dropzone-imagem');
  if (!secFormatos || !dropzone) return; // pagina sem os elementos esperados -- nao tenta

  let overlay = null;
  let holeEl = null;
  let tooltipEl = null;
  let passoAtual = 0; // 0 = nao iniciado/escondido
  let cancelado = false;

  const PASSOS = [
    null, // indice 0 nao usado (facilita passoAtual comecar em 1)
    {
      alvo: () => secFormatos,
      titulo: '1. Escolha o formato',
      texto: 'Medalha, entremeio ou chaveiro -- de 1 ou 2 lados.',
      botao: 'Próximo',
      aoAvancar: () => mostrarPasso(2),
    },
    {
      alvo: () => dropzone,
      titulo: '2. Envie sua foto',
      texto: 'Do santo, de uma pessoa ou de um momento especial. Toque aqui pra escolher.',
      botao: 'Entendi',
      aoAvancar: esconderTour, // ultimo passo interativo desta tela -- some e espera a proxima view
    },
    {
      alvo: () => document.getElementById('cropper-canvas'),
      titulo: '3. Ajuste o enquadramento',
      texto: 'Arraste pra posicionar e use o controle de zoom -- do jeito que você quiser.',
      botao: 'Entendi',
      aoAvancar: esconderTour,
    },
    {
      alvo: () =>
        (document.getElementById('view-preview-duas-faces') &&
          !document.getElementById('view-preview-duas-faces').hidden
          ? document.querySelector('#view-preview-duas-faces .quantidade')
          : document.querySelector('#view-preview .quantidade')),
      titulo: '4. Veja a prévia e peça',
      texto: 'Confira a simulação, escolha a quantidade e adicione ao carrinho.',
      botao: 'Concluir',
      aoAvancar: concluirTour,
    },
  ];

  function criarOverlaySeNecessario() {
    if (overlay) return;
    overlay = document.createElement('div');
    overlay.className = 'tour-overlay';

    holeEl = document.createElement('div');
    holeEl.className = 'tour-hole';
    overlay.appendChild(holeEl);

    tooltipEl = document.createElement('div');
    tooltipEl.className = 'tour-tooltip';
    tooltipEl.innerHTML =
      '<p class="tour-tooltip-titulo"></p>' +
      '<p class="tour-tooltip-texto"></p>' +
      '<div class="tour-tooltip-acoes">' +
      '<button type="button" class="tour-pular">Pular tutorial</button>' +
      '<button type="button" class="tour-proximo botao-carrinho"></button>' +
      '</div>';
    overlay.appendChild(tooltipEl);
    document.body.appendChild(overlay);

    tooltipEl.querySelector('.tour-pular').addEventListener('click', cancelarTour);
    tooltipEl.querySelector('.tour-proximo').addEventListener('click', () => {
      const passo = PASSOS[passoAtual];
      if (passo && passo.aoAvancar) passo.aoAvancar();
    });

    window.addEventListener('resize', posicionarNoAlvoAtual);
    window.addEventListener('scroll', posicionarNoAlvoAtual, true);
  }

  function posicionarNoAlvoAtual() {
    const passo = PASSOS[passoAtual];
    if (!passo) return;
    const alvo = passo.alvo();
    if (!alvo) return;
    posicionar(alvo);
  }

  function posicionar(alvo) {
    const rect = alvo.getBoundingClientRect();
    const folga = 6;
    holeEl.style.top = `${rect.top - folga}px`;
    holeEl.style.left = `${rect.left - folga}px`;
    holeEl.style.width = `${rect.width + folga * 2}px`;
    holeEl.style.height = `${rect.height + folga * 2}px`;

    // tooltip embaixo do alvo, ou em cima se nao couber embaixo --
    // usa a altura JA RENDERIZADA do tooltip (nao uma estimativa fixa),
    // senao o texto mais longo de alguns passos pode ficar maior do
    // que o previsto e sobrepor o proprio buraco (ver conversa).
    const gapTooltip = 16;
    const alturaTooltip = tooltipEl.offsetHeight || 150;
    const espacoAbaixo = window.innerHeight - rect.bottom;
    const emCima = espacoAbaixo < alturaTooltip + gapTooltip && rect.top > alturaTooltip + gapTooltip;
    tooltipEl.style.top = emCima
      ? `${Math.max(12, rect.top - alturaTooltip - gapTooltip)}px`
      : `${rect.bottom + folga + gapTooltip}px`;
    const esquerdaDesejada = Math.max(12, Math.min(rect.left, window.innerWidth - 296));
    tooltipEl.style.left = `${esquerdaDesejada}px`;
  }

  function mostrarPasso(numero) {
    const passo = PASSOS[numero];
    if (!passo) return;
    const alvo = passo.alvo();
    if (!alvo) return; // elemento ainda nao existe -- fica esperando o observer chamar de novo
    passoAtual = numero;
    criarOverlaySeNecessario();
    overlay.hidden = false;
    tooltipEl.querySelector('.tour-tooltip-titulo').textContent = passo.titulo;
    tooltipEl.querySelector('.tour-tooltip-texto').textContent = passo.texto;
    tooltipEl.querySelector('.tour-proximo').textContent = passo.botao;
    posicionar(alvo);
    alvo.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function esconderTour() {
    if (overlay) overlay.hidden = true;
  }

  function cancelarTour() {
    cancelado = true;
    esconderTour();
    localStorage.setItem(CHAVE_TOUR_VISTO, '1');
  }

  function concluirTour() {
    esconderTour();
    localStorage.setItem(CHAVE_TOUR_VISTO, '1');
  }

  // passos 3 e 4 so existem depois de uma acao real da pessoa (subiu
  // foto, terminou o recorte) -- observa as views em vez de tentar
  // adivinhar quando isso acontece.
  function observarViews() {
    const viewCropper = document.getElementById('view-cropper');
    const viewPreview = document.getElementById('view-preview');
    const viewPreviewDuasFaces = document.getElementById('view-preview-duas-faces');
    const alvos = [viewCropper, viewPreview, viewPreviewDuasFaces].filter(Boolean);
    if (!alvos.length) return;

    const observer = new MutationObserver(() => {
      if (cancelado) {
        observer.disconnect();
        return;
      }
      if (viewCropper && !viewCropper.hidden && passoAtual < 3) {
        mostrarPasso(3);
      } else if (
        ((viewPreview && !viewPreview.hidden) || (viewPreviewDuasFaces && !viewPreviewDuasFaces.hidden)) &&
        passoAtual < 4
      ) {
        mostrarPasso(4);
      }
    });
    alvos.forEach((el) => observer.observe(el, { attributes: true, attributeFilter: ['hidden'] }));
  }

  document.addEventListener('DOMContentLoaded', () => {
    observarViews();
    mostrarPasso(1);
  });
})();
