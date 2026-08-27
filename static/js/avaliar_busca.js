(function () {
  // busca de produto pra pagina /avaliar sem produto fixo na URL (ver
  // conversa: um unico link geral pra mandar pra base de clientes
  // antiga, em vez de um link por produto). Reaproveita /api/busca
  // (mesma API da home) e o mesmo padrao de dropdown (busca-resultados).
  const input = document.getElementById('avaliar-busca-produto');
  const resultados = document.getElementById('avaliar-busca-resultados');
  if (!input || !resultados) return; // pagina com produto ja fixo (ver avaliar_produto em app.py) -- nada a fazer

  const buscaWrap = document.querySelector('.avaliar-busca-wrap');
  const produtoCard = document.getElementById('avaliar-produto-card');
  const produtoImagem = document.getElementById('avaliar-produto-imagem');
  const produtoNome = document.getElementById('avaliar-produto-nome');
  const produtoTrocar = document.getElementById('avaliar-produto-trocar');
  const caixa = document.getElementById('avaliar-caixa');
  const produtoIdInput = document.getElementById('aval-produto-id');

  let buscaTimer = null;
  let requisicaoAtual = 0;

  function esconderResultados() {
    resultados.hidden = true;
    resultados.innerHTML = '';
  }

  function selecionarProduto(item) {
    produtoIdInput.value = item.id;
    produtoImagem.src = item.thumbnail;
    produtoNome.textContent = item.nome;
    produtoCard.hidden = false;
    caixa.hidden = false;
    buscaWrap.hidden = true;
    esconderResultados();
  }

  function renderizarResultados(itens) {
    if (itens.length === 0) {
      resultados.innerHTML = '<p class="busca-resultados-vazio">Nenhum produto encontrado com esse nome.</p>';
      resultados.hidden = false;
      return;
    }
    resultados.innerHTML = '';
    itens.forEach((item) => {
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.className = 'busca-resultado-item';
      botao.style.width = '100%';
      botao.style.border = 'none';
      botao.style.background = 'none';
      botao.style.cursor = 'pointer';
      botao.style.textAlign = 'left';
      botao.innerHTML = `<img src="${item.thumbnail}" alt="" loading="lazy"><span>${item.nome}</span>`;
      botao.addEventListener('click', () => selecionarProduto(item));
      resultados.appendChild(botao);
    });
    resultados.hidden = false;
  }

  function buscar() {
    const termo = input.value.trim();
    if (!termo) {
      esconderResultados();
      return;
    }
    const idRequisicao = ++requisicaoAtual;
    fetch(`/api/busca?q=${encodeURIComponent(termo)}`)
      .then((resposta) => (resposta.ok ? resposta.json() : []))
      .then((itens) => {
        if (idRequisicao !== requisicaoAtual) return;
        renderizarResultados(itens);
      })
      .catch(() => {});
  }

  input.addEventListener('input', () => {
    clearTimeout(buscaTimer);
    buscaTimer = setTimeout(buscar, 250);
  });

  document.addEventListener('click', (evento) => {
    if (evento.target !== input && !resultados.contains(evento.target)) {
      esconderResultados();
    }
  });

  if (produtoTrocar) {
    produtoTrocar.addEventListener('click', () => {
      caixa.hidden = true;
      produtoCard.hidden = true;
      buscaWrap.hidden = false;
      input.value = '';
      input.focus();
    });
  }
})();
