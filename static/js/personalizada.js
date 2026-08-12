(function () {
  const input = document.getElementById('input-imagem');
  const nomeDiv = document.getElementById('nome-arquivo');
  const botao = document.getElementById('botao-enviar');
  const form = document.getElementById('form-upload');

  if (input) {
    input.addEventListener('change', () => {
      if (input.files.length === 0) {
        nomeDiv.textContent = '';
        botao.disabled = true;
        botao.textContent = 'Selecione uma imagem primeiro';
        return;
      }
      nomeDiv.textContent = input.files[0].name;
      botao.disabled = false;
      botao.textContent = 'Gerar simulação';
    });
  }

  if (form) {
    form.addEventListener('submit', () => {
      botao.disabled = true;
      botao.textContent = 'Gerando simulação...';
    });
  }

  const qtdMenos = document.getElementById('qtd-menos');
  const qtdMais = document.getElementById('qtd-mais');
  const quantidadeInput = document.getElementById('sel-quantidade');

  function ajustarQuantidade(delta) {
    const atual = parseInt(quantidadeInput.value, 10) || 1;
    quantidadeInput.value = Math.max(1, atual + delta);
  }

  if (qtdMenos) qtdMenos.addEventListener('click', () => ajustarQuantidade(-1));
  if (qtdMais) qtdMais.addEventListener('click', () => ajustarQuantidade(1));

  // adicionar ao carrinho -- a simulacao em si (preview_src) pode ser um
  // PNG grande demais pra guardar em localStorage sem risco de estourar a
  // cota; gera uma miniatura JPEG pequena so pra referencia visual no
  // carrinho (nao e o arquivo final de producao, so preview de sessao).
  function gerarMiniatura(imgEl, ladoMax) {
    const escala = Math.min(1, ladoMax / Math.max(imgEl.naturalWidth, imgEl.naturalHeight));
    const largura = Math.round(imgEl.naturalWidth * escala);
    const altura = Math.round(imgEl.naturalHeight * escala);
    const canvas = document.createElement('canvas');
    canvas.width = largura;
    canvas.height = altura;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, largura, altura);
    ctx.drawImage(imgEl, 0, 0, largura, altura);
    return canvas.toDataURL('image/jpeg', 0.8);
  }

  const btnAdicionar = document.getElementById('btn-adicionar');
  const painel = document.getElementById('painel-selecao');
  const previewImg = document.getElementById('preview-imagem');

  if (btnAdicionar && painel && previewImg) {
    btnAdicionar.addEventListener('click', () => {
      const quantidade = Math.max(1, parseInt(quantidadeInput.value, 10) || 1);
      const tamanho = painel.dataset.tamanho;

      carrinhoAdicionarItem({
        chave: `personalizada-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        tipo: 'personalizada',
        produtoNome: 'Medalha Personalizada',
        modeloNome: null,
        imagem: gerarMiniatura(previewImg, 320),
        tamanho,
        quantidade,
      });

      const textoOriginal = 'Adicionar ao carrinho';
      btnAdicionar.textContent = 'Adicionado ✓';
      setTimeout(() => {
        btnAdicionar.textContent = textoOriginal;
      }, 1200);
    });
  }
})();
