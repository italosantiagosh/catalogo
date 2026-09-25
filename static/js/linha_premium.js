(function () {
  const botaoAdicionar = document.getElementById('peca-btn-adicionar');
  if (!botaoAdicionar) return;

  const pecaId = botaoAdicionar.dataset.pecaId;
  const formato = botaoAdicionar.dataset.formato;
  const personalizavel = botaoAdicionar.dataset.personalizavel === 'true';
  const preco = parseFloat(botaoAdicionar.dataset.preco);

  function formatarPreco(valor) {
    return 'R$ ' + valor.toFixed(2).replace('.', ',');
  }

  const quantidadeInput = document.getElementById('peca-quantidade');
  const previewEl = document.getElementById('peca-preview-preco');

  // Preco fixo (sem faixa de atacado -- ver GRUPO_DE_CHAVE em
  // services/pricing.py: cada grupo de peca da Linha Premium e´ isolado
  // dos outros de proposito), entao so mostra unidades x subtotal, sem
  // chamada ao /api/carrinho/calcular -- o preco unitario nunca muda.
  function atualizarPreviewPreco() {
    if (!quantidadeInput || !previewEl) return;
    const quantidade = Math.max(1, parseInt(quantidadeInput.value, 10) || 1);
    const subtotal = preco * quantidade;
    previewEl.innerHTML =
      `<strong>${quantidade} unidade${quantidade > 1 ? 's' : ''}</strong> · ${formatarPreco(preco)}/un · ` +
      `subtotal <strong>${formatarPreco(subtotal)}</strong>`;
    previewEl.hidden = false;
  }

  const btnMenos = document.getElementById('peca-qtd-menos');
  const btnMais = document.getElementById('peca-qtd-mais');
  if (btnMenos) {
    btnMenos.addEventListener('click', () => {
      const atual = parseInt(quantidadeInput.value, 10) || 1;
      quantidadeInput.value = Math.max(1, atual - 1);
      atualizarPreviewPreco();
    });
  }
  if (btnMais) {
    btnMais.addEventListener('click', () => {
      const atual = parseInt(quantidadeInput.value, 10) || 1;
      quantidadeInput.value = atual + 1;
      atualizarPreviewPreco();
    });
  }
  if (quantidadeInput) {
    quantidadeInput.addEventListener('input', atualizarPreviewPreco);
  }

  // ---- personalizacao: foto opcional, SEM gerar previa/mockup (loja nao
  // tem gerador pra relicario ainda, ver services/relicarios.py) -- so
  // reduz a foto num canvas (mesmo teto de lado usado nas fotos de
  // avaliacao, ver app.py:_AVALIACAO_FOTO_LADO_MAXIMO) e guarda como
  // data-URI direto no item do carrinho, pra nao pesar o localStorage
  // nem exigir upload pro servidor antes do pedido existir.
  const FOTO_LADO_MAXIMO = 1000;
  let fotoPersonalizacao = null;

  function reduzirFotoParaDataUri(arquivo) {
    return new Promise((resolve, reject) => {
      const leitor = new FileReader();
      leitor.onerror = () => reject(new Error('Não foi possível ler a foto.'));
      leitor.onload = () => {
        const imagem = new Image();
        imagem.onerror = () => reject(new Error('Não foi possível ler a foto.'));
        imagem.onload = () => {
          const escala = Math.min(1, FOTO_LADO_MAXIMO / Math.max(imagem.width, imagem.height));
          const canvas = document.createElement('canvas');
          canvas.width = Math.round(imagem.width * escala);
          canvas.height = Math.round(imagem.height * escala);
          const ctx = canvas.getContext('2d');
          ctx.drawImage(imagem, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL('image/jpeg', 0.82));
        };
        imagem.src = leitor.result;
      };
      leitor.readAsDataURL(arquivo);
    });
  }

  const inputFotoPersonalizacao = document.getElementById('personalizacao-foto');
  if (inputFotoPersonalizacao) {
    const bloco = inputFotoPersonalizacao.closest('[data-personalizacao]');
    const preview = bloco ? bloco.querySelector('[data-personalizacao-preview]') : null;
    const previewImg = bloco ? bloco.querySelector('[data-personalizacao-preview-img]') : null;
    const removerBtn = bloco ? bloco.querySelector('[data-personalizacao-remover]') : null;

    inputFotoPersonalizacao.addEventListener('change', async () => {
      const arquivo = inputFotoPersonalizacao.files[0];
      if (!arquivo) return;
      try {
        fotoPersonalizacao = await reduzirFotoParaDataUri(arquivo);
        if (previewImg) previewImg.src = fotoPersonalizacao;
        if (preview) preview.hidden = false;
      } catch (e) {
        fotoPersonalizacao = null;
      }
    });

    if (removerBtn) {
      removerBtn.addEventListener('click', () => {
        fotoPersonalizacao = null;
        inputFotoPersonalizacao.value = '';
        if (preview) preview.hidden = true;
      });
    }
  }

  // ---- compre junto: checkbox que adiciona a corrente junto da peca no
  // mesmo clique (preco cheio dos dois, sem desconto de combo -- ver
  // conversa 2026-09-25) ----
  const checkboxCorrente = document.getElementById('compre-junto-checkbox');

  function adicionarCorrenteAoCarrinho() {
    if (!checkboxCorrente) return;
    const quantidade = 1;
    carrinhoAdicionarItem({
      chave: `corrente-${checkboxCorrente.dataset.correnteChavePreco}`,
      tipo: 'catalogo',
      produtoId: checkboxCorrente.dataset.correnteChavePreco,
      produtoNome: checkboxCorrente.dataset.correnteNome,
      modeloId: '',
      modeloNome: '',
      imagem: checkboxCorrente.dataset.correnteImagem,
      formato: 'corrente',
      chave_preco: checkboxCorrente.dataset.correnteChavePreco,
      tamanho: '',
      cor: null,
      quantidade,
    });
    rastrearEventoGA4('add_to_cart', {
      item_id: checkboxCorrente.dataset.correnteChavePreco,
      value: parseFloat(checkboxCorrente.dataset.correntePreco),
      currency: 'BRL',
      quantity: quantidade,
    });
  }

  // ---- popup de upsell: se a peca tem corrente companheira e o cliente
  // NAO marcou o checkbox de "compre junto", oferece de novo logo depois
  // de adicionar (ver templates/linha_premium_item.html) ----
  const upsellModal = document.getElementById('upsell-modal');
  const upsellFechar = document.getElementById('upsell-modal-fechar');
  const upsellImagem = document.getElementById('upsell-modal-imagem');
  const upsellNome = document.getElementById('upsell-modal-nome');
  const upsellPreco = document.getElementById('upsell-modal-preco');
  const upsellBtnAdicionar = document.getElementById('upsell-modal-adicionar');
  const upsellBtnRecusar = document.getElementById('upsell-modal-recusar');

  function fecharUpsellModal() {
    if (upsellModal) upsellModal.hidden = true;
  }

  function abrirUpsellModal() {
    if (!upsellModal || !upsellImagem || !upsellNome || !upsellPreco || !checkboxCorrente) return;
    upsellImagem.src = checkboxCorrente.dataset.correnteImagem;
    upsellImagem.alt = checkboxCorrente.dataset.correnteNome;
    upsellNome.textContent = checkboxCorrente.dataset.correnteNome;
    upsellPreco.textContent = formatarPreco(parseFloat(checkboxCorrente.dataset.correntePreco));
    upsellModal.hidden = false;

    const aoAdicionar = () => {
      adicionarCorrenteAoCarrinho();
      checkboxCorrente.checked = true;
      fecharUpsellModal();
      if (typeof carrinhoAtualizarContador === 'function') carrinhoAtualizarContador();
      if (typeof carrinhoAtualizarBarraPersistente === 'function') carrinhoAtualizarBarraPersistente();
      upsellBtnAdicionar.removeEventListener('click', aoAdicionar);
      upsellBtnRecusar.removeEventListener('click', aoRecusar);
    };
    const aoRecusar = () => {
      fecharUpsellModal();
      upsellBtnAdicionar.removeEventListener('click', aoAdicionar);
      upsellBtnRecusar.removeEventListener('click', aoRecusar);
    };
    if (upsellBtnAdicionar) upsellBtnAdicionar.addEventListener('click', aoAdicionar);
    if (upsellBtnRecusar) upsellBtnRecusar.addEventListener('click', aoRecusar);
  }

  if (upsellFechar) upsellFechar.addEventListener('click', fecharUpsellModal);
  if (upsellModal) {
    upsellModal.addEventListener('click', (evento) => {
      if (evento.target === upsellModal) fecharUpsellModal();
    });
  }

  atualizarPreviewPreco();
  rastrearEventoGA4('view_item', { item_id: pecaId, item_name: botaoAdicionar.dataset.nome, value: preco, currency: 'BRL' });

  botaoAdicionar.addEventListener('click', () => {
    const quantidade = quantidadeInput ? Math.max(1, parseInt(quantidadeInput.value, 10) || 1) : 1;

    const item = {
      chave: `${formato}-${pecaId}`,
      tipo: 'catalogo',
      produtoId: pecaId,
      produtoNome: botaoAdicionar.dataset.nome,
      modeloId: '',
      modeloNome: '',
      imagem: botaoAdicionar.dataset.imagem,
      formato,
      chave_preco: botaoAdicionar.dataset.chavePreco,
      tamanho: '',
      cor: null,
      quantidade,
    };
    if (personalizavel) {
      item.personalizavel = true;
      if (fotoPersonalizacao) item.personalizacaoFoto = fotoPersonalizacao;
    }
    carrinhoAdicionarItem(item);

    if (checkboxCorrente && checkboxCorrente.checked) adicionarCorrenteAoCarrinho();

    if (typeof carrinhoAtualizarContador === 'function') carrinhoAtualizarContador();
    if (typeof carrinhoAtualizarBarraPersistente === 'function') carrinhoAtualizarBarraPersistente();
    rastrearEventoGA4('add_to_cart', { item_id: pecaId, value: preco, currency: 'BRL', quantity: quantidade });
    atualizarPreviewPreco();

    const textoOriginal = botaoAdicionar.textContent;
    botaoAdicionar.textContent = 'Adicionado ✓';
    setTimeout(() => {
      botaoAdicionar.textContent = textoOriginal;
    }, 1200);

    // Se tem corrente companheira e o cliente nao marcou o "compre
    // junto" antes de clicar, oferece de novo no popup (ver conversa:
    // "aparecer popup upsell quando adicionar o relicário no carrinho").
    if (checkboxCorrente && !checkboxCorrente.checked) {
      abrirUpsellModal();
    }
  });
})();
