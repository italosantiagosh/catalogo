(function () {
  const grid = document.getElementById('modelos-grid');
  const painel = document.getElementById('painel-selecao');
  const nomeSpan = document.getElementById('sel-modelo-nome');
  const previewImg = document.getElementById('sel-preview-imagem');
  const formatosFieldset = document.getElementById('sel-formatos');
  const tamanhosFieldset = document.getElementById('sel-tamanhos');
  const coresFieldset = document.getElementById('sel-cores');
  const avisoPreco = document.getElementById('aviso-preco-atacado');
  const quantidadeInput = document.getElementById('sel-quantidade');
  const qtdMenos = document.getElementById('qtd-menos');
  const qtdMais = document.getElementById('qtd-mais');
  const btnAdicionar = document.getElementById('btn-adicionar');
  const barraFixa = document.getElementById('barra-fixa-comprar');
  const barraFixaPreco = document.getElementById('barra-fixa-preco');
  const barraFixaBtn = document.getElementById('barra-fixa-btn-adicionar');
  if (!grid || !painel) return;

  const produtoId = grid.dataset.produtoId;
  const produtoNome = grid.dataset.produtoNome;
  let modeloSelecionado = null;

  function formatarPrecoLocal(valor) {
    return 'R$ ' + valor.toFixed(2).replace('.', ',');
  }

  function formatoAtual() {
    const input = formatosFieldset.querySelector('input[name="formato"]:checked');
    return input ? input.value : 'medalha';
  }

  function atualizarAvisoPreco() {
    if (!avisoPreco) return;
    const formato = formatoAtual();
    const preco = formato === 'chaveiro' ? window.PRECO_VAREJO_CHAVEIRO : window.PRECO_VAREJO_PADRAO;
    avisoPreco.innerHTML =
      `Preço unitário a partir de <strong>${formatarPrecoLocal(preco)}</strong>. ` +
      'O desconto de atacado é calculado automaticamente pela quantidade total ' +
      'do seu carrinho, assim que você adicionar os itens.';
  }

  // qual imagem mostrar pro formato/cor escolhidos -- entremeio sem cor
  // ainda marcada usa prata como previa provisoria (a cor so afeta a
  // previa, o preco/chave ja e "entremeio" nos dois casos).
  function imagemParaFormato() {
    if (!modeloSelecionado) return null;
    const formato = formatoAtual();
    if (formato === 'medalha') return modeloSelecionado.imagens.medalha;
    if (formato === 'chaveiro') return modeloSelecionado.imagens.chaveiro;
    const cor = coresFieldset.querySelector('input[name="cor"]:checked');
    return cor && cor.value === 'ouro_velho'
      ? modeloSelecionado.imagens.entremeio_ouro_velho
      : modeloSelecionado.imagens.entremeio_prata;
  }

  function atualizarPreview() {
    if (!previewImg || !modeloSelecionado) return;
    previewImg.src = imagemParaFormato();
    previewImg.alt = `${produtoNome} — ${modeloSelecionado.nome}`;
  }

  function atualizarInfoFormato() {
    const formato = formatoAtual();
    for (const nome of ['medalha', 'entremeio', 'chaveiro']) {
      const bloco = document.getElementById(`formato-info-${nome}`);
      if (bloco) bloco.hidden = formato !== nome;
    }
  }

  function atualizarSubSelecao() {
    const formato = formatoAtual();
    tamanhosFieldset.hidden = formato !== 'medalha';
    coresFieldset.hidden = formato !== 'entremeio';
    atualizarInfoFormato();
    atualizarAvisoPreco();
    atualizarPreview();
    atualizarBotao();
  }

  function atualizarBotao() {
    const formato = formatoAtual();
    let completo = true;
    if (formato === 'medalha') {
      completo = !!tamanhosFieldset.querySelector('input[name="tamanho"]:checked');
    } else if (formato === 'entremeio') {
      completo = !!coresFieldset.querySelector('input[name="cor"]:checked');
    }
    if (!completo) {
      btnAdicionar.disabled = true;
      btnAdicionar.textContent = formato === 'medalha' ? 'Selecione um tamanho' : 'Selecione uma cor';
    } else {
      btnAdicionar.disabled = false;
      btnAdicionar.textContent = 'Adicionar ao carrinho';
    }

    // barra fixa (mobile, aparece quando o botao real sai da tela --
    // ver IntersectionObserver mais abaixo) espelha o mesmo estado
    if (barraFixaBtn) {
      barraFixaBtn.disabled = btnAdicionar.disabled;
      barraFixaBtn.textContent = btnAdicionar.disabled ? 'Complete a seleção acima' : 'Adicionar ao carrinho';
    }
    if (barraFixaPreco) {
      const preco = formato === 'chaveiro' ? window.PRECO_VAREJO_CHAVEIRO : window.PRECO_VAREJO_PADRAO;
      barraFixaPreco.textContent = `a partir de ${formatarPrecoLocal(preco)}`;
    }
  }

  function selecionarModelo(botao) {
    for (const outro of grid.querySelectorAll('.modelo-card')) {
      outro.setAttribute('aria-pressed', String(outro === botao));
    }

    modeloSelecionado = {
      id: botao.dataset.modeloId,
      nome: botao.dataset.modeloNome,
      imagens: JSON.parse(botao.dataset.imagens || '{}'),
    };
    nomeSpan.textContent = modeloSelecionado.nome;

    // formato sempre volta pra medalha ao trocar de modelo -- evita
    // carregar uma escolha de cor/tamanho que nao fez sentido no modelo novo
    const inputMedalha = formatosFieldset.querySelector('#formato-medalha');
    if (inputMedalha) inputMedalha.checked = true;

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
    for (const input of coresFieldset.querySelectorAll('input[name="cor"]')) {
      input.checked = false;
    }

    painel.hidden = false;
    painel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    atualizarSubSelecao();
  }

  grid.addEventListener('click', (evento) => {
    const botao = evento.target.closest('.modelo-card');
    if (botao) selecionarModelo(botao);
  });

  formatosFieldset.addEventListener('change', (evento) => {
    if (evento.target.name === 'formato') atualizarSubSelecao();
  });

  tamanhosFieldset.addEventListener('change', (evento) => {
    if (evento.target.name === 'tamanho') atualizarBotao();
  });

  coresFieldset.addEventListener('change', (evento) => {
    if (evento.target.name === 'cor') {
      atualizarPreview();
      atualizarBotao();
    }
  });

  function ajustarQuantidade(delta) {
    const atual = parseInt(quantidadeInput.value, 10) || 1;
    quantidadeInput.value = Math.max(1, atual + delta);
  }

  if (qtdMenos) qtdMenos.addEventListener('click', () => ajustarQuantidade(-1));
  if (qtdMais) qtdMais.addEventListener('click', () => ajustarQuantidade(1));

  if (btnAdicionar) {
    btnAdicionar.addEventListener('click', () => {
      if (!modeloSelecionado) return;
      const formato = formatoAtual();

      let chavePreco = null;
      let tamanho = null;
      let cor = null;
      let subAttr = '';
      if (formato === 'medalha') {
        const tamanhoInput = tamanhosFieldset.querySelector('input[name="tamanho"]:checked');
        if (!tamanhoInput) return;
        tamanho = tamanhoInput.value;
        chavePreco = tamanho;
        subAttr = tamanho;
      } else if (formato === 'entremeio') {
        const corInput = coresFieldset.querySelector('input[name="cor"]:checked');
        if (!corInput) return;
        cor = corInput.value;
        chavePreco = 'entremeio';
        subAttr = cor;
      } else {
        chavePreco = 'chaveiro';
      }

      const quantidade = Math.max(1, parseInt(quantidadeInput.value, 10) || 1);
      carrinhoAdicionarItem({
        chave: `${produtoId}-${modeloSelecionado.id}-${formato}-${subAttr}`,
        tipo: 'catalogo',
        produtoId,
        produtoNome,
        modeloId: modeloSelecionado.id,
        modeloNome: modeloSelecionado.nome,
        imagem: imagemParaFormato(),
        formato,
        chave_preco: chavePreco,
        tamanho,
        cor,
        quantidade,
      });

      const textoOriginal = 'Adicionar ao carrinho';
      btnAdicionar.textContent = 'Adicionado ✓';
      setTimeout(() => {
        btnAdicionar.textContent = textoOriginal;
      }, 1200);
    });
  }

  // barra fixa: aparece quando o botao "Adicionar ao carrinho" de
  // verdade sai da tela (rolando pra baixo pra ver mais informacoes) e
  // ja tem um modelo selecionado -- some de novo quando o botao real
  // volta a aparecer. Clicar nela so aciona o botao real (mesma
  // validacao/logica, sem duplicar estado).
  if (barraFixa && btnAdicionar && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      ([entrada]) => {
        barraFixa.hidden = entrada.isIntersecting || painel.hidden;
        document.body.classList.toggle('tem-barra-fixa-comprar', !barraFixa.hidden);
      },
      { threshold: 0 }
    );
    observer.observe(btnAdicionar);
  }

  if (barraFixaBtn) {
    barraFixaBtn.addEventListener('click', () => btnAdicionar.click());
  }

  // seleciona o primeiro modelo automaticamente para quem tem só um --
  // mas tamanho/cor continuam em branco, precisa escolher na mao.
  const primeiro = grid.querySelector('.modelo-card');
  if (primeiro && grid.querySelectorAll('.modelo-card').length === 1) {
    selecionarModelo(primeiro);
  }
})();
