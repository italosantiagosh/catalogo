function formatarPreco(valor) {
  return 'R$ ' + valor.toFixed(2).replace('.', ',');
}

(function () {
  const listaEl = document.getElementById('lista-itens');
  const vazioEl = document.getElementById('carrinho-vazio');
  const resumoEl = document.getElementById('resumo-carrinho');
  const resumoQtdEl = document.getElementById('resumo-quantidade');
  const resumoFaixaEl = document.getElementById('resumo-faixa');
  const resumoSubtotalEl = document.getElementById('resumo-subtotal');
  const avisoProximaFaixaEl = document.getElementById('aviso-proxima-faixa');
  const avisoMinimoEl = document.getElementById('aviso-minimo');
  const btnLimpar = document.getElementById('btn-limpar');
  if (!listaEl) return;

  function linhaItem(item, calculo) {
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
        <p class="item-preco">
          ${formatarPreco(calculo.preco_unitario)} un. &middot;
          <strong>${formatarPreco(calculo.subtotal)}</strong>
        </p>
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

  async function render() {
    const itens = carrinhoObterItens();
    listaEl.innerHTML = '';

    if (itens.length === 0) {
      vazioEl.hidden = false;
      resumoEl.hidden = true;
      return;
    }

    vazioEl.hidden = true;
    resumoEl.hidden = false;

    const resposta = await fetch('/api/carrinho/calcular', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        itens: itens.map((item) => ({ tamanho: item.tamanho, quantidade: item.quantidade })),
      }),
    });
    const dados = await resposta.json();

    listaEl.innerHTML = '';
    itens.forEach((item, i) => {
      listaEl.appendChild(linhaItem(item, dados.itens[i]));
    });

    resumoQtdEl.textContent = String(dados.quantidade_total);
    resumoFaixaEl.textContent = dados.faixa_label;
    resumoSubtotalEl.textContent = formatarPreco(dados.subtotal_total);

    if (dados.proxima_faixa) {
      avisoProximaFaixaEl.hidden = false;
      avisoProximaFaixaEl.textContent =
        `Faltam ${dados.proxima_faixa.faltam} unidade(s) para desbloquear ${formatarPreco(dados.proxima_faixa.preco)}/un.`;
    } else {
      avisoProximaFaixaEl.hidden = true;
    }

    if (!dados.atinge_minimo) {
      avisoMinimoEl.hidden = false;
      avisoMinimoEl.textContent =
        `Pedido mínimo de ${formatarPreco(dados.pedido_minimo_reais)} -- adicione mais itens para finalizar.`;
    } else {
      avisoMinimoEl.hidden = true;
    }
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
