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
  const previewPrecoEl = document.getElementById('preview-preco');
  if (!grid || !painel) return;

  const produtoId = grid.dataset.produtoId;
  const produtoNome = grid.dataset.produtoNome;
  let modeloSelecionado = null;

  rastrearEventoGA4('view_product', { item_id: produtoId, item_name: produtoNome });

  function formatarPrecoLocal(valor) {
    return 'R$ ' + valor.toFixed(2).replace('.', ',');
  }

  function formatoAtual() {
    const input = formatosFieldset.querySelector('input[name="formato"]:checked');
    return input ? input.value : 'medalha';
  }

  // resolve a chave_preco (12mm/16mm/entremeio/chaveiro) a partir do
  // formato/tamanho/cor escolhidos -- null se a selecao ainda esta
  // incompleta. Compartilhado entre o botao de adicionar e o preview
  // de preco (evita duplicar a mesma logica de branching duas vezes).
  function resolverChavePreco() {
    const formato = formatoAtual();
    if (formato === 'medalha') {
      const tamanhoInput = tamanhosFieldset.querySelector('input[name="tamanho"]:checked');
      if (!tamanhoInput) return null;
      return { chavePreco: tamanhoInput.value, tamanho: tamanhoInput.value, cor: null, subAttr: tamanhoInput.value };
    }
    if (formato === 'entremeio') {
      const corInput = coresFieldset.querySelector('input[name="cor"]:checked');
      if (!corInput) return null;
      return { chavePreco: 'entremeio', tamanho: null, cor: corInput.value, subAttr: corInput.value };
    }
    return { chavePreco: 'chaveiro', tamanho: null, cor: null, subAttr: '' };
  }

  // preview de preco real: junta o carrinho ATUAL (localStorage) com o
  // item que esta sendo configurado agora (ainda sem adicionar) e manda
  // pro mesmo endpoint que calcula o carrinho de verdade -- mostra
  // preco/subtotal reais e o impacto na faixa de atacado ANTES de
  // clicar em adicionar (pedido: preco deveria aparecer imediatamente
  // apos cada selecao, nao so um "a partir de" generico).
  async function atualizarPreviewPreco() {
    if (!previewPrecoEl) return;
    const resolvido = resolverChavePreco();
    if (!resolvido) {
      previewPrecoEl.hidden = true;
      return;
    }
    const quantidade = Math.max(1, parseInt(quantidadeInput.value, 10) || 1);
    const itens = carrinhoObterItens().map((item) => ({
      chave_preco: item.chave_preco,
      quantidade: item.quantidade,
    }));
    itens.push({ chave_preco: resolvido.chavePreco, quantidade });

    try {
      const resposta = await fetch('/api/carrinho/calcular', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ itens }),
      });
      const dados = await resposta.json();
      const itemPreview = dados.itens[dados.itens.length - 1];
      const grupoNome = GRUPO_DE_CHAVE[resolvido.chavePreco];
      const grupo = dados.grupos[grupoNome];
      const rotuloGrupo = GRUPO_LABEL[grupoNome] || grupoNome;

      let html =
        `<strong>${quantidade} unidades</strong> · ${formatarPreco(itemPreview.preco_unitario)}/un · ` +
        `subtotal <strong>${formatarPreco(itemPreview.subtotal)}</strong>`;
      if (grupo.proxima_faixa) {
        html +=
          `<br>Seu carrinho ficará com ${grupo.quantidade_total} ${rotuloGrupo} — faltam ` +
          `${grupo.proxima_faixa.faltam} para cair para ${formatarPreco(grupo.proxima_faixa.preco)}/un`;
        if (grupo.proxima_faixa.economia > 0) {
          html += ` (economia de ${formatarPreco(grupo.proxima_faixa.economia)} no pedido)`;
        }
      } else {
        html += `<br>🎉 Essa já é a melhor faixa de preço de ${rotuloGrupo}!`;
      }
      previewPrecoEl.innerHTML = html;
      previewPrecoEl.hidden = false;
    } catch (e) {
      previewPrecoEl.hidden = true;
    }
  }

  let previewPrecoTimer = null;
  function agendarAtualizarPreviewPreco() {
    clearTimeout(previewPrecoTimer);
    previewPrecoTimer = setTimeout(atualizarPreviewPreco, 300);
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
    atualizarPreviewPreco();
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
    rastrearEventoGA4('select_model', {
      item_id: produtoId,
      item_name: produtoNome,
      modelo: modeloSelecionado.nome,
    });

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
    if (evento.target.name === 'formato') {
      atualizarSubSelecao();
      rastrearEventoGA4('select_format', {
        item_id: produtoId,
        item_name: produtoNome,
        formato: evento.target.value,
      });
    }
  });

  tamanhosFieldset.addEventListener('change', (evento) => {
    if (evento.target.name === 'tamanho') {
      atualizarBotao();
      atualizarPreviewPreco();
      rastrearEventoGA4('select_size', {
        item_id: produtoId,
        item_name: produtoNome,
        tamanho: evento.target.value,
      });
    }
  });

  coresFieldset.addEventListener('change', (evento) => {
    if (evento.target.name === 'cor') {
      atualizarPreview();
      atualizarBotao();
      atualizarPreviewPreco();
    }
  });

  function ajustarQuantidade(delta) {
    const atual = parseInt(quantidadeInput.value, 10) || 1;
    quantidadeInput.value = Math.max(1, atual + delta);
    atualizarPreviewPreco();
  }

  if (qtdMenos) qtdMenos.addEventListener('click', () => ajustarQuantidade(-1));
  if (qtdMais) qtdMais.addEventListener('click', () => ajustarQuantidade(1));
  if (quantidadeInput) quantidadeInput.addEventListener('input', agendarAtualizarPreviewPreco);

  if (btnAdicionar) {
    btnAdicionar.addEventListener('click', () => {
      if (!modeloSelecionado) return;
      const formato = formatoAtual();
      const resolvido = resolverChavePreco();
      if (!resolvido) return;
      const { chavePreco, tamanho, cor, subAttr } = resolvido;

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

      // atualiza contador/barra do topo (visivel em toda pagina) na
      // hora -- sem isso so refletia depois de recarregar a pagina.
      if (typeof carrinhoAtualizarContador === 'function') carrinhoAtualizarContador();
      if (typeof carrinhoAtualizarBarraPersistente === 'function') carrinhoAtualizarBarraPersistente();
      atualizarPreviewPreco();

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
