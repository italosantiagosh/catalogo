(function () {
  const botoesAdicionar = document.querySelectorAll('.relicario-btn-adicionar');
  if (botoesAdicionar.length === 0) return;

  function formatarPreco(valor) {
    return 'R$ ' + valor.toFixed(2).replace('.', ',');
  }

  function quantidadeInputDe(relicarioId) {
    return document.getElementById(`relicario-quantidade-${relicarioId}`);
  }

  // Preco fixo (sem faixa de atacado -- ver GRUPO_DE_CHAVE em
  // services/pricing.py: "relicarios"/"correntes" sao isolados dos
  // outros grupos de proposito, mesmo padrao de colares/pulseiras),
  // entao so mostra unidades x subtotal, sem chamada ao
  // /api/carrinho/calcular -- o preco unitario nunca muda.
  function atualizarPreviewPreco(relicarioId, preco) {
    const quantidadeInput = quantidadeInputDe(relicarioId);
    const previewEl = document.getElementById(`relicario-preview-preco-${relicarioId}`);
    if (!quantidadeInput || !previewEl) return;
    const quantidade = Math.max(1, parseInt(quantidadeInput.value, 10) || 1);
    const subtotal = preco * quantidade;
    previewEl.innerHTML =
      `<strong>${quantidade} unidade${quantidade > 1 ? 's' : ''}</strong> · ${formatarPreco(preco)}/un · ` +
      `subtotal <strong>${formatarPreco(subtotal)}</strong>`;
    previewEl.hidden = false;
  }

  document.querySelectorAll('.relicario-qtd-menos, .relicario-qtd-mais').forEach((botao) => {
    botao.addEventListener('click', () => {
      const relicarioId = botao.dataset.relicario;
      const quantidadeInput = quantidadeInputDe(relicarioId);
      if (!quantidadeInput) return;
      const delta = botao.classList.contains('relicario-qtd-mais') ? 1 : -1;
      const atual = parseInt(quantidadeInput.value, 10) || 1;
      quantidadeInput.value = Math.max(1, atual + delta);
      const btnAdicionar = document.querySelector(`.relicario-btn-adicionar[data-relicario="${relicarioId}"]`);
      if (btnAdicionar) atualizarPreviewPreco(relicarioId, parseFloat(btnAdicionar.dataset.preco));
    });
  });

  document.querySelectorAll('.relicario-quantidade').forEach((input) => {
    input.addEventListener('input', () => {
      const relicarioId = input.id.replace('relicario-quantidade-', '');
      const btnAdicionar = document.querySelector(`.relicario-btn-adicionar[data-relicario="${relicarioId}"]`);
      if (btnAdicionar) atualizarPreviewPreco(relicarioId, parseFloat(btnAdicionar.dataset.preco));
    });
  });

  // ---- personalizacao: foto opcional, SEM gerar previa/mockup (loja nao
  // tem gerador pra relicario ainda, ver services/relicarios.py) -- so
  // reduz a foto num canvas (mesmo teto de lado usado nas fotos de
  // avaliacao, ver app.py:_AVALIACAO_FOTO_LADO_MAXIMO) e guarda como
  // data-URI direto no item do carrinho, pra nao pesar o localStorage
  // nem exigir upload pro servidor antes do pedido existir.
  const FOTO_LADO_MAXIMO = 1000;
  const fotosPersonalizacao = {};

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

  document.querySelectorAll('.personalizacao-input').forEach((input) => {
    const relicarioId = input.dataset.relicario;
    const bloco = input.closest('[data-personalizacao]');
    const preview = bloco ? bloco.querySelector('[data-personalizacao-preview]') : null;
    const previewImg = bloco ? bloco.querySelector('[data-personalizacao-preview-img]') : null;
    const removerBtn = bloco ? bloco.querySelector('[data-personalizacao-remover]') : null;

    input.addEventListener('change', async () => {
      const arquivo = input.files[0];
      if (!arquivo) return;
      try {
        const dataUri = await reduzirFotoParaDataUri(arquivo);
        fotosPersonalizacao[relicarioId] = dataUri;
        if (previewImg) previewImg.src = dataUri;
        if (preview) preview.hidden = false;
      } catch (e) {
        delete fotosPersonalizacao[relicarioId];
      }
    });

    if (removerBtn) {
      removerBtn.addEventListener('click', () => {
        delete fotosPersonalizacao[relicarioId];
        input.value = '';
        if (preview) preview.hidden = true;
      });
    }
  });

  // ---- compre junto: checkbox que adiciona a corrente junto do
  // relicario no mesmo clique (preco cheio dos dois, sem desconto de
  // combo -- ver conversa 2026-09-25) ----
  function correnteSelecionada(relicarioId) {
    const checkbox = document.querySelector(`.compre-junto-checkbox[data-relicario="${relicarioId}"]`);
    return checkbox && checkbox.checked ? checkbox : null;
  }

  function adicionarCorrenteAoCarrinho(checkbox) {
    const quantidade = 1;
    carrinhoAdicionarItem({
      chave: `corrente-${checkbox.dataset.correnteChavePreco}`,
      tipo: 'catalogo',
      produtoId: checkbox.dataset.correnteChavePreco,
      produtoNome: checkbox.dataset.correnteNome,
      modeloId: '',
      modeloNome: '',
      imagem: checkbox.dataset.correnteImagem,
      formato: 'corrente',
      chave_preco: checkbox.dataset.correnteChavePreco,
      tamanho: '',
      cor: null,
      quantidade,
    });
    rastrearEventoGA4('add_to_cart', {
      item_id: checkbox.dataset.correnteChavePreco,
      value: parseFloat(checkbox.dataset.correntePreco),
      currency: 'BRL',
      quantity: quantidade,
    });
  }

  // ---- popup de upsell: se o relicario tem corrente companheira e o
  // cliente NAO marcou o checkbox de "compre junto", oferece de novo
  // logo depois de adicionar (ver templates/relicarios.html) ----
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

  function abrirUpsellModal(checkbox) {
    if (!upsellModal || !upsellImagem || !upsellNome || !upsellPreco) return;
    upsellImagem.src = checkbox.dataset.correnteImagem;
    upsellImagem.alt = checkbox.dataset.correnteNome;
    upsellNome.textContent = checkbox.dataset.correnteNome;
    upsellPreco.textContent = formatarPreco(parseFloat(checkbox.dataset.correntePreco));
    upsellModal.hidden = false;

    const aoAdicionar = () => {
      adicionarCorrenteAoCarrinho(checkbox);
      checkbox.checked = true;
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

  botoesAdicionar.forEach((botao) => {
    const relicarioId = botao.dataset.relicario;
    const preco = parseFloat(botao.dataset.preco);
    const personalizavel = botao.dataset.personalizavel === 'true';
    atualizarPreviewPreco(relicarioId, preco);
    rastrearEventoGA4('view_item', { item_id: relicarioId, item_name: botao.dataset.nome, value: preco, currency: 'BRL' });

    botao.addEventListener('click', () => {
      const quantidadeInput = quantidadeInputDe(relicarioId);
      const quantidade = quantidadeInput ? Math.max(1, parseInt(quantidadeInput.value, 10) || 1) : 1;

      const item = {
        chave: `relicario-${relicarioId}`,
        tipo: 'catalogo',
        produtoId: relicarioId,
        produtoNome: botao.dataset.nome,
        modeloId: '',
        modeloNome: '',
        imagem: botao.dataset.imagem,
        formato: 'relicario',
        chave_preco: botao.dataset.chavePreco,
        tamanho: '',
        cor: null,
        quantidade,
      };
      if (personalizavel) {
        item.personalizavel = true;
        if (fotosPersonalizacao[relicarioId]) item.personalizacaoFoto = fotosPersonalizacao[relicarioId];
      }
      carrinhoAdicionarItem(item);

      const checkbox = correnteSelecionada(relicarioId);
      if (checkbox) adicionarCorrenteAoCarrinho(checkbox);

      if (typeof carrinhoAtualizarContador === 'function') carrinhoAtualizarContador();
      if (typeof carrinhoAtualizarBarraPersistente === 'function') carrinhoAtualizarBarraPersistente();
      rastrearEventoGA4('add_to_cart', { item_id: relicarioId, value: preco, currency: 'BRL', quantity: quantidade });
      atualizarPreviewPreco(relicarioId, preco);

      const textoOriginal = botao.textContent;
      botao.textContent = 'Adicionado ✓';
      setTimeout(() => {
        botao.textContent = textoOriginal;
      }, 1200);

      // Se tem corrente companheira e o cliente nao marcou o "compre
      // junto" antes de clicar, oferece de novo no popup (ver conversa:
      // "aparecer popup upsell quando adicionar o relicário no carrinho").
      const checkboxCorrente = document.querySelector(`.compre-junto-checkbox[data-relicario="${relicarioId}"]`);
      if (checkboxCorrente && !checkboxCorrente.checked) {
        abrirUpsellModal(checkboxCorrente);
      }
    });
  });
})();
