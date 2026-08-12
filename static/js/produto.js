(function () {
  const grid = document.getElementById('modelos-grid');
  const painel = document.getElementById('painel-selecao');
  const nomeSpan = document.getElementById('sel-modelo-nome');
  const tamanhosFieldset = document.getElementById('sel-tamanhos');
  const quantidadeInput = document.getElementById('sel-quantidade');
  const qtdMenos = document.getElementById('qtd-menos');
  const qtdMais = document.getElementById('qtd-mais');
  if (!grid || !painel) return;

  function selecionarModelo(botao) {
    for (const outro of grid.querySelectorAll('.modelo-card')) {
      outro.setAttribute('aria-pressed', String(outro === botao));
    }

    nomeSpan.textContent = botao.dataset.modeloNome;

    const tamanhos = JSON.parse(botao.dataset.tamanhos || '[]');
    tamanhosFieldset.innerHTML = '<legend>Tamanho</legend>';
    tamanhos.forEach((tamanho, i) => {
      const id = `tamanho-${tamanho}`;
      const label = document.createElement('label');
      label.className = 'opcao-tamanho';
      label.innerHTML = `
        <input type="radio" name="tamanho" id="${id}" value="${tamanho}" ${i === 0 ? 'checked' : ''}>
        ${tamanho.replace('mm', ' mm')}
      `;
      tamanhosFieldset.appendChild(label);
    });

    painel.hidden = false;
    painel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  grid.addEventListener('click', (evento) => {
    const botao = evento.target.closest('.modelo-card');
    if (botao) selecionarModelo(botao);
  });

  function ajustarQuantidade(delta) {
    const atual = parseInt(quantidadeInput.value, 10) || 1;
    quantidadeInput.value = Math.max(1, atual + delta);
  }

  if (qtdMenos) qtdMenos.addEventListener('click', () => ajustarQuantidade(-1));
  if (qtdMais) qtdMais.addEventListener('click', () => ajustarQuantidade(1));

  // seleciona o primeiro modelo automaticamente para quem tem só um
  const primeiro = grid.querySelector('.modelo-card');
  if (primeiro && grid.querySelectorAll('.modelo-card').length === 1) {
    selecionarModelo(primeiro);
  }
})();
