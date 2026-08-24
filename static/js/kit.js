(function () {
  const lista = document.getElementById('kit-itens');
  const totalSpan = document.getElementById('kit-total-unidades');
  const btnAdicionar = document.getElementById('kit-adicionar-btn');
  const tamanhoFieldset = document.getElementById('kit-tamanho');
  if (!lista || !btnAdicionar) return;

  const linhas = Array.from(lista.querySelectorAll('.kit-item'));

  function atualizarTotal() {
    const total = linhas.reduce((soma, linha) => {
      const input = linha.querySelector('.kit-qtd-input');
      return soma + Math.max(0, parseInt(input.value, 10) || 0);
    }, 0);
    if (totalSpan) totalSpan.textContent = `${total} unidades no total`;
  }

  linhas.forEach((linha) => {
    const input = linha.querySelector('.kit-qtd-input');
    const menos = linha.querySelector('.kit-qtd-menos');
    const mais = linha.querySelector('.kit-qtd-mais');
    menos.addEventListener('click', () => {
      input.value = Math.max(0, (parseInt(input.value, 10) || 0) - 1);
      atualizarTotal();
    });
    mais.addEventListener('click', () => {
      input.value = (parseInt(input.value, 10) || 0) + 1;
      atualizarTotal();
    });
    input.addEventListener('input', atualizarTotal);
  });

  function tamanhoSelecionado() {
    const marcado = tamanhoFieldset.querySelector('input[name="kit-tamanho"]:checked');
    return marcado ? marcado.value : '16mm';
  }

  // divide a quantidade de um item entre 12mm e 16mm quando "misturado"
  // esta selecionado -- metade pra cada, a diferenca de arredondamento
  // (quantidade impar) fica no 16mm.
  function dividirQuantidade(quantidade) {
    const metadeMenor = Math.floor(quantidade / 2);
    return { qtd12mm: metadeMenor, qtd16mm: quantidade - metadeMenor };
  }

  function adicionarItemAoCarrinho(linha, tamanho, quantidade) {
    if (quantidade <= 0) return;
    const produtoId = linha.dataset.produtoId;
    const produtoNome = linha.dataset.produtoNome;
    const modeloId = linha.dataset.modeloId;
    const modeloNome = linha.dataset.modeloNome;
    const imagem = linha.dataset.imagem;
    carrinhoAdicionarItem({
      chave: `${produtoId}-${modeloId}-medalha-${tamanho}`,
      tipo: 'catalogo',
      produtoId,
      produtoNome,
      modeloId,
      modeloNome,
      imagem,
      formato: 'medalha',
      chave_preco: tamanho,
      tamanho,
      cor: null,
      quantidade,
    });
  }

  btnAdicionar.addEventListener('click', () => {
    const tamanho = tamanhoSelecionado();
    linhas.forEach((linha) => {
      const input = linha.querySelector('.kit-qtd-input');
      const quantidade = Math.max(0, parseInt(input.value, 10) || 0);
      if (quantidade <= 0) return;
      if (tamanho === 'misturado') {
        const { qtd12mm, qtd16mm } = dividirQuantidade(quantidade);
        adicionarItemAoCarrinho(linha, '12mm', qtd12mm);
        adicionarItemAoCarrinho(linha, '16mm', qtd16mm);
      } else {
        adicionarItemAoCarrinho(linha, tamanho, quantidade);
      }
    });
    if (typeof carrinhoAtualizarContador === 'function') carrinhoAtualizarContador();
    if (typeof carrinhoAtualizarBarraPersistente === 'function') carrinhoAtualizarBarraPersistente();
    rastrearEventoGA4('select_content', { content_type: 'kit', item_id: 'kit-livraria-shalom' });
    window.location.href = '/carrinho';
  });

  atualizarTotal();
})();
