(function () {
  "use strict";

  const CROPPER_SIZE = 320;
  const RAIO = CROPPER_SIZE / 2;
  const ZOOM_MAX_MULT = 4;

  const viewUpload = document.getElementById('view-upload');
  const opcaoSemFoto = document.getElementById('opcao-sem-foto');
  const viewCropper = document.getElementById('view-cropper');
  const viewPreview = document.getElementById('view-preview');
  const viewPreviewDuasFaces = document.getElementById('view-preview-duas-faces');
  const bannerErro = document.getElementById('banner-erro');
  const avisoPreco = document.getElementById('aviso-preco-atacado');

  const formatosFieldset = document.getElementById('sel-formatos');
  const tamanhosFieldset = document.getElementById('sel-tamanhos');
  const coresFieldset = document.getElementById('sel-cores');
  const dropzoneImagem = document.getElementById('dropzone-imagem');
  const inputImagem = document.getElementById('input-imagem');
  const nomeArquivoDiv = document.getElementById('nome-arquivo');
  const quantidadeUploadDiv = document.getElementById('quantidade-upload');
  const qtdFormInput = document.getElementById('qtd-form');
  const qtdMenosForm = document.getElementById('qtd-menos-form');
  const qtdMaisForm = document.getElementById('qtd-mais-form');
  const botaoEnviar = document.getElementById('botao-enviar');
  const btnSemFoto = document.getElementById('btn-sem-foto');
  const indicadorLado = document.getElementById('indicador-lado');
  const btnLadoIgual = document.getElementById('btn-lado-igual');
  const escolherCatalogoDiv = document.getElementById('escolher-catalogo');

  if (!viewUpload) return;

  // ---- 2 lados (medalha_2lados / entremeio_2lados): o MESMO fluxo de
  // upload+recorte+previa de baixo e reaproveitado duas vezes seguidas
  // (uma por lado) em vez de duplicar toda a mecanica do cropper -- ver
  // avancarLado()/resetarFluxoDuasFaces() mais abaixo. ----
  let ladoAtual = 1;
  let resultadoLado1 = null;
  let resultadoLado2 = null;

  function formatarPrecoLocal(valor) {
    return 'R$ ' + valor.toFixed(2).replace('.', ',');
  }

  function mostrarErro(msg) {
    bannerErro.textContent = msg;
    bannerErro.hidden = false;
  }

  function limparErro() {
    bannerErro.hidden = true;
    bannerErro.textContent = '';
  }

  function mostrarView(nome) {
    viewUpload.hidden = nome !== 'upload';
    opcaoSemFoto.hidden = nome !== 'upload';
    viewCropper.hidden = nome !== 'cropper';
    viewPreview.hidden = nome !== 'preview';
    viewPreviewDuasFaces.hidden = nome !== 'preview-2f';
    window.scrollTo(0, 0);
  }

  // ---- formato / tamanho / cor (mesmo padrao de produto.js) ----

  function formatoAtual() {
    const input = formatosFieldset.querySelector('input[name="formato"]:checked');
    return input ? input.value : 'medalha';
  }

  function duasFacesAtual() {
    const formato = formatoAtual();
    return formato === 'medalha_2lados' || formato === 'entremeio_2lados' || formato === 'chaveiro_2lados';
  }

  function tamanhoAtual() {
    const input = tamanhosFieldset.querySelector('input[name="tamanho"]:checked');
    return input ? input.value : null;
  }

  function corAtual() {
    const input = coresFieldset.querySelector('input[name="cor"]:checked');
    return input ? input.value : null;
  }

  function subSelecaoCompleta() {
    const formato = formatoAtual();
    if (formato === 'medalha') return !!tamanhoAtual();
    // medalha_2lados tem tamanho (14/18mm, mesmo preco -- so fisico) E
    // cor (prata/ouro velho); entremeio_2lados so cor (mesma base do
    // entremeio de 1 lado, sem opcao de tamanho).
    if (formato === 'medalha_2lados') return !!tamanhoAtual() && !!corAtual();
    if (formato === 'entremeio' || formato === 'entremeio_2lados') return !!corAtual();
    return true;
  }

  function chavePrecoAtual() {
    const formato = formatoAtual();
    if (formato === 'medalha') return tamanhoAtual();
    return formato;
  }

  function atualizarAvisoPreco() {
    if (!avisoPreco) return;
    let preco = window.PRECO_VAREJO_PADRAO;
    // chaveiro_2lados usa o MESMO preco do chaveiro de 1 lado (pedido do
    // usuario: "preço de atacado é igual ao chaveiro de um lado") --
    // precisa vir ANTES do duasFacesAtual() abaixo, senao cairia no
    // preco de medalha/entremeio de 2 lados por engano.
    if (formatoAtual() === 'chaveiro' || formatoAtual() === 'chaveiro_2lados') preco = window.PRECO_VAREJO_CHAVEIRO;
    else if (duasFacesAtual()) preco = window.PRECO_VAREJO_2LADOS;
    avisoPreco.innerHTML =
      `Preço unitário a partir de <strong>${formatarPrecoLocal(preco)}</strong>. ` +
      'O desconto de atacado é calculado automaticamente pela quantidade total ' +
      'do seu carrinho, assim que você adicionar os itens.';
  }

  // ---- 2 lados: reseta o estado do "assistente" (lado 1/lado 2) toda
  // vez que o formato muda -- trocar de formato no meio do fluxo
  // invalidaria o lado ja escolhido (base fisica diferente). ----
  function resetarFluxoDuasFaces() {
    ladoAtual = 1;
    resultadoLado1 = null;
    resultadoLado2 = null;
    atualizarIndicadorLado();
  }

  function atualizarIndicadorLado() {
    // botao "lado 2 e´ igual ao lado 1" so faz sentido depois do lado 1
    // ja escolhido, num item de 2 lados -- ver clique dele mais abaixo.
    if (btnLadoIgual) btnLadoIgual.hidden = !(duasFacesAtual() && ladoAtual === 2);
    if (!indicadorLado) return;
    if (!duasFacesAtual()) {
      indicadorLado.hidden = true;
      return;
    }
    indicadorLado.hidden = false;
    if (ladoAtual === 1) {
      indicadorLado.textContent = 'Lado 1 de 2 — escolha a foto (ou envie depois) desse lado.';
    } else {
      indicadorLado.textContent = '✅ Lado 1 pronto! Agora o Lado 2 — escolha a foto (ou envie depois) desse lado.';
    }
  }

  // Atalho pra quando o lado 2 e´ literalmente a mesma imagem do lado 1
  // (pedido do usuario) -- copia o resultado ja pronto em vez de repetir
  // upload/recorte ou escolha do catalogo, e pula direto pra previa
  // combinada final.
  if (btnLadoIgual) {
    btnLadoIgual.addEventListener('click', () => {
      if (!resultadoLado1) return;
      resultadoLado2 = { ...resultadoLado1 };
      rastrearEventoGA4('lado2_igual_lado1', { formato: formatoAtual() });
      mostrarPreviewDuasFaces();
    });
  }

  // medalha 1 lado usa 12/16mm; medalha_2lados usa 14/18mm (mesmo preco,
  // so o tamanho fisico muda -- ver conversa) -- alterna qual par de
  // radios fica visivel/habilitado dentro do MESMO fieldset #sel-tamanhos.
  const opcoesTamanho1Lado = tamanhosFieldset.querySelectorAll('.opcao-tamanho-1lado');
  const opcoesTamanho2Lados = tamanhosFieldset.querySelectorAll('.opcao-tamanho-2lados');

  function atualizarSubSelecao() {
    const formato = formatoAtual();
    const usar2ladosTamanho = formato === 'medalha_2lados';
    tamanhosFieldset.hidden = formato !== 'medalha' && formato !== 'medalha_2lados';
    coresFieldset.hidden = !(formato === 'entremeio' || formato === 'entremeio_2lados' || formato === 'medalha_2lados');

    opcoesTamanho1Lado.forEach((label) => {
      label.hidden = usar2ladosTamanho;
      label.querySelector('input').disabled = usar2ladosTamanho;
    });
    opcoesTamanho2Lados.forEach((label) => {
      label.hidden = !usar2ladosTamanho;
      label.querySelector('input').disabled = !usar2ladosTamanho;
    });
    if (!tamanhosFieldset.hidden) {
      const parAtivo = usar2ladosTamanho ? opcoesTamanho2Lados : opcoesTamanho1Lado;
      const jaTemMarcado = Array.from(parAtivo).some((label) => label.querySelector('input').checked);
      if (!jaTemMarcado) parAtivo[0].querySelector('input').checked = true;
    }

    // quantidade so e´ perguntada UMA vez, na tela final -- em item de 2
    // lados isso e´ depois dos dois lados prontos (view-preview-duas-faces),
    // nao aqui em cada lado.
    if (quantidadeUploadDiv) quantidadeUploadDiv.hidden = duasFacesAtual();
    // "escolher do catalogo" -- entremeio_2lados reaproveita a mesma
    // foto composta do entremeio de 1 lado; medalha_2lados e
    // chaveiro_2lados tem gabarito proprio novo, com o catalogo
    // regenerado nele (ver conversa 2026-09-02 e 2026-09-03) -- so os
    // santos adicionados DEPOIS dessa regeneracao ficariam sem essa
    // opcao, por isso renderizarModelosCatalogo filtra quem nao tiver a
    // imagem.
    if (escolherCatalogoDiv) {
      escolherCatalogoDiv.hidden = formato !== 'entremeio_2lados' && formato !== 'medalha_2lados' && formato !== 'chaveiro_2lados';
      resetarEscolherCatalogo();
    }
    resetarFluxoDuasFaces();
    atualizarAvisoPreco();
    atualizarBotoesUpload();
  }

  function atualizarBotoesUpload() {
    const completo = subSelecaoCompleta();
    const temArquivo = inputImagem.files.length > 0;

    if (!completo) {
      const formato = formatoAtual();
      if (formato === 'medalha') {
        botaoEnviar.textContent = 'Selecione um tamanho';
      } else if (formato === 'medalha_2lados' && !tamanhoAtual()) {
        botaoEnviar.textContent = 'Selecione um tamanho';
      } else {
        botaoEnviar.textContent = 'Selecione uma cor';
      }
    } else if (!temArquivo) {
      botaoEnviar.textContent = 'Selecione uma imagem';
    } else {
      botaoEnviar.textContent = 'Gerar simulação';
    }
    botaoEnviar.disabled = !(completo && temArquivo);
    btnSemFoto.disabled = !completo;
    btnSemFoto.textContent = duasFacesAtual()
      ? `Lado ${ladoAtual}: enviar depois pelo WhatsApp`
      : 'Adicionar ao carrinho sem foto (envio depois pelo WhatsApp)';
  }

  formatosFieldset.addEventListener('change', (evento) => {
    if (evento.target.name === 'formato') atualizarSubSelecao();
  });
  tamanhosFieldset.addEventListener('change', (evento) => {
    if (evento.target.name === 'tamanho') {
      atualizarBotoesUpload();
      tentarAutoPreencherCombo();
    }
  });
  coresFieldset.addEventListener('change', (evento) => {
    if (evento.target.name === 'cor') {
      atualizarBotoesUpload();
      rerenderizarModelosCatalogoSeNecessario();
      tentarAutoPreencherCombo();
    }
  });

  // ---- escolher um santo do catalogo (entremeio_2lados e medalha_2lados
  // -- ver atualizarSubSelecao acima). Pula upload+recorte: a foto do
  // modelo escolhido ja e´ um render pronto (ver services/gerador/
  // config.py), so avanca o lado direto com ela. ----

  const buscaCatalogoInput = document.getElementById('busca-personalizada');
  const buscaCatalogoResultados = document.getElementById('busca-personalizada-resultados');
  const escolherCatalogoBuscaWrap = document.getElementById('escolher-catalogo-busca-wrap');
  const escolherCatalogoModelosDiv = document.getElementById('escolher-catalogo-modelos');
  const escolherCatalogoSantoNome = document.getElementById('escolher-catalogo-santo-nome');
  const modelosGridCatalogo = document.getElementById('modelos-grid-catalogo');
  const escolherCatalogoTrocarBtn = document.getElementById('escolher-catalogo-trocar');

  let santoEModelosSelecionados = null; // { santo, modelos } -- pra re-renderizar se a cor mudar depois

  function resetarEscolherCatalogo() {
    if (!buscaCatalogoInput) return;
    santoEModelosSelecionados = null;
    buscaCatalogoInput.value = '';
    buscaCatalogoResultados.hidden = true;
    buscaCatalogoResultados.innerHTML = '';
    escolherCatalogoModelosDiv.hidden = true;
    escolherCatalogoBuscaWrap.hidden = false;
  }

  function chaveImagemCatalogoAtual() {
    const formato = formatoAtual();
    // chaveiro_2lados so tem uma cor (prata/inox, ver conversa
    // 2026-09-03) -- chave fixa, sem depender de corAtual().
    if (formato === 'chaveiro_2lados') return 'chaveiro_2lados';
    const ouroVelho = corAtual() === 'ouro_velho';
    if (formato === 'medalha_2lados') {
      return ouroVelho ? 'medalha_2lados_ouro_velho' : 'medalha_2lados_prata';
    }
    return ouroVelho ? 'entremeio_ouro_velho' : 'entremeio_prata';
  }

  function renderizarModelosCatalogo(santo, modelos) {
    const chave = chaveImagemCatalogoAtual();
    modelosGridCatalogo.innerHTML = '';
    // medalha_2lados: nem todo modelo do catalogo tem imagem nesse
    // gabarito ainda (ver conversa) -- filtra em vez de mostrar link
    // quebrado.
    const disponiveis = modelos.filter((modelo) => modelo.imagens[chave]);
    if (disponiveis.length === 0) {
      modelosGridCatalogo.innerHTML = '<p class="busca-resultados-vazio">Nenhum modelo disponível nesse formato ainda.</p>';
      return;
    }
    disponiveis.forEach((modelo) => {
      const url = modelo.imagens[chave];
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.className = 'modelo-card';
      botao.innerHTML = `<img src="${url}" alt="${santo.nome} — ${modelo.nome}" loading="lazy"><span>${modelo.nome}</span>`;
      botao.addEventListener('click', () => {
        avancarLado({
          origem: 'catalogo',
          imagem: url,
          produtoId: santo.id,
          produtoNome: santo.nome,
          modeloId: modelo.id,
          modeloNome: modelo.nome,
        });
      });
      modelosGridCatalogo.appendChild(botao);
    });
  }

  function rerenderizarModelosCatalogoSeNecessario() {
    if (!santoEModelosSelecionados || escolherCatalogoModelosDiv.hidden) return;
    renderizarModelosCatalogo(santoEModelosSelecionados.santo, santoEModelosSelecionados.modelos);
  }

  async function selecionarSantoDoCatalogo(item) {
    buscaCatalogoResultados.hidden = true;
    escolherCatalogoSantoNome.textContent = item.nome;
    modelosGridCatalogo.innerHTML = '<p class="busca-resultados-vazio">Carregando modelos…</p>';
    escolherCatalogoModelosDiv.hidden = false;
    escolherCatalogoBuscaWrap.hidden = true;
    try {
      const resp = await fetch(`/api/produto/${encodeURIComponent(item.id)}/modelos`);
      if (!resp.ok) throw new Error('nao encontrado');
      const modelos = await resp.json();
      santoEModelosSelecionados = { santo: item, modelos };
      renderizarModelosCatalogo(item, modelos);
    } catch (err) {
      modelosGridCatalogo.innerHTML = '<p class="busca-resultados-vazio">Não foi possível carregar os modelos agora.</p>';
    }
  }

  // ---- combo "medalha de 2 lados" pronto (window.COMBO_2LADOS, ver
  // config.py:COMBOS_2LADOS_PRONTOS e app.py:personalizada -- card de
  // novidade da home que ja vem com os 2 lados escolhidos). Assim que a
  // sub-selecao fica completa (tamanho + cor, ver subSelecaoCompleta),
  // busca a imagem de cada lado no gabarito/cor certos e pula direto pra
  // tela final combinada -- sem precisar buscar/clicar nada. Reaproveita
  // a MESMA API que a busca manual usa (/api/produto/<id>/modelos), so
  // que preenchendo resultadoLado1/2 direto em vez de passar por
  // avancarLado()/prepararProximoLado() (que existem pra transicao de
  // TELA entre os 2 lados, desnecessaria aqui). ----
  let comboEmAndamento = false;

  async function buscarImagemModeloCatalogo(produtoId, modeloId) {
    const resp = await fetch(`/api/produto/${encodeURIComponent(produtoId)}/modelos`);
    if (!resp.ok) return null;
    const modelos = await resp.json();
    const modelo = modelos.find((m) => m.id === modeloId);
    return modelo ? modelo.imagens[chaveImagemCatalogoAtual()] : null;
  }

  async function tentarAutoPreencherCombo() {
    const combo = window.COMBO_2LADOS;
    if (!combo || !duasFacesAtual() || !subSelecaoCompleta() || comboEmAndamento) return;
    comboEmAndamento = true;
    try {
      const [url1, url2] = await Promise.all([
        buscarImagemModeloCatalogo(combo.lado1.produto_id, combo.lado1.modelo_id),
        buscarImagemModeloCatalogo(combo.lado2.produto_id, combo.lado2.modelo_id),
      ]);
      if (!url1 || !url2) return; // gabarito/cor sem imagem pronta -- deixa o fluxo normal (busca manual)
      resultadoLado1 = {
        origem: 'catalogo', imagem: url1,
        produtoId: combo.lado1.produto_id, produtoNome: combo.lado1.produto_nome,
        modeloId: combo.lado1.modelo_id, modeloNome: combo.lado1.modelo_nome,
      };
      resultadoLado2 = {
        origem: 'catalogo', imagem: url2,
        produtoId: combo.lado2.produto_id, produtoNome: combo.lado2.produto_nome,
        modeloId: combo.lado2.modelo_id, modeloNome: combo.lado2.modelo_nome,
      };
      mostrarPreviewDuasFaces();
    } finally {
      comboEmAndamento = false;
    }
  }

  if (buscaCatalogoInput) {
    let buscaCatalogoTimer = null;
    let buscaCatalogoReq = 0;

    function renderizarResultadosBuscaCatalogo(itens) {
      // so produtos de verdade tem modelos -- os cards "personalizada"
      // (config.py:PRODUTOS_PERSONALIZADOS) tambem aparecem em
      // /api/busca, mas nao servem aqui.
      const encontrados = itens.filter((item) => !item.id.startsWith('personalizada-'));
      if (encontrados.length === 0) {
        buscaCatalogoResultados.innerHTML = '<p class="busca-resultados-vazio">Nenhum santo encontrado com esse nome.</p>';
        buscaCatalogoResultados.hidden = false;
        return;
      }
      buscaCatalogoResultados.innerHTML = '';
      encontrados.forEach((item) => {
        const botao = document.createElement('button');
        botao.type = 'button';
        botao.className = 'busca-resultado-item';
        botao.style.cssText = 'width:100%;border:none;background:none;cursor:pointer;text-align:left;';
        botao.innerHTML = `<img src="${item.thumbnail}" alt="" loading="lazy"><span>${item.nome}</span>`;
        botao.addEventListener('click', () => selecionarSantoDoCatalogo(item));
        buscaCatalogoResultados.appendChild(botao);
      });
      buscaCatalogoResultados.hidden = false;
    }

    function buscarNoCatalogo() {
      const termo = buscaCatalogoInput.value.trim();
      if (!termo) {
        buscaCatalogoResultados.hidden = true;
        buscaCatalogoResultados.innerHTML = '';
        return;
      }
      const idReq = ++buscaCatalogoReq;
      fetch(`/api/busca?q=${encodeURIComponent(termo)}`)
        .then((resp) => (resp.ok ? resp.json() : []))
        .then((itens) => {
          if (idReq !== buscaCatalogoReq) return;
          renderizarResultadosBuscaCatalogo(itens);
        })
        .catch(() => {});
    }

    buscaCatalogoInput.addEventListener('input', () => {
      clearTimeout(buscaCatalogoTimer);
      buscaCatalogoTimer = setTimeout(buscarNoCatalogo, 250);
    });

    document.addEventListener('click', (evento) => {
      if (evento.target !== buscaCatalogoInput && !buscaCatalogoResultados.contains(evento.target)) {
        buscaCatalogoResultados.hidden = true;
      }
    });

    escolherCatalogoTrocarBtn.addEventListener('click', resetarEscolherCatalogo);
  }

  let customizerIniciado = false;
  inputImagem.addEventListener('change', () => {
    nomeArquivoDiv.textContent = inputImagem.files.length > 0 ? inputImagem.files[0].name : '';
    atualizarBotoesUpload();
    if (!customizerIniciado && inputImagem.files.length > 0) {
      customizerIniciado = true;
      rastrearEventoGA4('start_customizer', {});
    }
  });

  // Arrastar o arquivo pra dropzone ou colar (Ctrl+V) uma imagem
  // copiada -- so faz sentido no desktop (ver conversa), mas nao
  // atrapalha em touch (esses eventos simplesmente nunca disparam la).
  // Reaproveita o MESMO <input type="file"> via DataTransfer, pra nao
  // duplicar nenhuma logica de validacao/preview -- so preenche
  // inputImagem.files e dispara 'change' como se a pessoa tivesse
  // escolhido o arquivo pelo seletor normal.
  function definirArquivoNoInput(file) {
    if (!file || !file.type.startsWith('image/')) return;
    const dt = new DataTransfer();
    dt.items.add(file);
    inputImagem.files = dt.files;
    inputImagem.dispatchEvent(new Event('change'));
  }

  if (dropzoneImagem) {
    ['dragenter', 'dragover'].forEach((tipo) => {
      dropzoneImagem.addEventListener(tipo, (evento) => {
        evento.preventDefault();
        dropzoneImagem.classList.add('dropzone-arrastando');
      });
    });
    ['dragleave', 'dragend'].forEach((tipo) => {
      dropzoneImagem.addEventListener(tipo, () => {
        dropzoneImagem.classList.remove('dropzone-arrastando');
      });
    });
    dropzoneImagem.addEventListener('drop', (evento) => {
      evento.preventDefault();
      dropzoneImagem.classList.remove('dropzone-arrastando');
      const arquivo = evento.dataTransfer.files[0];
      definirArquivoNoInput(arquivo);
    });
  }

  document.addEventListener('paste', (evento) => {
    // Nao intercepta colar se a view de upload nem esta visivel (ex:
    // pessoa ja esta no editor de recorte ou na tela de preview).
    if (viewUpload.hidden) return;
    const itens = evento.clipboardData ? evento.clipboardData.items : null;
    if (!itens) return;
    for (const item of itens) {
      if (item.type && item.type.startsWith('image/')) {
        definirArquivoNoInput(item.getAsFile());
        break;
      }
    }
  });

  function ajustarQuantidadeForm(delta) {
    const atual = parseInt(qtdFormInput.value, 10) || 1;
    qtdFormInput.value = Math.max(1, atual + delta);
  }
  qtdMenosForm.addEventListener('click', () => ajustarQuantidadeForm(-1));
  qtdMaisForm.addEventListener('click', () => ajustarQuantidadeForm(1));

  // ---- editor de recorte (canvas): pan com arraste, zoom com o slider.
  // Nunca deixa posicionar/zoom-out alem dos limites da imagem original --
  // sem preenchimento de branco/preto, o recorte fica sempre 100% dentro
  // da foto. Portado sem alteracoes do repositorio `mockup`. ----

  const canvas = document.getElementById('cropper-canvas');
  const ctx = canvas.getContext('2d');
  const zoomSlider = document.getElementById('cropper-zoom');
  const botaoConfirmar = document.getElementById('botao-cropper-confirmar');
  const botaoCancelar = document.getElementById('botao-cropper-cancelar');

  let cropperImg = null;
  let minScale = 1, maxScale = 1, scale = 1;
  let offsetX = 0, offsetY = 0;
  let recorteFoiAjustado = false;

  function clampOffset() {
    const rImg = RAIO / scale;
    const maxX = Math.max(rImg, cropperImg.naturalWidth - rImg);
    const maxY = Math.max(rImg, cropperImg.naturalHeight - rImg);
    offsetX = Math.min(Math.max(offsetX, rImg), maxX);
    offsetY = Math.min(Math.max(offsetY, rImg), maxY);
  }

  function desenharCropper() {
    ctx.clearRect(0, 0, CROPPER_SIZE, CROPPER_SIZE);
    const drawW = cropperImg.naturalWidth * scale;
    const drawH = cropperImg.naturalHeight * scale;
    const drawX = RAIO - offsetX * scale;
    const drawY = RAIO - offsetY * scale;
    ctx.drawImage(cropperImg, drawX, drawY, drawW, drawH);

    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,0.55)';
    ctx.beginPath();
    ctx.rect(0, 0, CROPPER_SIZE, CROPPER_SIZE);
    ctx.arc(RAIO, RAIO, RAIO, 0, Math.PI * 2, true);
    ctx.fill('evenodd');
    ctx.restore();

    ctx.beginPath();
    ctx.arc(RAIO, RAIO, RAIO - 1, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.9)';
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  function zoomSliderParaEscala(valorSlider) {
    const t = valorSlider / 1000;
    return minScale * Math.pow(ZOOM_MAX_MULT, t);
  }

  function escalaParaZoomSlider(valorEscala) {
    const t = Math.log(valorEscala / minScale) / Math.log(ZOOM_MAX_MULT);
    return Math.round(Math.min(Math.max(t, 0), 1) * 1000);
  }

  function iniciarCropper(imgEl, boxInicial) {
    cropperImg = imgEl;
    minScale = CROPPER_SIZE / Math.min(imgEl.naturalWidth, imgEl.naturalHeight);
    maxScale = minScale * ZOOM_MAX_MULT;

    if (boxInicial) {
      const [x1, y1, x2, y2] = boxInicial;
      const lado = x2 - x1;
      scale = Math.min(Math.max(CROPPER_SIZE / lado, minScale), maxScale);
      offsetX = (x1 + x2) / 2;
      offsetY = (y1 + y2) / 2;
    } else {
      scale = minScale;
      offsetX = imgEl.naturalWidth / 2;
      offsetY = imgEl.naturalHeight / 2;
    }
    clampOffset();
    zoomSlider.value = escalaParaZoomSlider(scale);
    desenharCropper();
  }

  function boxAtual() {
    const rImg = RAIO / scale;
    return [offsetX - rImg, offsetY - rImg, offsetX + rImg, offsetY + rImg];
  }

  zoomSlider.addEventListener('input', () => {
    recorteFoiAjustado = true;
    scale = zoomSliderParaEscala(Number(zoomSlider.value));
    clampOffset();
    desenharCropper();
  });

  let arrastando = false;
  let inicioPointer = { x: 0, y: 0 };
  let inicioOffset = { x: 0, y: 0 };

  canvas.addEventListener('pointerdown', (ev) => {
    arrastando = true;
    canvas.setPointerCapture(ev.pointerId);
    const rect = canvas.getBoundingClientRect();
    inicioPointer = { x: ev.clientX, y: ev.clientY };
    inicioOffset = { x: offsetX, y: offsetY };
    canvas._escalaTela = canvas.width / rect.width;
  });
  canvas.addEventListener('pointermove', (ev) => {
    if (!arrastando) return;
    recorteFoiAjustado = true;
    const fator = canvas._escalaTela || 1;
    const dx = (ev.clientX - inicioPointer.x) * fator;
    const dy = (ev.clientY - inicioPointer.y) * fator;
    offsetX = inicioOffset.x - dx / scale;
    offsetY = inicioOffset.y - dy / scale;
    clampOffset();
    desenharCropper();
  });
  function pararArraste(ev) {
    if (arrastando) canvas.releasePointerCapture(ev.pointerId);
    arrastando = false;
  }
  canvas.addEventListener('pointerup', pararArraste);
  canvas.addEventListener('pointercancel', pararArraste);

  // ---- fluxo geral ----

  let arquivoAtual = null;
  let boxAnterior = null;
  let ultimoResultado = null; // { previewSrc, urlPreview, urlCrop, formato, tamanho, cor, chavePreco }

  function carregarImagemDeArquivo(file) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = URL.createObjectURL(file);
    });
  }

  botaoEnviar.addEventListener('click', async () => {
    if (botaoEnviar.disabled) return;
    limparErro();
    arquivoAtual = inputImagem.files[0];
    boxAnterior = null;
    recorteFoiAjustado = false;
    const img = await carregarImagemDeArquivo(arquivoAtual);
    iniciarCropper(img, null);
    mostrarView('cropper');
  });

  botaoCancelar.addEventListener('click', () => {
    inputImagem.value = '';
    nomeArquivoDiv.textContent = '';
    atualizarBotoesUpload();
    mostrarView('upload');
  });

  async function gerarPreviaUnica(box) {
    limparErro();
    botaoConfirmar.disabled = true;
    botaoConfirmar.textContent = 'Gerando...';
    try {
      const fd = new FormData();
      fd.append('imagem', arquivoAtual);
      fd.append('formato', formatoAtual());
      if (corAtual()) fd.append('cor', corAtual());
      fd.append('x1', box[0]); fd.append('y1', box[1]);
      fd.append('x2', box[2]); fd.append('y2', box[3]);
      const resp = await fetch('/api/personalizada/preview', { method: 'POST', body: fd });
      const dados = await resp.json();
      if (!resp.ok) throw new Error(dados.erro || 'Erro ao gerar prévia.');

      boxAnterior = box;
      ultimoResultado = {
        previewSrc: dados.preview,
        cropSrc: dados.crop,
        urlPreview: dados.url_preview,
        urlCrop: dados.url_crop,
        formato: formatoAtual(),
        tamanho: tamanhoAtual(),
        cor: corAtual(),
        chavePreco: chavePrecoAtual(),
        ajustado: recorteFoiAjustado,
      };
      renderizarPreview();
      mostrarView('preview');
    } catch (err) {
      mostrarErro(err.message || String(err));
      mostrarView('cropper');
    } finally {
      botaoConfirmar.disabled = false;
      botaoConfirmar.textContent = 'Gerar prévia';
    }
  }

  botaoConfirmar.addEventListener('click', () => {
    gerarPreviaUnica(boxAtual());
  });

  // ---- resultado ----

  const previewImg = document.getElementById('preview-imagem');
  const linkBaixarPrevia = document.getElementById('link-baixar-previa');
  const linkBaixarRecorte = document.getElementById('link-baixar-recorte');
  const avisoReenvio = document.getElementById('aviso-reenvio');
  const qtdMenos = document.getElementById('qtd-menos');
  const qtdMais = document.getElementById('qtd-mais');
  const quantidadeInput = document.getElementById('sel-quantidade');
  const quantidadePreviewDiv = document.querySelector('#view-preview .quantidade');
  const btnAdicionar = document.getElementById('btn-adicionar');
  const botaoReposicionar = document.getElementById('botao-reposicionar');

  function renderizarPreview() {
    previewImg.src = ultimoResultado.previewSrc;
    linkBaixarPrevia.href = ultimoResultado.urlPreview;
    linkBaixarRecorte.href = ultimoResultado.urlCrop;
    quantidadeInput.value = qtdFormInput.value;

    if (duasFacesAtual()) {
      // quantidade e´ perguntada so uma vez, na tela combinada final
      // (view-preview-duas-faces) -- aqui e´ so a confirmacao do recorte
      // DESSE lado, no meio do assistente.
      quantidadePreviewDiv.hidden = true;
      avisoReenvio.innerHTML =
        '✅ A foto desse lado, no recorte exato desta simulação, já fica salva junto com o pedido.';
      btnAdicionar.textContent = ladoAtual === 1 ? 'Confirmar lado 1 e continuar →' : 'Confirmar lado 2 →';
    } else {
      quantidadePreviewDiv.hidden = false;
      avisoReenvio.innerHTML =
        '✅ Sua foto no recorte exato desta simulação já fica salva junto com o pedido — ' +
        'não precisa reenviar nada pelo WhatsApp.';
      btnAdicionar.textContent = 'Adicionar ao carrinho';
    }
  }

  function ajustarQuantidade(delta) {
    const atual = parseInt(quantidadeInput.value, 10) || 1;
    quantidadeInput.value = Math.max(1, atual + delta);
  }
  qtdMenos.addEventListener('click', () => ajustarQuantidade(-1));
  qtdMais.addEventListener('click', () => ajustarQuantidade(1));

  botaoReposicionar.addEventListener('click', async () => {
    const img = await carregarImagemDeArquivo(arquivoAtual);
    recorteFoiAjustado = true; // reabriu o editor -- nao ha garantia de que o recorte final bate com a foto original
    iniciarCropper(img, boxAnterior);
    mostrarView('cropper');
  });

  // ---- 2 lados: prepara a view-upload de novo pro proximo lado
  // (limpa o arquivo escolhido, mantem formato/cor travados -- ver
  // atualizarSubSelecao, que so reseta isso quando o FORMATO muda). ----
  function prepararProximoLado() {
    inputImagem.value = '';
    nomeArquivoDiv.textContent = '';
    arquivoAtual = null;
    boxAnterior = null;
    resetarEscolherCatalogo();
    atualizarIndicadorLado();
    atualizarBotoesUpload();
    mostrarView('upload');
  }

  function avancarLado(resultadoDesseLado) {
    if (ladoAtual === 1) {
      resultadoLado1 = resultadoDesseLado;
      ladoAtual = 2;
      prepararProximoLado();
    } else {
      resultadoLado2 = resultadoDesseLado;
      mostrarPreviewDuasFaces();
    }
  }

  btnAdicionar.addEventListener('click', () => {
    if (!ultimoResultado) return;
    const r = ultimoResultado;

    if (duasFacesAtual()) {
      avancarLado({ origem: 'upload', imagem: r.previewSrc, imagemRecorte: r.cropSrc });
      return;
    }

    const quantidade = Math.max(1, parseInt(quantidadeInput.value, 10) || 1);
    carrinhoAdicionarItem({
      chave: `personalizada-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      tipo: 'personalizada',
      produtoNome: 'Personalizada',
      modeloNome: null,
      imagem: r.previewSrc,
      imagemRecorte: r.cropSrc,
      formato: r.formato,
      chave_preco: r.chavePreco,
      tamanho: r.tamanho,
      cor: r.cor,
      quantidade,
      semImagem: false,
    });
    rastrearEventoGA4('add_custom_to_cart', { formato: r.formato, quantity: quantidade, com_foto: true });

    const textoOriginal = 'Adicionar ao carrinho';
    btnAdicionar.textContent = 'Adicionado ✓';
    setTimeout(() => {
      btnAdicionar.textContent = textoOriginal;
    }, 1200);
  });

  // ---- sem foto ----

  btnSemFoto.addEventListener('click', () => {
    if (btnSemFoto.disabled) return;

    if (duasFacesAtual()) {
      rastrearEventoGA4('add_custom_to_cart_lado_sem_foto', { formato: formatoAtual(), lado: ladoAtual });
      avancarLado({ origem: 'sem_foto', imagem: '/static/img/sem-foto.svg' });
      return;
    }

    const quantidade = Math.max(1, parseInt(qtdFormInput.value, 10) || 1);
    carrinhoAdicionarItem({
      chave: `personalizada-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      tipo: 'personalizada',
      produtoNome: 'Personalizada',
      modeloNome: null,
      imagem: '/static/img/sem-foto.svg',
      formato: formatoAtual(),
      chave_preco: chavePrecoAtual(),
      tamanho: tamanhoAtual(),
      cor: corAtual(),
      quantidade,
      semImagem: true,
    });
    rastrearEventoGA4('add_custom_to_cart', { formato: formatoAtual(), quantity: quantidade, com_foto: false });

    const textoOriginal = 'Adicionar ao carrinho sem foto (envio depois pelo WhatsApp)';
    btnSemFoto.textContent = 'Adicionado ✓ — não esqueça de enviar a foto depois';
    setTimeout(() => {
      btnSemFoto.textContent = textoOriginal;
    }, 2200);
  });

  // ---- 2 lados: tela final combinada (ve os dois lados antes de ir
  // pro carrinho -- so aqui a quantidade e´ perguntada de verdade). ----

  const previewImgLado1 = document.getElementById('preview-imagem-lado1');
  const previewImgLado2 = document.getElementById('preview-imagem-lado2');
  const avisoReenvio2f = document.getElementById('aviso-reenvio-2f');
  const quantidadeInput2f = document.getElementById('sel-quantidade-2f');
  const qtdMenos2f = document.getElementById('qtd-menos-2f');
  const qtdMais2f = document.getElementById('qtd-mais-2f');
  const btnAdicionar2f = document.getElementById('btn-adicionar-2f');

  function mostrarPreviewDuasFaces() {
    previewImgLado1.src = resultadoLado1.imagem;
    previewImgLado2.src = resultadoLado2.imagem;
    quantidadeInput2f.value = qtdFormInput.value;

    const algumSemFoto = resultadoLado1.origem === 'sem_foto' || resultadoLado2.origem === 'sem_foto';
    avisoReenvio2f.innerHTML = algumSemFoto
      ? '📷 Pelo menos um lado ainda não tem foto — não esqueça de enviar pelo WhatsApp depois de fechar o pedido.'
      : '✅ As fotos dos dois lados, no recorte exato desta simulação, já ficam salvas junto com o pedido — ' +
        'não precisa reenviar nada pelo WhatsApp.';
    mostrarView('preview-2f');
  }

  function ajustarQuantidade2f(delta) {
    const atual = parseInt(quantidadeInput2f.value, 10) || 1;
    quantidadeInput2f.value = Math.max(1, atual + delta);
  }
  qtdMenos2f.addEventListener('click', () => ajustarQuantidade2f(-1));
  qtdMais2f.addEventListener('click', () => ajustarQuantidade2f(1));

  btnAdicionar2f.addEventListener('click', () => {
    if (!resultadoLado1 || !resultadoLado2) return;
    const quantidade = Math.max(1, parseInt(quantidadeInput2f.value, 10) || 1);
    const semFoto1 = resultadoLado1.origem === 'sem_foto';
    const semFoto2 = resultadoLado2.origem === 'sem_foto';

    carrinhoAdicionarItem({
      chave: `personalizada-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      tipo: 'personalizada',
      duasFaces: true,
      produtoNome: 'Personalizada',
      modeloNome: null,
      formato: formatoAtual(),
      chave_preco: chavePrecoAtual(),
      cor: corAtual(),
      tamanho: tamanhoAtual(),
      quantidade,
      semImagem: semFoto1 && semFoto2,
      lado1: resultadoLado1,
      lado2: resultadoLado2,
    });
    rastrearEventoGA4('add_custom_to_cart', {
      formato: formatoAtual(), quantity: quantidade, com_foto: !semFoto1 && !semFoto2,
    });

    const textoOriginal = 'Adicionar ao carrinho';
    btnAdicionar2f.textContent = 'Adicionado ✓';
    setTimeout(() => {
      btnAdicionar2f.textContent = textoOriginal;
    }, 1200);
  });

  // Pre-seleciona o formato vindo do card "produto" da personalizada no
  // catalogo/busca (?formato=..., ver app.py:personalizada).
  if (window.FORMATO_INICIAL) {
    const inputFormato = formatosFieldset.querySelector(`input[name="formato"][value="${window.FORMATO_INICIAL}"]`);
    if (inputFormato) inputFormato.checked = true;
  }

  atualizarSubSelecao();
})();
