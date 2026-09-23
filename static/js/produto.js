(function () {
  const grid = document.getElementById('modelos-grid');
  const painel = document.getElementById('painel-selecao');
  const nomeSpan = document.getElementById('sel-modelo-nome');
  const previewImg = document.getElementById('sel-preview-imagem');
  const previewWrap = document.querySelector('.preview-formato-wrap');
  const previewVerso = document.getElementById('preview-verso');
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
  const barraFixaDetalhe = document.getElementById('barra-fixa-detalhe');
  const barraFixaBtn = document.getElementById('barra-fixa-btn-adicionar');
  const previewPrecoEl = document.getElementById('preview-preco');
  const toggle2Lados = document.getElementById('toggle-2lados');
  const lado2Widget = document.getElementById('lado2-widget');
  const lado2WidgetImagemLado1 = document.getElementById('lado2-widget-imagem-lado1');
  const lado2WidgetNomeLado1 = document.getElementById('lado2-widget-nome-lado1');
  const lado2WidgetInput = document.getElementById('lado2-widget-input');
  const lado2WidgetResultados = document.getElementById('lado2-widget-resultados');
  const lado2WidgetModelos = document.getElementById('lado2-widget-modelos');
  const lado2WidgetEscolhido = document.getElementById('lado2-widget-escolhido');
  const lado2WidgetEscolhidoImagem = document.getElementById('lado2-widget-escolhido-imagem');
  const lado2WidgetEscolhidoNome = document.getElementById('lado2-widget-escolhido-nome');
  const lado2WidgetTrocar = document.getElementById('lado2-widget-trocar');
  const lado2WidgetSubselecao = document.getElementById('lado2-widget-subselecao');
  const lado2WidgetTamanhoGrupo = document.getElementById('lado2-widget-tamanho-grupo');
  const lado2WidgetCorGrupo = document.getElementById('lado2-widget-cor-grupo');
  const lado2WidgetPrecoNota = document.getElementById('lado2-widget-preco-nota');
  const lado2WidgetPersonalizada = document.getElementById('lado2-widget-personalizada');
  if (!grid || !painel) return;

  const produtoId = grid.dataset.produtoId;
  const produtoNome = grid.dataset.produtoNome;
  let modeloSelecionado = null;

  // ---- "quero acrescentar um segundo lado" (pedido 2026-09-17: em vez
  // de 6 botoes de formato como a personalizada tem, mantem os 3 formatos
  // normais e esse toggle transforma o formato escolhido na sua versao de
  // 2 lados por baixo dos panos). O item final tem exatamente o mesmo
  // formato que static/js/personalizada.js:btnAdicionar2f ja produz
  // (tipo:"personalizada", duasFaces:true, lado1/lado2) -- reaproveita o
  // MESMO processo de venda/CSV/link, sem mudar nada la. ----
  let duasFacesAtiva = false;
  let lado2Selecionado = null;

  function formato2LadosDe(formato) {
    return { medalha: 'medalha_2lados', entremeio: 'entremeio_2lados', chaveiro: 'chaveiro_2lados' }[formato];
  }

  function corParaImagem2Lados() {
    if (formatoAtual() === 'entremeio') {
      const cor = coresFieldset.querySelector('input[name="cor"]:checked');
      return cor ? cor.value : 'prata';
    }
    const corMedalha = lado2WidgetCorGrupo && lado2WidgetCorGrupo.querySelector('input[name="cor-2lados"]:checked');
    return corMedalha ? corMedalha.value : 'prata';
  }

  // chave de imagem certa pra base FISICA de 2 lados -- essa base e´
  // diferente da de 1 lado (bezel mais fino, ver config.py:MEDAL_SPECS),
  // entao NUNCA reaproveita imagens.medalha/imagens.chaveiro aqui.
  // entremeio_2lados e´ excecao real: usa a MESMA base/imagem do entremeio
  // de 1 lado (nao existe imagem "entremeio_2lados_*" separada, ver
  // produtos.json) -- por isso cai no mesmo entremeio_prata/ouro_velho.
  function chaveImagem2Lados(formato2Lados, cor) {
    if (formato2Lados === 'chaveiro_2lados') return 'chaveiro_2lados';
    const ouroVelho = cor === 'ouro_velho';
    if (formato2Lados === 'medalha_2lados') {
      return ouroVelho ? 'medalha_2lados_ouro_velho' : 'medalha_2lados_prata';
    }
    return ouroVelho ? 'entremeio_ouro_velho' : 'entremeio_prata';
  }

  // Nem todo modelo do catalogo ja tem a base de 2 lados gerada (ver
  // conversa 2026-09-02) -- o toggle so aparece pra quem tem, senao
  // mostraria uma imagem quebrada.
  function disponivel2Lados() {
    if (!modeloSelecionado) return false;
    const formato2Lados = formato2LadosDe(formatoAtual());
    if (!formato2Lados) return false;
    const chave = chaveImagem2Lados(formato2Lados, 'prata');
    return !!modeloSelecionado.imagens[chave];
  }

  function imagemLado1Atual() {
    if (!modeloSelecionado) return null;
    const formato2Lados = formato2LadosDe(formatoAtual());
    const chave = chaveImagem2Lados(formato2Lados, corParaImagem2Lados());
    return modeloSelecionado.imagens[chave];
  }

  function desligarToggle2Lados() {
    duasFacesAtiva = false;
    lado2Selecionado = null;
    if (toggle2Lados) toggle2Lados.classList.remove('ativo');
    if (lado2Widget) lado2Widget.hidden = true;
    resetarLado2Widget();
  }

  function resetarLado2Widget() {
    if (lado2WidgetInput) lado2WidgetInput.value = '';
    if (lado2WidgetResultados) { lado2WidgetResultados.hidden = true; lado2WidgetResultados.innerHTML = ''; }
    if (lado2WidgetModelos) { lado2WidgetModelos.hidden = true; lado2WidgetModelos.innerHTML = ''; }
    if (lado2WidgetEscolhido) lado2WidgetEscolhido.hidden = true;
    if (lado2WidgetInput) lado2WidgetInput.hidden = false;
  }

  function atualizarToggleDisponibilidade() {
    if (!toggle2Lados) return;
    const disponivel = disponivel2Lados();
    toggle2Lados.hidden = !disponivel;
    if (!disponivel && duasFacesAtiva) desligarToggle2Lados();
  }

  function atualizarLado2SubSelecao() {
    if (!lado2WidgetSubselecao) return;
    const formato = formatoAtual();
    // medalha_2lados: tamanho (14/18mm, so fisico -- mesmo preco) E cor
    // (prata/ouro velho). entremeio_2lados reaproveita o #sel-cores que
    // ja aparece pro entremeio normal (mesma cor, mesma imagem -- nao
    // duplica selecao). chaveiro_2lados nao tem nenhuma das duas.
    const precisaGrupo = formato === 'medalha';
    lado2WidgetSubselecao.hidden = !precisaGrupo;
    if (lado2WidgetTamanhoGrupo) lado2WidgetTamanhoGrupo.hidden = !precisaGrupo;
    if (lado2WidgetCorGrupo) lado2WidgetCorGrupo.hidden = !precisaGrupo;
  }

  function precoTextoParaFormato2Lados(formato2Lados) {
    if (formato2Lados === 'chaveiro_2lados') {
      return `Chaveiro 2 lados: ${formatarPrecoLocal(window.PRECO_VAREJO_CHAVEIRO)}`;
    }
    const nome = formato2Lados === 'medalha_2lados' ? 'Medalha 2 lados' : 'Entremeio 2 lados';
    return `${nome}: ${formatarPrecoLocal(window.PRECO_VAREJO_2LADOS)}`;
  }

  function atualizarBotaoLado2() {
    if (!lado2WidgetPersonalizada || !modeloSelecionado) return;
    const formato2Lados = formato2LadosDe(formatoAtual());
    const params = new URLSearchParams({
      formato: formato2Lados,
      lado1_produto_id: produtoId,
      lado1_modelo_id: modeloSelecionado.id,
    });
    if (formato2Lados === 'medalha_2lados') {
      params.set('cor', corParaImagem2Lados());
      const tamanhoInput = lado2WidgetTamanhoGrupo && lado2WidgetTamanhoGrupo.querySelector('input[name="tamanho-2lados"]:checked');
      params.set('tamanho', tamanhoInput ? tamanhoInput.value : '14mm');
    } else if (formato2Lados === 'entremeio_2lados') {
      params.set('cor', corParaImagem2Lados());
    }
    lado2WidgetPersonalizada.dataset.href = `/personalizada?${params.toString()}`;
  }

  function atualizar2LadosUI() {
    if (!duasFacesAtiva || !modeloSelecionado) return;
    const formato2Lados = formato2LadosDe(formatoAtual());
    atualizarLado2SubSelecao();
    if (lado2WidgetImagemLado1) lado2WidgetImagemLado1.src = imagemLado1Atual();
    if (lado2WidgetNomeLado1) lado2WidgetNomeLado1.textContent = `Lado 1: ${produtoNome} — ${modeloSelecionado.nome}`;
    if (lado2WidgetPrecoNota) lado2WidgetPrecoNota.textContent = precoTextoParaFormato2Lados(formato2Lados);
    atualizarBotaoLado2();
    atualizarPreview();
    atualizarBotao();
  }

  if (toggle2Lados) {
    toggle2Lados.addEventListener('click', () => {
      duasFacesAtiva = !duasFacesAtiva;
      toggle2Lados.classList.toggle('ativo', duasFacesAtiva);
      if (lado2Widget) lado2Widget.hidden = !duasFacesAtiva;
      atualizarVisibilidadeTamanho();
      atualizarVersoVisivel();
      if (duasFacesAtiva) {
        atualizar2LadosUI();
      } else {
        lado2Selecionado = null;
        resetarLado2Widget();
        atualizarPreview();
        atualizarBotao();
      }
      rastrearEventoGA4('toggle_2_lados', { item_id: produtoId, ativo: duasFacesAtiva });
    });
  }

  if (lado2WidgetTamanhoGrupo) {
    lado2WidgetTamanhoGrupo.addEventListener('change', atualizar2LadosUI);
  }
  if (lado2WidgetCorGrupo) {
    lado2WidgetCorGrupo.addEventListener('change', () => {
      // cor mudou depois do lado 2 ja escolhido -- a imagem guardada
      // ficaria da cor errada, busca de novo no gabarito novo.
      if (lado2Selecionado) refazerBuscaImagemLado2();
      atualizar2LadosUI();
    });
  }

  if (lado2WidgetPersonalizada) {
    lado2WidgetPersonalizada.addEventListener('click', () => {
      if (lado2WidgetPersonalizada.dataset.href) window.location.href = lado2WidgetPersonalizada.dataset.href;
    });
  }

  // ---- busca de santo pro lado 2 (mesmo padrao de static/js/
  // personalizada.js:buscaCatalogoInput, so que embutido aqui) ----

  let lado2BuscaTimer = null;
  let lado2BuscaReq = 0;

  function renderizarResultadosLado2(itens) {
    const encontrados = itens.filter((item) => !item.id.startsWith('personalizada-'));
    lado2WidgetResultados.innerHTML = '';
    if (encontrados.length === 0) {
      lado2WidgetResultados.innerHTML = '<p class="busca-resultados-vazio">Nenhum santo encontrado.</p>';
      lado2WidgetResultados.hidden = false;
      return;
    }
    encontrados.forEach((item) => {
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.className = 'lado2-widget-resultado-item';
      botao.innerHTML = `<img src="${item.thumbnail}" alt="" loading="lazy"><span>${item.nome}</span>`;
      botao.addEventListener('click', () => selecionarSantoLado2(item));
      lado2WidgetResultados.appendChild(botao);
    });
    lado2WidgetResultados.hidden = false;
  }

  async function selecionarSantoLado2(item) {
    lado2WidgetResultados.hidden = true;
    lado2WidgetModelos.innerHTML = '<p class="busca-resultados-vazio">Carregando modelos…</p>';
    lado2WidgetModelos.hidden = false;
    try {
      const resp = await fetch(`/api/produto/${encodeURIComponent(item.id)}/modelos`);
      if (!resp.ok) throw new Error('nao encontrado');
      const modelos = await resp.json();
      renderizarModelosLado2(item, modelos);
    } catch (err) {
      lado2WidgetModelos.innerHTML = '<p class="busca-resultados-vazio">Não foi possível carregar os modelos agora.</p>';
    }
  }

  function renderizarModelosLado2(santo, modelos) {
    const formato2Lados = formato2LadosDe(formatoAtual());
    const chave = chaveImagem2Lados(formato2Lados, corParaImagem2Lados());
    lado2WidgetModelos.innerHTML = '';
    const disponiveis = modelos.filter((modelo) => modelo.imagens[chave]);
    if (disponiveis.length === 0) {
      lado2WidgetModelos.innerHTML = '<p class="busca-resultados-vazio">Nenhum modelo disponível nesse formato ainda.</p>';
      return;
    }
    disponiveis.forEach((modelo) => {
      const url = modelo.imagens[chave];
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.className = 'lado2-widget-modelo-item';
      botao.innerHTML = `<img src="${url}" alt="${santo.nome} — ${modelo.nome}" loading="lazy"><span>${modelo.nome}</span>`;
      botao.addEventListener('click', () => {
        lado2Selecionado = {
          origem: 'catalogo', imagem: url,
          produtoId: santo.id, produtoNome: santo.nome,
          modeloId: modelo.id, modeloNome: modelo.nome,
        };
        lado2WidgetModelos.hidden = true;
        lado2WidgetInput.hidden = true;
        lado2WidgetEscolhidoImagem.src = url;
        lado2WidgetEscolhidoNome.textContent = `${santo.nome} — ${modelo.nome}`;
        lado2WidgetEscolhido.hidden = false;
        atualizarBotao();
      });
      lado2WidgetModelos.appendChild(botao);
    });
  }

  async function refazerBuscaImagemLado2() {
    if (!lado2Selecionado) return;
    try {
      const resp = await fetch(`/api/produto/${encodeURIComponent(lado2Selecionado.produtoId)}/modelos`);
      if (!resp.ok) return;
      const modelos = await resp.json();
      const modelo = modelos.find((m) => m.id === lado2Selecionado.modeloId);
      const formato2Lados = formato2LadosDe(formatoAtual());
      const chave = chaveImagem2Lados(formato2Lados, corParaImagem2Lados());
      const url = modelo && modelo.imagens[chave];
      if (url) {
        lado2Selecionado.imagem = url;
        lado2WidgetEscolhidoImagem.src = url;
      }
    } catch (err) { /* mantem a imagem anterior se a busca falhar */ }
  }

  if (lado2WidgetInput) {
    lado2WidgetInput.addEventListener('input', () => {
      clearTimeout(lado2BuscaTimer);
      const termo = lado2WidgetInput.value.trim();
      if (!termo) {
        lado2WidgetResultados.hidden = true;
        lado2WidgetResultados.innerHTML = '';
        return;
      }
      lado2BuscaTimer = setTimeout(() => {
        const idReq = ++lado2BuscaReq;
        fetch(`/api/busca?q=${encodeURIComponent(termo)}`)
          .then((resp) => (resp.ok ? resp.json() : []))
          .then((itens) => {
            if (idReq !== lado2BuscaReq) return;
            renderizarResultadosLado2(itens);
          })
          .catch(() => {});
      }, 250);
    });
    document.addEventListener('click', (evento) => {
      if (evento.target !== lado2WidgetInput && lado2WidgetResultados && !lado2WidgetResultados.contains(evento.target)) {
        lado2WidgetResultados.hidden = true;
      }
    });
  }

  if (lado2WidgetTrocar) {
    lado2WidgetTrocar.addEventListener('click', () => {
      lado2Selecionado = null;
      resetarLado2Widget();
      atualizarBotao();
    });
  }

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
    if (duasFacesAtiva) {
      const formato2Lados = formato2LadosDe(formato);
      if (formato2Lados === 'medalha_2lados') {
        const tamanhoInput = lado2WidgetTamanhoGrupo && lado2WidgetTamanhoGrupo.querySelector('input[name="tamanho-2lados"]:checked');
        const corInput = lado2WidgetCorGrupo && lado2WidgetCorGrupo.querySelector('input[name="cor-2lados"]:checked');
        const tamanho = tamanhoInput ? tamanhoInput.value : '14mm';
        const cor = corInput ? corInput.value : 'prata';
        return { chavePreco: 'medalha_2lados', tamanho, cor, subAttr: `${tamanho}/${cor}` };
      }
      if (formato2Lados === 'entremeio_2lados') {
        const corInput = coresFieldset.querySelector('input[name="cor"]:checked');
        if (!corInput) return null;
        return { chavePreco: 'entremeio_2lados', tamanho: null, cor: corInput.value, subAttr: corInput.value };
      }
      return { chavePreco: 'chaveiro_2lados', tamanho: null, cor: null, subAttr: '' };
    }
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
      if (barraFixaDetalhe) barraFixaDetalhe.hidden = true;
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

      // resumo persistente da barra fixa (aparece ao rolar a pagina) --
      // mesmos numeros do preview acima, so que continuam visiveis
      // mesmo depois que o preview sai da tela (ver conversa: "painel
      // de compra fixo" pedido pela auditoria da Manus).
      if (barraFixaDetalhe) {
        const COR_LABEL = { prata: 'Prata', ouro_velho: 'Ouro velho' };
        const variacao = resolvido.subAttr
          ? (COR_LABEL[resolvido.subAttr] || resolvido.subAttr)
          : '';
        // versao curta de proposito -- pouco espaco na barra fixa
        // (compartilhado com nome do produto + botao), preco unitario
        // ja aparece destacado no preview logo acima na pagina.
        barraFixaDetalhe.textContent =
          `${variacao ? variacao + ' · ' : ''}${quantidade} un · ${formatarPreco(itemPreview.subtotal)}`;
        barraFixaDetalhe.hidden = false;
        // esconde o "a partir de RX" generico -- ficaria redundante com
        // o preco de verdade que acabou de aparecer logo abaixo.
        if (barraFixaPreco) barraFixaPreco.hidden = true;
      }
    } catch (e) {
      previewPrecoEl.hidden = true;
      if (barraFixaDetalhe) barraFixaDetalhe.hidden = true;
    }
  }

  let previewPrecoTimer = null;
  function agendarAtualizarPreviewPreco() {
    clearTimeout(previewPrecoTimer);
    previewPrecoTimer = setTimeout(atualizarPreviewPreco, 300);
  }

  // preco base (generico, "a partir de") pro formato/toggle atuais --
  // compartilhado entre o aviso do topo e a barra fixa, pra nao duplicar
  // essa mesma conta em 2 lugares.
  function precoBaseAtual() {
    const formato = formatoAtual();
    if (duasFacesAtiva) {
      const formato2Lados = formato2LadosDe(formato);
      return formato2Lados === 'chaveiro_2lados' ? window.PRECO_VAREJO_CHAVEIRO : window.PRECO_VAREJO_2LADOS;
    }
    return formato === 'chaveiro' ? window.PRECO_VAREJO_CHAVEIRO : window.PRECO_VAREJO_PADRAO;
  }

  function atualizarAvisoPreco() {
    if (!avisoPreco) return;
    const preco = precoBaseAtual();
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
    if (duasFacesAtiva) return imagemLado1Atual();
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

  // tamanho de 1 lado (12/16mm) some quando o toggle de 2 lados esta
  // ligado -- o widget ja mostra o proprio tamanho (14/18mm, so faz
  // sentido pra medalha) mais abaixo, ter os dois visiveis ao mesmo
  // tempo confundia (ver conversa 2026-09-17).
  function atualizarVisibilidadeTamanho() {
    tamanhosFieldset.hidden = formatoAtual() !== 'medalha' || duasFacesAtiva;
  }

  // verso da peca (base inox lisa) so faz sentido pra medalha de 1 lado --
  // pedido 2026-09-24: nada de "acabamento maciço", so o rotulo simples
  // "VERSO: Base Inoxidável", visivel apenas junto do preview do modelo
  // ja escolhido (nao no topo da pagina).
  function atualizarVersoVisivel() {
    if (!previewVerso) return;
    const mostrar = formatoAtual() === 'medalha' && !duasFacesAtiva;
    previewVerso.hidden = !mostrar;
    if (previewWrap) previewWrap.classList.toggle('tem-verso', mostrar);
  }

  function atualizarSubSelecao() {
    const formato = formatoAtual();
    atualizarVisibilidadeTamanho();
    atualizarVersoVisivel();
    coresFieldset.hidden = formato !== 'entremeio';
    atualizarInfoFormato();
    atualizarAvisoPreco();
    atualizarToggleDisponibilidade();
    if (duasFacesAtiva) atualizar2LadosUI();
    atualizarPreview();
    atualizarBotao();
    atualizarPreviewPreco();
  }

  function atualizarBotao() {
    const formato = formatoAtual();
    let completo = true;
    let textoIncompleto = '';
    if (duasFacesAtiva) {
      // 2 lados: cor do entremeio (medalha/chaveiro ja vem com padrao
      // marcado no proprio widget, ver templates/produto.html) + o lado 2
      // escolhido sao as unicas pendencias possiveis aqui.
      if (formato === 'entremeio' && !coresFieldset.querySelector('input[name="cor"]:checked')) {
        completo = false;
        textoIncompleto = 'Selecione uma cor';
      } else if (!lado2Selecionado) {
        completo = false;
        textoIncompleto = 'Escolha o lado 2 acima';
      }
    } else if (formato === 'medalha') {
      completo = !!tamanhosFieldset.querySelector('input[name="tamanho"]:checked');
      textoIncompleto = 'Selecione um tamanho';
    } else if (formato === 'entremeio') {
      completo = !!coresFieldset.querySelector('input[name="cor"]:checked');
      textoIncompleto = 'Selecione uma cor';
    }
    if (!completo) {
      btnAdicionar.disabled = true;
      btnAdicionar.textContent = textoIncompleto;
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
      barraFixaPreco.textContent = `a partir de ${formatarPrecoLocal(precoBaseAtual())}`;
      // sempre reaparece aqui -- atualizarPreviewPreco (chamada logo em
      // seguida) esconde de novo se conseguir calcular o preco real,
      // senao fica esse generico visivel mesmo.
      barraFixaPreco.hidden = false;
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
    tamanhosFieldset.innerHTML = '<legend>Tamanho * <button type="button" class="link-guia-tamanhos" onclick="abrirGuiaTamanhos()">📏 Guia de tamanhos</button></legend>';
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
    desligarToggle2Lados();

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
      // troca de formato reseta o toggle de 2 lados -- a sub-selecao (cor/
      // tamanho) e o lado 2 ja escolhido nao fazem mais sentido no
      // formato novo (ver atualizarLado2SubSelecao).
      desligarToggle2Lados();
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
      // entremeio_2lados reaproveita esse MESMO seletor de cor (nao tem
      // um proprio, ver atualizarLado2SubSelecao) -- se o toggle esta
      // ligado, a imagem do lado 1 (e do lado 2, se ja escolhido) precisa
      // acompanhar a cor nova.
      if (duasFacesAtiva) {
        if (lado2Selecionado) refazerBuscaImagemLado2();
        atualizar2LadosUI();
      }
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

      // ---- 2 lados: monta o MESMO formato de item que static/js/
      // personalizada.js:btnAdicionar2f ja produz (tipo:"personalizada",
      // duasFaces:true, lado1/lado2) -- reaproveita o mesmo processo de
      // venda/CSV/link de venda, sem precisar de rota/formato novo la. ----
      if (duasFacesAtiva) {
        if (!lado2Selecionado) return;
        const lado1 = {
          origem: 'catalogo', imagem: imagemLado1Atual(),
          produtoId, produtoNome,
          modeloId: modeloSelecionado.id, modeloNome: modeloSelecionado.nome,
        };
        carrinhoAdicionarItem({
          chave: `personalizada-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          tipo: 'personalizada',
          duasFaces: true,
          produtoNome: 'Personalizada',
          modeloNome: null,
          formato: chavePreco,
          chave_preco: chavePreco,
          cor,
          tamanho,
          quantidade,
          semImagem: false,
          lado1,
          lado2: lado2Selecionado,
        });
        if (typeof carrinhoAtualizarContador === 'function') carrinhoAtualizarContador();
        if (typeof carrinhoAtualizarBarraPersistente === 'function') carrinhoAtualizarBarraPersistente();
        atualizarPreviewPreco();
        rastrearEventoGA4('add_custom_to_cart', { formato: chavePreco, quantity: quantidade, com_foto: true });

        // upsell "Cruz para Terco" -- entremeio de 2 lados tambem vai pro
        // terco, igual o de 1 lado (ver static/js/upsell_cruz.js).
        if (chavePreco === 'entremeio_2lados' && (cor === 'prata' || cor === 'ouro_velho') && typeof ofertarUpsellCruz === 'function') {
          setTimeout(() => ofertarUpsellCruz(cor, quantidade), 500);
        }

        const textoOriginal2f = 'Adicionar ao carrinho';
        btnAdicionar.textContent = 'Adicionado ✓';
        setTimeout(() => { btnAdicionar.textContent = textoOriginal2f; }, 1200);
        return;
      }

      // entremeio (1 lado) tem 2 cores com a MESMA imagem "estatica" do
      // modelo (nao depende de foto do cliente) e o MESMO preco (ver
      // services/pricing.py) -- guarda as 2 URLs no item pra permitir
      // trocar a cor direto no carrinho, trocando so a imagem, sem
      // precisar voltar nessa pagina (ver static/js/carrinho.js:
      // carrinhoAtualizarCor).
      const imagensCor = formato === 'entremeio'
        ? { prata: modeloSelecionado.imagens.entremeio_prata, ouro_velho: modeloSelecionado.imagens.entremeio_ouro_velho }
        : null;
      carrinhoAdicionarItem({
        chave: `${produtoId}-${modeloSelecionado.id}-${formato}-${subAttr}`,
        tipo: 'catalogo',
        produtoId,
        produtoNome,
        modeloId: modeloSelecionado.id,
        modeloNome: modeloSelecionado.nome,
        imagem: imagemParaFormato(),
        imagensCor,
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

      // upsell "Cruz para Terco" (ver static/js/upsell_cruz.js) -- so faz
      // sentido pra entremeio prata/ouro velho, que e´ o formato que
      // realmente vai junto num terco.
      if (formato === 'entremeio' && (cor === 'prata' || cor === 'ouro_velho') && typeof ofertarUpsellCruz === 'function') {
        setTimeout(() => ofertarUpsellCruz(cor, quantidade), 500);
      }

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
