(function () {
  const listaEl = document.getElementById('lista-itens');
  const vazioEl = document.getElementById('carrinho-vazio');
  const resumoEl = document.getElementById('resumo-carrinho');
  const resumoQtdEl = document.getElementById('resumo-quantidade');
  const btnLimpar = document.getElementById('btn-limpar');
  if (!listaEl) return;

  function linhaItem(item) {
    const linha = document.createElement('article');
    linha.className = 'item-carrinho';
    linha.innerHTML = `
      <img src="${item.imagem}" alt="${item.produtoNome}">
      <div class="item-info">
        <h2>${item.produtoNome}</h2>
        <p>${item.modeloNome} &middot; ${item.tamanho.replace('mm', ' mm')}</p>
        <div class="item-stepper">
          <button type="button" class="qtd-menos" aria-label="Diminuir quantidade">−</button>
          <span class="item-qtd">${item.quantidade}</span>
          <button type="button" class="qtd-mais" aria-label="Aumentar quantidade">+</button>
        </div>
      </div>
      <button type="button" class="item-remover" aria-label="Remover item">×</button>
    `;
    linha.querySelector('.qtd-menos').addEventListener('click', () => {
      carrinhoAtualizarQuantidade(item.chave, item.quantidade - 1);
      render();
    });
    linha.querySelector('.qtd-mais').addEventListener('click', () => {
      carrinhoAtualizarQuantidade(item.chave, item.quantidade + 1);
      render();
    });
    linha.querySelector('.item-remover').addEventListener('click', () => {
      carrinhoRemoverItem(item.chave);
      render();
    });
    return linha;
  }

  function render() {
    const itens = carrinhoObterItens();
    listaEl.innerHTML = '';

    if (itens.length === 0) {
      vazioEl.hidden = false;
      resumoEl.hidden = true;
      return;
    }

    vazioEl.hidden = true;
    resumoEl.hidden = false;
    for (const item of itens) {
      listaEl.appendChild(linhaItem(item));
    }
    resumoQtdEl.textContent = String(carrinhoQuantidadeTotal());
  }

  if (btnLimpar) {
    btnLimpar.addEventListener('click', () => {
      if (confirm('Limpar todo o carrinho?')) {
        carrinhoLimpar();
        render();
      }
    });
  }

  render();
})();
