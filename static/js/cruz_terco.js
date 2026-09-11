(function () {
  const imagemFrenteEl = document.getElementById('cruz-imagem-frente');
  const imagemPerfilEl = document.getElementById('cruz-imagem-perfil');
  const coresFieldset = document.getElementById('cruz-cores');
  const quantidadeInput = document.getElementById('cruz-quantidade');
  const qtdMenos = document.getElementById('cruz-qtd-menos');
  const qtdMais = document.getElementById('cruz-qtd-mais');
  const previewPrecoEl = document.getElementById('cruz-preview-preco');
  const btnAdicionar = document.getElementById('cruz-btn-adicionar');
  if (!coresFieldset || !btnAdicionar) return;

  function formatarPreco(valor) {
    return 'R$ ' + valor.toFixed(2).replace('.', ',');
  }

  function corSelecionada() {
    return coresFieldset.querySelector('input[name="cruz-cor"]:checked');
  }

  function atualizarImagem() {
    const input = corSelecionada();
    if (!input) return;
    if (imagemFrenteEl) imagemFrenteEl.src = input.dataset.imagem;
    if (imagemPerfilEl) imagemPerfilEl.src = input.dataset.imagemPerfil;
  }

  async function atualizarPreviewPreco() {
    const input = corSelecionada();
    if (!input || !previewPrecoEl) return;
    const chavePreco = input.dataset.chavePreco;
    const quantidade = Math.max(1, parseInt(quantidadeInput.value, 10) || 1);

    const itens = carrinhoObterItens().map((item) => ({
      chave_preco: item.chave_preco,
      quantidade: item.quantidade,
    }));
    itens.push({ chave_preco: chavePreco, quantidade });

    try {
      const resposta = await fetch('/api/carrinho/calcular', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ itens }),
      });
      const dados = await resposta.json();
      const itemPreview = dados.itens[dados.itens.length - 1];

      // preco fixo (sem faixa de atacado propria -- ver GRUPO_DE_CHAVE em
      // services/pricing.py: "cruz_terco" e´ isolado dos outros grupos de
      // proposito, pra nao interferir no desconto de medalhas/entremeios),
      // entao aqui so mostra unidades/subtotal, sem "faltam X pra cair".
      previewPrecoEl.innerHTML =
        `<strong>${quantidade} unidades</strong> · ${formatarPreco(itemPreview.preco_unitario)}/un · ` +
        `subtotal <strong>${formatarPreco(itemPreview.subtotal)}</strong>`;
      previewPrecoEl.hidden = false;
    } catch (e) {
      previewPrecoEl.hidden = true;
    }
  }

  coresFieldset.addEventListener('change', (evento) => {
    if (evento.target.name === 'cruz-cor') {
      atualizarImagem();
      atualizarPreviewPreco();
      rastrearEventoGA4('select_item_variant', { item_id: 'cruz-para-terco', cor: evento.target.value });
    }
  });

  function ajustarQuantidade(delta) {
    const atual = parseInt(quantidadeInput.value, 10) || 1;
    quantidadeInput.value = Math.max(1, atual + delta);
    atualizarPreviewPreco();
  }
  qtdMenos.addEventListener('click', () => ajustarQuantidade(-1));
  qtdMais.addEventListener('click', () => ajustarQuantidade(1));
  quantidadeInput.addEventListener('input', atualizarPreviewPreco);

  btnAdicionar.addEventListener('click', () => {
    const input = corSelecionada();
    if (!input) return;
    const cor = input.value;
    const chavePreco = input.dataset.chavePreco;
    const quantidade = Math.max(1, parseInt(quantidadeInput.value, 10) || 1);

    carrinhoAdicionarItem({
      chave: `cruz-terco-${cor}`,
      tipo: 'catalogo',
      produtoId: 'cruz-para-terco',
      produtoNome: 'Cruz para Terço',
      modeloId: '',
      modeloNome: '',
      imagem: input.dataset.imagem,
      formato: 'cruz_terco',
      chave_preco: chavePreco,
      tamanho: '',
      cor,
      quantidade,
    });

    if (typeof carrinhoAtualizarContador === 'function') carrinhoAtualizarContador();
    if (typeof carrinhoAtualizarBarraPersistente === 'function') carrinhoAtualizarBarraPersistente();
    atualizarPreviewPreco();

    const textoOriginal = 'Adicionar ao carrinho';
    btnAdicionar.textContent = 'Adicionado ✓';
    setTimeout(() => {
      btnAdicionar.textContent = textoOriginal;
    }, 1200);
  });

  rastrearEventoGA4('view_item', { item_id: 'cruz-para-terco', item_name: 'Cruz para Terço' });
  atualizarPreviewPreco();
})();
