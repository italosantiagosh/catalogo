(function () {
  // busca ao vivo da home: nao ha grade nessa pagina (fica em /catalogo),
  // entao a cada tecla busca no servidor (/api/busca) e mostra nome +
  // miniatura dos santos que baterem, num dropdown embaixo do campo.
  const input = document.getElementById('busca-home');
  const resultados = document.getElementById('busca-home-resultados');
  if (!input || !resultados) return;

  let buscaTimer = null;
  let requisicaoAtual = 0;

  function esconderResultados() {
    resultados.hidden = true;
    resultados.innerHTML = '';
  }

  function renderizarResultados(itens, termo) {
    if (itens.length === 0) {
      resultados.innerHTML = '<p class="busca-resultados-vazio">Nenhum santo encontrado com esse nome.</p>';
      resultados.hidden = false;
      return;
    }
    const linksHtml = itens
      .map(
        (item) => `
          <a class="busca-resultado-item" href="${item.url}">
            <img src="${item.thumbnail}" alt="" loading="lazy" decoding="async">
            <span>${item.nome}</span>
          </a>
        `
      )
      .join('');
    const verTodosHtml = `<a class="busca-resultado-ver-todos" href="/catalogo?q=${encodeURIComponent(termo)}">Ver todos os resultados →</a>`;
    resultados.innerHTML = linksHtml + verTodosHtml;
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
        if (idRequisicao !== requisicaoAtual) return; // resposta antiga, ignora
        renderizarResultados(itens, termo);
      })
      .catch(() => {});
  }

  input.addEventListener('input', () => {
    clearTimeout(buscaTimer);
    buscaTimer = setTimeout(buscar, 250);
  });

  input.addEventListener('keydown', (evento) => {
    if (evento.key === 'Enter') {
      evento.preventDefault();
      const termo = input.value.trim();
      window.location.href = termo ? `/catalogo?q=${encodeURIComponent(termo)}` : '/catalogo';
    } else if (evento.key === 'Escape') {
      esconderResultados();
    }
  });

  document.addEventListener('click', (evento) => {
    if (evento.target !== input && !resultados.contains(evento.target)) {
      esconderResultados();
    }
  });
})();
