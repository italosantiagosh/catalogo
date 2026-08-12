function normalizar(texto) {
  return texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim();
}

(function () {
  const input = document.getElementById('busca');
  const grid = document.getElementById('grid-produtos');
  const contagem = document.getElementById('contagem');
  const semResultado = document.getElementById('sem-resultado');
  if (!input || !grid) return;

  const cards = Array.from(grid.querySelectorAll('.card-produto')).map((card) => ({
    el: card,
    nome: normalizar(card.dataset.nome || ''),
  }));

  function atualizarContagem(visiveis) {
    if (!contagem) return;
    contagem.textContent = visiveis === cards.length
      ? `${cards.length} santos e devoções`
      : `${visiveis} de ${cards.length} santos e devoções`;
  }

  function filtrar() {
    const termo = normalizar(input.value);
    let visiveis = 0;
    for (const card of cards) {
      const bate = termo === '' || card.nome.includes(termo);
      card.el.hidden = !bate;
      if (bate) visiveis += 1;
    }
    atualizarContagem(visiveis);
    if (semResultado) semResultado.hidden = visiveis !== 0;
  }

  input.addEventListener('input', filtrar);
  filtrar();
})();
