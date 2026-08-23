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
  const filtrosCategoria = document.getElementById('filtros-categoria');
  if (!input || !grid) return;

  const cards = Array.from(grid.querySelectorAll('.card-produto')).map((card) => ({
    el: card,
    nome: normalizar(card.dataset.nome || ''),
    categoria: card.dataset.categoria || '',
  }));

  let categoriaAtual = '';

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
      const bateBusca = termo === '' || card.nome.includes(termo);
      const bateCategoria = categoriaAtual === '' || card.categoria === categoriaAtual;
      const bate = bateBusca && bateCategoria;
      card.el.hidden = !bate;
      if (bate) visiveis += 1;
    }
    atualizarContagem(visiveis);
    if (semResultado) semResultado.hidden = visiveis !== 0;
  }

  input.addEventListener('input', filtrar);

  if (filtrosCategoria) {
    filtrosCategoria.addEventListener('click', (evento) => {
      const chip = evento.target.closest('.chip-categoria');
      if (!chip) return;
      // os chips sao links de verdade pra /categoria/<slug> (SEO -- URL
      // indexavel por categoria), mas com JS ligado o filtro instantaneo
      // na propria pagina continua sendo a experiencia melhor.
      evento.preventDefault();
      categoriaAtual = chip.dataset.categoria || '';
      for (const outro of filtrosCategoria.querySelectorAll('.chip-categoria')) {
        outro.setAttribute('aria-pressed', String(outro === chip));
      }
      filtrar();
    });
  }

  filtrar();
})();
