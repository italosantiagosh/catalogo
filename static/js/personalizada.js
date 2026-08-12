(function () {
  const PLACEHOLDER_SEM_FOTO = '/static/img/sem-foto.svg';

  // ---- formulario de upload (antes de gerar a simulacao) ----

  const input = document.getElementById('input-imagem');
  const nomeDiv = document.getElementById('nome-arquivo');
  const botaoEnviar = document.getElementById('botao-enviar');
  const form = document.getElementById('form-upload');
  const tamanhosForm = document.getElementById('tamanhos-form');
  const qtdFormInput = document.getElementById('qtd-form');
  const qtdMenosForm = document.getElementById('qtd-menos-form');
  const qtdMaisForm = document.getElementById('qtd-mais-form');
  const btnSemFoto = document.getElementById('btn-sem-foto');

  function tamanhoDoFormulario() {
    const marcado = tamanhosForm ? tamanhosForm.querySelector('input[name="tamanho"]:checked') : null;
    return marcado ? marcado.value : null;
  }

  function atualizarBotaoEnviar() {
    if (!botaoEnviar) return;
    const temArquivo = input && input.files.length > 0;
    const temTamanho = !!tamanhoDoFormulario();
    if (!temArquivo && !temTamanho) {
      botaoEnviar.textContent = 'Selecione uma imagem e o tamanho';
    } else if (!temArquivo) {
      botaoEnviar.textContent = 'Selecione uma imagem';
    } else if (!temTamanho) {
      botaoEnviar.textContent = 'Selecione o tamanho';
    } else {
      botaoEnviar.textContent = 'Gerar simulação';
    }
    botaoEnviar.disabled = !(temArquivo && temTamanho);
  }

  function atualizarBotaoSemFoto() {
    if (!btnSemFoto) return;
    btnSemFoto.disabled = !tamanhoDoFormulario();
  }

  if (input) {
    input.addEventListener('change', () => {
      nomeDiv.textContent = input.files.length > 0 ? input.files[0].name : '';
      atualizarBotaoEnviar();
    });
  }

  if (tamanhosForm) {
    tamanhosForm.addEventListener('change', (evento) => {
      if (evento.target.name === 'tamanho') {
        atualizarBotaoEnviar();
        atualizarBotaoSemFoto();
      }
    });
  }

  function ajustarQuantidadeForm(delta) {
    const atual = parseInt(qtdFormInput.value, 10) || 1;
    qtdFormInput.value = Math.max(1, atual + delta);
  }

  if (qtdMenosForm) qtdMenosForm.addEventListener('click', () => ajustarQuantidadeForm(-1));
  if (qtdMaisForm) qtdMaisForm.addEventListener('click', () => ajustarQuantidadeForm(1));

  if (form) {
    form.addEventListener('submit', () => {
      botaoEnviar.disabled = true;
      botaoEnviar.textContent = 'Gerando simulação...';
    });
  }

  if (btnSemFoto) {
    btnSemFoto.addEventListener('click', () => {
      const tamanho = tamanhoDoFormulario();
      if (!tamanho) return;
      const quantidade = Math.max(1, parseInt(qtdFormInput.value, 10) || 1);

      carrinhoAdicionarItem({
        chave: `personalizada-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        tipo: 'personalizada',
        produtoNome: 'Medalha Personalizada',
        modeloNome: null,
        imagem: PLACEHOLDER_SEM_FOTO,
        tamanho,
        quantidade,
        semImagem: true,
      });

      const textoOriginal = 'Adicionar ao carrinho sem foto (envio depois pelo WhatsApp)';
      btnSemFoto.textContent = 'Adicionado ✓ — não esqueça de enviar a foto depois';
      setTimeout(() => {
        btnSemFoto.textContent = textoOriginal;
      }, 2200);
    });
  }

  atualizarBotaoEnviar();
  atualizarBotaoSemFoto();

  // ---- resultado (depois de gerar a simulacao) ----

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
  const qtdMenos = document.getElementById('qtd-menos');
  const qtdMais = document.getElementById('qtd-mais');
  const quantidadeInput = document.getElementById('sel-quantidade');

  function ajustarQuantidade(delta) {
    const atual = parseInt(quantidadeInput.value, 10) || 1;
    quantidadeInput.value = Math.max(1, atual + delta);
  }

  if (qtdMenos) qtdMenos.addEventListener('click', () => ajustarQuantidade(-1));
  if (qtdMais) qtdMais.addEventListener('click', () => ajustarQuantidade(1));

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
        semImagem: false,
      });

      const textoOriginal = 'Adicionar ao carrinho';
      btnAdicionar.textContent = 'Adicionado ✓';
      setTimeout(() => {
        btnAdicionar.textContent = textoOriginal;
      }, 1200);
    });
  }
})();
