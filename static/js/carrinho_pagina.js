(function () {
  const listaEl = document.getElementById('lista-itens');
  const vazioEl = document.getElementById('carrinho-vazio');
  const resumoEl = document.getElementById('resumo-carrinho');
  const resumoQtdEl = document.getElementById('resumo-quantidade');
  const resumoFaixaEl = document.getElementById('resumo-faixa');
  const resumoSubtotalEl = document.getElementById('resumo-subtotal');
  const progressoFaixaTexto = document.getElementById('progresso-faixa-texto');
  const progressoFaixaPreenchimento = document.getElementById('progresso-faixa-preenchimento');
  const progressoFreteTexto = document.getElementById('progresso-frete-texto');
  const progressoFretePreenchimento = document.getElementById('progresso-frete-preenchimento');
  const avisoMinimoEl = document.getElementById('aviso-minimo');
  const btnLimpar = document.getElementById('btn-limpar');
  if (!listaEl) return;

  let faixaAnterior = null;
  let freteAnteriorAtingido = null;
  let primeiraRenderizacao = true;

  function mostrarToast(texto) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = texto;
    toast.hidden = false;
    clearTimeout(mostrarToast._timer);
    mostrarToast._timer = setTimeout(() => {
      toast.hidden = true;
    }, 2600);
  }

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

    // barra de progresso: proxima faixa de desconto
    if (dados.proxima_faixa) {
      progressoFaixaTexto.textContent =
        `${dados.quantidade_total} / ${dados.proxima_faixa.quantidade} medalhas — ` +
        `faltam ${dados.proxima_faixa.faltam} para o próximo desconto`;
      progressoFaixaPreenchimento.style.width =
        _percentualBarra(dados.quantidade_total, dados.faixa_atual_inicio, dados.proxima_faixa.quantidade) + '%';
    } else {
      progressoFaixaTexto.textContent = '🎉 Você já está na melhor faixa de preço!';
      progressoFaixaPreenchimento.style.width = '100%';
    }

    // barra de progresso: frete gratis
    if (dados.frete_gratis_atingido) {
      progressoFreteTexto.textContent = '🎉 Frete grátis desbloqueado!';
      progressoFretePreenchimento.style.width = '100%';
    } else {
      progressoFreteTexto.textContent =
        `Faltam ${formatarPreco(dados.falta_para_frete_gratis)} em compras para o frete grátis`;
      progressoFretePreenchimento.style.width =
        Math.min(100, (dados.subtotal_total / dados.frete_gratis_reais) * 100) + '%';
    }

    // toast de comemoracao -- so depois da primeira renderizacao, pra nao
    // disparar assim que a pagina abre com um carrinho ja em faixa alta.
    if (!primeiraRenderizacao) {
      if (dados.faixa_label !== faixaAnterior) {
        const preco = dados.itens[0] ? dados.itens[0].preco_unitario : null;
        mostrarToast(`🎉 Novo desconto desbloqueado! Agora ${formatarPreco(preco)}/un`);
      } else if (dados.frete_gratis_atingido && !freteAnteriorAtingido) {
        mostrarToast('🎉 Frete grátis desbloqueado!');
      }
    }
    faixaAnterior = dados.faixa_label;
    freteAnteriorAtingido = dados.frete_gratis_atingido;
    primeiraRenderizacao = false;

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
