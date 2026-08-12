(function () {
  const grid = document.getElementById('modelos-grid');
  const painel = document.getElementById('painel-selecao');
  const nomeSpan = document.getElementById('sel-modelo-nome');
  const tamanhosFieldset = document.getElementById('sel-tamanhos');
  const quantidadeInput = document.getElementById('sel-quantidade');
  const qtdMenos = document.getElementById('qtd-menos');
  const qtdMais = document.getElementById('qtd-mais');
  const btnAdicionar = document.getElementById('btn-adicionar');
  if (!grid || !painel) return;

  const produtoId = grid.dataset.produtoId;
  const produtoNome = grid.dataset.produtoNome;
  let modeloSelecionado = null;

  function atualizarBotao() {
    const tamanhoEscolhido = tamanhosFieldset.querySelector('input[name="tamanho"]:checked');
    if (!tamanhoEscolhido) {
      btnAdicionar.disabled = true;
      btnAdicionar.textContent = 'Selecione um tamanho';
    } else {
      btnAdicionar.disabled = false;
      btnAdicionar.textContent = 'Adicionar ao carrinho';
    }
  }

  function selecionarModelo(botao) {
    for (const outro of grid.querySelectorAll('.modelo-card')) {
      outro.setAttribute('aria-pressed', String(outro === botao));
    }

    modeloSelecionado = {
      id: botao.dataset.modeloId,
      nome: botao.dataset.modeloNome,
      imagem: botao.querySelector('img').src,
    };
    nomeSpan.textContent = modeloSelecionado.nome;

    const tamanhos = JSON.parse(botao.dataset.tamanhos || '[]');
    tamanhosFieldset.innerHTML = '<legend>Tamanho *</legend>';
    tamanhos.forEach((tamanho) => {
      const id = `tamanho-${tamanho}`;
      const label = document.createElement('label');
      label.className = 'opcao-tamanho';
      label.innerHTML = `
        <input type="radio" name="tamanho" id="${id}" value="${tamanho}">
        ${tamanho.replace('mm', ' mm')}
      `;
      tamanhosFieldset.appendChild(label);
    });

    painel.hidden = false;
    painel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    atualizarBotao();
  }

  grid.addEventListener('click', (evento) => {
    const botao = evento.target.closest('.modelo-card');
    if (botao) selecionarModelo(botao);
  });

  tamanhosFieldset.addEventListener('change', (evento) => {
    if (evento.target.name === 'tamanho') atualizarBotao();
  });

  function ajustarQuantidade(delta) {
    const atual = parseInt(quantidadeInput.value, 10) || 1;
    quantidadeInput.value = Math.max(1, atual + delta);
  }

  if (qtdMenos) qtdMenos.addEventListener('click', () => ajustarQuantidade(-1));
  if (qtdMais) qtdMais.addEventListener('click', () => ajustarQuantidade(1));

  if (btnAdicionar) {
    btnAdicionar.addEventListener('click', () => {
      const tamanhoInput = tamanhosFieldset.querySelector('input[name="tamanho"]:checked');
      if (!modeloSelecionado || !tamanhoInput) return;

      const quantidade = Math.max(1, parseInt(quantidadeInput.value, 10) || 1);
      carrinhoAdicionarItem({
        chave: `${produtoId}-${modeloSelecionado.id}-${tamanhoInput.value}`,
        tipo: 'catalogo',
        produtoId,
        produtoNome,
        modeloId: modeloSelecionado.id,
        modeloNome: modeloSelecionado.nome,
        imagem: modeloSelecionado.imagem,
        tamanho: tamanhoInput.value,
        quantidade,
      });

      const textoOriginal = 'Adicionar ao carrinho';
      btnAdicionar.textContent = 'Adicionado ✓';
      setTimeout(() => {
        btnAdicionar.textContent = textoOriginal;
      }, 1200);
    });
  }

  // seleciona o primeiro modelo automaticamente para quem tem só um --
  // mas o tamanho continua em branco, precisa escolher na mao.
  const primeiro = grid.querySelector('.modelo-card');
  if (primeiro && grid.querySelectorAll('.modelo-card').length === 1) {
    selecionarModelo(primeiro);
  }
})();
