(function () {
  const botoesAdicionar = document.querySelectorAll('.pulseira-btn-adicionar');
  if (botoesAdicionar.length === 0) return;

  function formatarPreco(valor) {
    return 'R$ ' + valor.toFixed(2).replace('.', ',');
  }

  function quantidadeInputDe(pulseiraId) {
    return document.getElementById(`pulseira-quantidade-${pulseiraId}`);
  }

  // Preco fixo (sem faixa de atacado -- ver GRUPO_DE_CHAVE em
  // services/pricing.py: "pulseiras" e´ isolado dos outros grupos de
  // proposito, mesmo padrao de colares.js), entao so mostra unidades x
  // subtotal, sem "faltam X pra cair" nem chamada ao /api/carrinho/
  // calcular -- o preco unitario nunca muda.
  function atualizarPreviewPreco(pulseiraId, preco) {
    const quantidadeInput = quantidadeInputDe(pulseiraId);
    const previewEl = document.getElementById(`pulseira-preview-preco-${pulseiraId}`);
    if (!quantidadeInput || !previewEl) return;
    const quantidade = Math.max(1, parseInt(quantidadeInput.value, 10) || 1);
    const subtotal = preco * quantidade;
    previewEl.innerHTML =
      `<strong>${quantidade} unidade${quantidade > 1 ? 's' : ''}</strong> · ${formatarPreco(preco)}/un · ` +
      `subtotal <strong>${formatarPreco(subtotal)}</strong>`;
    previewEl.hidden = false;
  }

  document.querySelectorAll('.pulseira-qtd-menos, .pulseira-qtd-mais').forEach((botao) => {
    botao.addEventListener('click', () => {
      const pulseiraId = botao.dataset.pulseira;
      const quantidadeInput = quantidadeInputDe(pulseiraId);
      if (!quantidadeInput) return;
      const delta = botao.classList.contains('pulseira-qtd-mais') ? 1 : -1;
      const atual = parseInt(quantidadeInput.value, 10) || 1;
      quantidadeInput.value = Math.max(1, atual + delta);
      const btnAdicionar = document.querySelector(`.pulseira-btn-adicionar[data-pulseira="${pulseiraId}"]`);
      if (btnAdicionar) atualizarPreviewPreco(pulseiraId, parseFloat(btnAdicionar.dataset.preco));
    });
  });

  document.querySelectorAll('.pulseira-quantidade').forEach((input) => {
    input.addEventListener('input', () => {
      const pulseiraId = input.id.replace('pulseira-quantidade-', '');
      const btnAdicionar = document.querySelector(`.pulseira-btn-adicionar[data-pulseira="${pulseiraId}"]`);
      if (btnAdicionar) atualizarPreviewPreco(pulseiraId, parseFloat(btnAdicionar.dataset.preco));
    });
  });

  botoesAdicionar.forEach((botao) => {
    const pulseiraId = botao.dataset.pulseira;
    const preco = parseFloat(botao.dataset.preco);
    atualizarPreviewPreco(pulseiraId, preco);
    rastrearEventoGA4('view_item', { item_id: pulseiraId, item_name: botao.dataset.nome, value: preco, currency: 'BRL' });

    botao.addEventListener('click', () => {
      const quantidadeInput = quantidadeInputDe(pulseiraId);
      const quantidade = quantidadeInput ? Math.max(1, parseInt(quantidadeInput.value, 10) || 1) : 1;

      carrinhoAdicionarItem({
        chave: `pulseira-${pulseiraId}`,
        tipo: 'catalogo',
        produtoId: pulseiraId,
        produtoNome: botao.dataset.nome,
        modeloId: '',
        modeloNome: '',
        imagem: botao.dataset.imagem,
        formato: 'pulseira',
        chave_preco: botao.dataset.chavePreco,
        tamanho: '',
        cor: null,
        quantidade,
      });

      if (typeof carrinhoAtualizarContador === 'function') carrinhoAtualizarContador();
      if (typeof carrinhoAtualizarBarraPersistente === 'function') carrinhoAtualizarBarraPersistente();
      rastrearEventoGA4('add_to_cart', { item_id: pulseiraId, value: preco, currency: 'BRL', quantity: quantidade });
      atualizarPreviewPreco(pulseiraId, preco);

      const textoOriginal = botao.textContent;
      botao.textContent = 'Adicionado ✓';
      setTimeout(() => {
        botao.textContent = textoOriginal;
      }, 1200);
    });
  });
})();
