(function () {
  const botoesAdicionar = document.querySelectorAll('.colar-btn-adicionar');
  if (botoesAdicionar.length === 0) return;

  function formatarPreco(valor) {
    return 'R$ ' + valor.toFixed(2).replace('.', ',');
  }

  function quantidadeInputDe(colarId) {
    return document.getElementById(`colar-quantidade-${colarId}`);
  }

  // Preco fixo (sem faixa de atacado -- ver GRUPO_DE_CHAVE em
  // services/pricing.py: "colares" e´ isolado dos outros grupos de
  // proposito, mesmo padrao da Cruz para Terco), entao so mostra
  // unidades x subtotal, sem "faltam X pra cair" nem chamada ao
  // /api/carrinho/calcular -- o preco unitario nunca muda.
  function atualizarPreviewPreco(colarId, preco) {
    const quantidadeInput = quantidadeInputDe(colarId);
    const previewEl = document.getElementById(`colar-preview-preco-${colarId}`);
    if (!quantidadeInput || !previewEl) return;
    const quantidade = Math.max(1, parseInt(quantidadeInput.value, 10) || 1);
    const subtotal = preco * quantidade;
    previewEl.innerHTML =
      `<strong>${quantidade} unidade${quantidade > 1 ? 's' : ''}</strong> · ${formatarPreco(preco)}/un · ` +
      `subtotal <strong>${formatarPreco(subtotal)}</strong>`;
    previewEl.hidden = false;
  }

  document.querySelectorAll('.colar-qtd-menos, .colar-qtd-mais').forEach((botao) => {
    botao.addEventListener('click', () => {
      const colarId = botao.dataset.colar;
      const quantidadeInput = quantidadeInputDe(colarId);
      if (!quantidadeInput) return;
      const delta = botao.classList.contains('colar-qtd-mais') ? 1 : -1;
      const atual = parseInt(quantidadeInput.value, 10) || 1;
      quantidadeInput.value = Math.max(1, atual + delta);
      const btnAdicionar = document.querySelector(`.colar-btn-adicionar[data-colar="${colarId}"]`);
      if (btnAdicionar) atualizarPreviewPreco(colarId, parseFloat(btnAdicionar.dataset.preco));
    });
  });

  document.querySelectorAll('.colar-quantidade').forEach((input) => {
    input.addEventListener('input', () => {
      const colarId = input.id.replace('colar-quantidade-', '');
      const btnAdicionar = document.querySelector(`.colar-btn-adicionar[data-colar="${colarId}"]`);
      if (btnAdicionar) atualizarPreviewPreco(colarId, parseFloat(btnAdicionar.dataset.preco));
    });
  });

  botoesAdicionar.forEach((botao) => {
    const colarId = botao.dataset.colar;
    const preco = parseFloat(botao.dataset.preco);
    atualizarPreviewPreco(colarId, preco);
    rastrearEventoGA4('view_item', { item_id: colarId, item_name: botao.dataset.nome, value: preco, currency: 'BRL' });

    botao.addEventListener('click', () => {
      const quantidadeInput = quantidadeInputDe(colarId);
      const quantidade = quantidadeInput ? Math.max(1, parseInt(quantidadeInput.value, 10) || 1) : 1;

      carrinhoAdicionarItem({
        chave: `colar-${colarId}`,
        tipo: 'catalogo',
        produtoId: colarId,
        produtoNome: botao.dataset.nome,
        modeloId: '',
        modeloNome: '',
        imagem: botao.dataset.imagem,
        formato: 'colar',
        chave_preco: botao.dataset.chavePreco,
        tamanho: '',
        cor: null,
        quantidade,
      });

      if (typeof carrinhoAtualizarContador === 'function') carrinhoAtualizarContador();
      if (typeof carrinhoAtualizarBarraPersistente === 'function') carrinhoAtualizarBarraPersistente();
      rastrearEventoGA4('add_to_cart', { item_id: colarId, value: preco, currency: 'BRL', quantity: quantidade });
      atualizarPreviewPreco(colarId, preco);

      const textoOriginal = botao.textContent;
      botao.textContent = 'Adicionado ✓';
      setTimeout(() => {
        botao.textContent = textoOriginal;
      }, 1200);
    });
  });
})();
