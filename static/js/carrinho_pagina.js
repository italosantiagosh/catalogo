(function () {
  const listaEl = document.getElementById('lista-itens');
  const vazioEl = document.getElementById('carrinho-vazio');
  const resumoEl = document.getElementById('resumo-carrinho');
  const resumoQtdEl = document.getElementById('resumo-quantidade');
  const resumoSubtotalEl = document.getElementById('resumo-subtotal');
  const progressoGruposEl = document.getElementById('progresso-grupos');
  const progressoFreteTexto = document.getElementById('progresso-frete-texto');
  const progressoFretePreenchimento = document.getElementById('progresso-frete-preenchimento');
  const avisoMinimoEl = document.getElementById('aviso-minimo');
  const pedidoIdTexto = document.getElementById('pedido-id-texto');
  const btnWhatsappFinalizar = document.getElementById('btn-whatsapp-finalizar');
  const btnWhatsappDuvida = document.getElementById('btn-whatsapp-duvida');
  const formaPagamentoRadios = document.querySelectorAll('input[name="forma-pagamento"]');
  const cadastroClienteEl = document.getElementById('cadastro-cliente');
  const whatsappFinalizarWrapEl = document.getElementById('whatsapp-finalizar-wrap');
  const btnLimpar = document.getElementById('btn-limpar');
  const freteCepInput = document.getElementById('frete-cep');
  const btnCalcularFrete = document.getElementById('btn-calcular-frete');
  const freteResultadoEl = document.getElementById('frete-resultado');
  const nudgeDescontoEl = document.getElementById('nudge-desconto');
  const tipoPessoaFisica = document.getElementById('tipo-pessoa-fisica');
  const tipoPessoaJuridica = document.getElementById('tipo-pessoa-juridica');
  const labelClienteDocumento = document.getElementById('label-cliente-documento');
  const clienteNomeInput = document.getElementById('cliente-nome');
  const clienteDocumentoInput = document.getElementById('cliente-documento');
  const clienteTelefoneInput = document.getElementById('cliente-telefone');
  const clienteEmailInput = document.getElementById('cliente-email');
  const enderecoLogradouroInput = document.getElementById('endereco-logradouro');
  const enderecoNumeroInput = document.getElementById('endereco-numero');
  const enderecoComplementoInput = document.getElementById('endereco-complemento');
  const enderecoBairroInput = document.getElementById('endereco-bairro');
  const enderecoCidadeInput = document.getElementById('endereco-cidade');
  const enderecoUfInput = document.getElementById('endereco-uf');
  const checkboxEntregaOutraPessoa = document.getElementById('entrega-outra-pessoa');
  const camposDestinatarioEl = document.getElementById('campos-destinatario');
  const destinatarioNomeInput = document.getElementById('destinatario-nome');
  const destinatarioTipoPessoaFisica = document.getElementById('destinatario-tipo-pessoa-fisica');
  const destinatarioTipoPessoaJuridica = document.getElementById('destinatario-tipo-pessoa-juridica');
  const labelDestinatarioDocumento = document.getElementById('label-destinatario-documento');
  const destinatarioDocumentoInput = document.getElementById('destinatario-documento');
  const destinatarioCepInput = document.getElementById('destinatario-cep');
  const destinatarioLogradouroInput = document.getElementById('destinatario-logradouro');
  const destinatarioNumeroInput = document.getElementById('destinatario-numero');
  const destinatarioComplementoInput = document.getElementById('destinatario-complemento');
  const destinatarioBairroInput = document.getElementById('destinatario-bairro');
  const destinatarioCidadeInput = document.getElementById('destinatario-cidade');
  const destinatarioUfInput = document.getElementById('destinatario-uf');
  const btnPagarAgora = document.getElementById('btn-pagar-agora');
  if (!listaEl) return;

  const TAMANHO_LABEL = { '12mm': '1,2 cm', '16mm': '1,6 cm' };
  const COR_LABEL = { prata: 'Prata', ouro_velho: 'Ouro velho' };
  const FORMATO_LABEL = { medalha: 'Medalha', entremeio: 'Entremeio', chaveiro: 'Chaveiro' };
  const GRUPO_LABEL = { padrao: 'medalhas/entremeios', chaveiro: 'chaveiros' };

  let faixasAnteriores = {};
  let freteAnteriorAtingido = null;
  let primeiraRenderizacao = true;
  let ultimosItens = [];
  let ultimoCalculo = null;
  let freteEscolhido = null; // { texto, preco } -- preco null quando e frete gratis

  function detalheFormato(item) {
    const formato = item.formato || 'medalha';
    if (formato === 'entremeio') return `${FORMATO_LABEL.entremeio} · ${COR_LABEL[item.cor] || item.cor}`;
    if (formato === 'chaveiro') return FORMATO_LABEL.chaveiro;
    return `${FORMATO_LABEL.medalha} · ${TAMANHO_LABEL[item.tamanho] || item.tamanho}`;
  }

  function montarListaPedido(itens) {
    return itens
      .map((item, i) => {
        const numero = i + 1;
        const detalhe = detalheFormato(item);
        if (item.tipo === 'personalizada') {
          const notaFoto = item.semImagem
            ? 'Foto: ainda não enviada -- enviar nesta conversa'
            : `Foto: ${item.avisoReenvio || 'reenviar esta medalha nesta conversa (o link do WhatsApp não anexa imagem)'}`;
          return `${numero}. Personalizada\n${detalhe}\nQuantidade: ${item.quantidade}\n${notaFoto}`;
        }
        return `${numero}. ${item.produtoNome}\nModelo: ${item.modeloId}\n${detalhe}\nQuantidade: ${item.quantidade}`;
      })
      .join('\n\n');
  }

  function montarLinhasFaixas(calculo) {
    const linhas = [];
    for (const nomeGrupo of Object.keys(calculo.grupos)) {
      const grupo = calculo.grupos[nomeGrupo];
      if (grupo.quantidade_total === 0) continue;
      linhas.push(`Faixa de atacado (${GRUPO_LABEL[nomeGrupo] || nomeGrupo}):`, grupo.faixa_label, '');
    }
    return linhas;
  }

  function montarLinhasFrete() {
    if (freteEscolhido) return ['Frete:', freteEscolhido.texto, ''];
    // Frete nao simulado (comum em quem fecha direto pelo WhatsApp) --
    // se ja tiver digitado o CEP no calculo, manda mesmo assim, pra
    // quem for atender ja ter o dado sem precisar perguntar de novo.
    const cepDigitado = freteCepInput ? freteCepInput.value.trim() : '';
    if (!cepDigitado) return [];
    return ['CEP informado (frete ainda não calculado):', cepDigitado, ''];
  }

  function montarCorpoPedido(itens, calculo) {
    return [
      `PEDIDO #${obterOuCriarPedidoId()}`,
      '',
      'PEDIDO DE MEDALHAS',
      '',
      montarListaPedido(itens),
      '',
      '--------------------',
      '',
      'Quantidade total:',
      `${calculo.quantidade_total} peças`,
      '',
      ...montarLinhasFaixas(calculo),
      ...montarLinhasFrete(),
      'Valor estimado:',
      formatarPreco(calculo.subtotal_total),
    ].join('\n');
  }

  function abrirWhatsApp(mensagem) {
    const url = `https://wa.me/${window.WHATSAPP_NUMBER}?text=${encodeURIComponent(mensagem)}`;
    window.open(url, '_blank');
  }

  function mostrarToast(texto) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = texto;
    toast.hidden = false;
    clearTimeout(mostrarToast._timer);
    mostrarToast._timer = setTimeout(() => {
      toast.hidden = true;
    }, 2600);
  }

  function linhaItem(item, calculo) {
    const linha = document.createElement('article');
    linha.className = 'item-carrinho';
    const subtitulo = item.tipo === 'personalizada'
      ? detalheFormato(item)
      : `${item.modeloNome} &middot; ${detalheFormato(item)}`;
    let avisoFoto = '';
    if (item.tipo === 'personalizada') {
      avisoFoto = item.semImagem
        ? '<p class="item-aviso-foto">📷 Foto pendente -- enviar pelo WhatsApp</p>'
        : `<p class="item-aviso-foto">📲 ${item.avisoReenvio || 'Reenviar esta foto pelo WhatsApp ao finalizar'}</p>`;
    }
    linha.innerHTML = `
      <img src="${item.imagem}" alt="${item.produtoNome}">
      <div class="item-info">
        <h2>${item.produtoNome}</h2>
        <p>${subtitulo}</p>
        ${avisoFoto}
        <div class="item-stepper">
          <button type="button" class="qtd-menos" aria-label="Diminuir quantidade">−</button>
          <input type="number" class="item-qtd" value="${item.quantidade}" min="1" inputmode="numeric" aria-label="Quantidade">
          <button type="button" class="qtd-mais" aria-label="Aumentar quantidade">+</button>
        </div>
        <p class="item-preco">
          ${formatarPreco(calculo.preco_unitario)} un. &middot;
          <strong>${formatarPreco(calculo.subtotal)}</strong>
        </p>
      </div>
      <button type="button" class="item-remover" aria-label="Remover item">×</button>
    `;
    linha.querySelector('.qtd-menos').addEventListener('click', () => {
      carrinhoAtualizarQuantidade(item.chave, item.quantidade - 1);
      render();
    });
    linha.querySelector('.qtd-mais').addEventListener('click', () => {
      carrinhoAtualizarQuantidade(item.chave, item.quantidade + 1);
      render();
    });
    const inputQtd = linha.querySelector('.item-qtd');
    const confirmarQtdDigitada = () => {
      const quantidade = parseInt(inputQtd.value, 10);
      carrinhoAtualizarQuantidade(item.chave, Number.isFinite(quantidade) ? quantidade : 1);
      render();
    };
    inputQtd.addEventListener('change', confirmarQtdDigitada);
    inputQtd.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        inputQtd.blur();
      }
    });
    linha.querySelector('.item-remover').addEventListener('click', () => {
      carrinhoRemoverItem(item.chave);
      render();
    });
    return linha;
  }

  async function render() {
    const itens = carrinhoObterItens();
    listaEl.innerHTML = '';

    if (itens.length === 0) {
      vazioEl.hidden = false;
      resumoEl.hidden = true;
      return;
    }

    vazioEl.hidden = true;
    resumoEl.hidden = false;

    const resposta = await fetch('/api/carrinho/calcular', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        itens: itens.map((item) => ({ chave_preco: item.chave_preco, quantidade: item.quantidade })),
      }),
    });
    const dados = await resposta.json();

    listaEl.innerHTML = '';
    itens.forEach((item, i) => {
      listaEl.appendChild(linhaItem(item, dados.itens[i]));
    });

    resumoQtdEl.textContent = String(dados.quantidade_total);
    resumoSubtotalEl.textContent = formatarPreco(dados.subtotal_total);

    // barra de progresso: proxima faixa de desconto, uma por grupo ativo
    // (medalhas/entremeios e chaveiros nao se misturam -- services/pricing.py)
    progressoGruposEl.innerHTML = '';
    for (const nomeGrupo of Object.keys(dados.grupos)) {
      const grupo = dados.grupos[nomeGrupo];
      if (grupo.quantidade_total === 0) continue;
      const bloco = document.createElement('div');
      bloco.className = 'progresso-bloco';
      const texto = document.createElement('p');
      texto.className = 'progresso-texto';
      const preenchimento = document.createElement('div');
      preenchimento.className = 'barra-progresso-preenchimento';
      if (grupo.proxima_faixa) {
        texto.textContent =
          `${grupo.quantidade_total} / ${grupo.proxima_faixa.quantidade} ${GRUPO_LABEL[nomeGrupo] || nomeGrupo} — ` +
          `faltam ${grupo.proxima_faixa.faltam} para o próximo desconto`;
        preenchimento.style.width =
          _percentualBarra(grupo.quantidade_total, grupo.faixa_atual_inicio, grupo.proxima_faixa.quantidade) + '%';
      } else {
        texto.textContent = `🎉 Você já está na melhor faixa de preço de ${GRUPO_LABEL[nomeGrupo] || nomeGrupo}!`;
        preenchimento.style.width = '100%';
      }
      const barra = document.createElement('div');
      barra.className = 'barra-progresso';
      barra.appendChild(preenchimento);
      bloco.appendChild(texto);
      bloco.appendChild(barra);
      progressoGruposEl.appendChild(bloco);
    }

    // nudge de desconto perto do botao de finalizar -- reforca, no
    // momento da decisao de fechar o pedido, quanto falta pro proximo
    // preco por unidade (mesmo dado da barra de progresso acima, so
    // repetido onde importa mais pra conversao).
    if (nudgeDescontoEl) {
      nudgeDescontoEl.innerHTML = '';
      for (const nomeGrupo of Object.keys(dados.grupos)) {
        const grupo = dados.grupos[nomeGrupo];
        if (grupo.quantidade_total === 0 || !grupo.proxima_faixa) continue;
        const nudge = document.createElement('p');
        nudge.className = 'nudge-desconto';
        let texto =
          `💰 Faltam ${grupo.proxima_faixa.faltam} ${GRUPO_LABEL[nomeGrupo] || nomeGrupo} para o preço cair ` +
          `para ${formatarPreco(grupo.proxima_faixa.preco)}/un`;
        if (grupo.proxima_faixa.economia > 0) {
          texto += ` — seu pedido economiza ${formatarPreco(grupo.proxima_faixa.economia)}!`;
        } else {
          texto += ' — adicione mais antes de finalizar!';
        }
        nudge.textContent = texto;
        nudgeDescontoEl.appendChild(nudge);
      }
    }

    // barra de progresso: frete gratis
    if (dados.frete_gratis_atingido) {
      progressoFreteTexto.textContent = '🎉 Frete grátis desbloqueado!';
      progressoFretePreenchimento.style.width = '100%';
    } else {
      progressoFreteTexto.textContent =
        `Faltam ${formatarPreco(dados.falta_para_frete_gratis)} em compras para o frete grátis`;
      progressoFretePreenchimento.style.width =
        Math.min(100, (dados.subtotal_total / dados.frete_gratis_reais) * 100) + '%';
    }

    // view_cart -- so na primeira renderizacao da pagina (carrinho ja
    // tinha itens ao abrir/voltar pra ca), nao a cada recalculo.
    if (primeiraRenderizacao && itens.length > 0) {
      rastrearEventoGA4('view_cart', { currency: 'BRL', value: dados.subtotal_total, items: itens.length });
    }

    // toast de comemoracao -- so depois da primeira renderizacao, pra nao
    // disparar assim que a pagina abre com um carrinho ja em faixa alta.
    if (!primeiraRenderizacao) {
      const grupoMudou = Object.keys(dados.grupos).find(
        (g) => dados.grupos[g].quantidade_total > 0 && dados.grupos[g].faixa_label !== faixasAnteriores[g]
      );
      if (grupoMudou) {
        const itemDoGrupo = dados.itens.find((i) => GRUPO_DE_CHAVE[i.chave_preco] === grupoMudou);
        const preco = itemDoGrupo ? itemDoGrupo.preco_unitario : null;
        mostrarToast(`🎉 Novo desconto desbloqueado (${GRUPO_LABEL[grupoMudou] || grupoMudou})! Agora ${formatarPreco(preco)}/un`);
        rastrearEventoGA4('reach_wholesale_tier', {
          grupo: grupoMudou,
          faixa: dados.grupos[grupoMudou].faixa_label,
          preco_unitario: preco,
        });
      } else if (dados.frete_gratis_atingido && !freteAnteriorAtingido) {
        mostrarToast('🎉 Frete grátis desbloqueado!');
        rastrearEventoGA4('reach_free_shipping', { subtotal: dados.subtotal_total });
      }
    }
    faixasAnteriores = Object.fromEntries(
      Object.keys(dados.grupos).map((g) => [g, dados.grupos[g].faixa_label])
    );
    freteAnteriorAtingido = dados.frete_gratis_atingido;
    primeiraRenderizacao = false;

    if (!dados.atinge_minimo) {
      const faltamParaMinimo = dados.pedido_minimo_reais - dados.subtotal_total;
      avisoMinimoEl.hidden = false;
      avisoMinimoEl.textContent =
        `Faltam ${formatarPreco(faltamParaMinimo)} em produtos para o pedido mínimo de ` +
        `${formatarPreco(dados.pedido_minimo_reais)}. Esse valor é somente em produtos -- o frete ` +
        `é calculado à parte e não entra nessa conta.`;
    } else {
      avisoMinimoEl.hidden = true;
    }

    // cart mudou -- qualquer frete calculado antes nao vale mais (peso/
    // faixa de frete gratis podem ter mudado), pede pra recalcular.
    freteEscolhido = null;
    if (freteResultadoEl) freteResultadoEl.innerHTML = '';

    ultimosItens = itens;
    ultimoCalculo = dados;
    pedidoIdTexto.textContent = `Pedido #${obterOuCriarPedidoId()}`;
  }

  // ---- calculadora de frete (Frenet) ----

  function mascararCep(valor) {
    const digitos = valor.replace(/\D/g, '').slice(0, 8);
    return digitos.length > 5 ? `${digitos.slice(0, 5)}-${digitos.slice(5)}` : digitos;
  }

  // preenche endereco/bairro/cidade/UF automaticamente a partir do CEP
  // (ViaCEP -- servico publico gratuito, sem chave) assim que o cliente
  // termina de digitar os 8 digitos. Falha silenciosamente (CEP nao
  // encontrado, ou servico fora do ar) -- o cliente sempre pode
  // preencher esses campos na mao, o autopreenchimento e so conveniencia.
  // Recebe os inputs de destino (endereco principal ou destinatario,
  // ver os dois listeners logo abaixo) pra reaproveitar a mesma logica.
  async function preencherEnderecoPorCep(cep, inputs) {
    try {
      const resposta = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const dados = await resposta.json();
      if (dados.erro) return;
      if (inputs.logradouro) inputs.logradouro.value = dados.logradouro || '';
      if (inputs.bairro) inputs.bairro.value = dados.bairro || '';
      if (inputs.cidade) inputs.cidade.value = dados.localidade || '';
      if (inputs.uf) inputs.uf.value = dados.uf || '';
    } catch (e) {
      // silencioso -- ver comentario acima
    }
  }

  // ---- calculo de frete reaproveitavel (endereco principal OU de
  // entrega -- ver destinatario-cep abaixo: quando a entrega e´ num
  // endereco diferente, o frete tem que refletir o CEP de verdade pra
  // onde o pacote vai, nao o CEP do endereco principal) ----
  async function calcularFreteParaCep(cep) {
    if (!cep || cep.length !== 8) return;
    const itens = carrinhoObterItens();
    if (itens.length === 0) return;
    try {
      const resposta = await fetch('/api/frete/calcular', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cep,
          itens: itens.map((item) => ({ chave_preco: item.chave_preco, quantidade: item.quantidade })),
        }),
      });
      const dados = await resposta.json();
      renderizarFrete(dados);
    } catch (e) {
      if (freteResultadoEl) freteResultadoEl.innerHTML = '<p class="frete-erro">Não foi possível calcular o frete agora.</p>';
    }
  }

  if (freteCepInput) {
    freteCepInput.addEventListener('input', () => {
      freteCepInput.value = mascararCep(freteCepInput.value);
      const digitos = freteCepInput.value.replace(/\D/g, '');
      if (digitos.length === 8) {
        preencherEnderecoPorCep(digitos, {
          logradouro: enderecoLogradouroInput, bairro: enderecoBairroInput,
          cidade: enderecoCidadeInput, uf: enderecoUfInput,
        });
      }
    });
  }

  if (destinatarioCepInput) {
    destinatarioCepInput.addEventListener('input', () => {
      destinatarioCepInput.value = mascararCep(destinatarioCepInput.value);
      const digitos = destinatarioCepInput.value.replace(/\D/g, '');
      if (digitos.length === 8) {
        preencherEnderecoPorCep(digitos, {
          logradouro: destinatarioLogradouroInput, bairro: destinatarioBairroInput,
          cidade: destinatarioCidadeInput, uf: destinatarioUfInput,
        });
        // entrega vai pra esse CEP, entao o frete precisa ser
        // recalculado com base nele, nao no CEP do endereco principal
        calcularFreteParaCep(digitos);
      }
    });
  }

  // marca visualmente qual opcao esta selecionada e atualiza freteEscolhido
  // -- compartilhado pelos dois formatos (frete gratis com opcoes / frete
  // pago), pra clicar em qualquer uma trocar a escolha, nao so a primeira.
  function selecionarOpcaoFrete(botao, escolha) {
    freteResultadoEl.querySelectorAll('.frete-opcao').forEach((el) => {
      el.setAttribute('aria-pressed', String(el === botao));
    });
    freteEscolhido = escolha;
  }

  function renderizarFrete(dados) {
    freteEscolhido = null;
    if (!freteResultadoEl) return;

    if (dados.erro) {
      freteResultadoEl.innerHTML = `<p class="frete-erro">${dados.erro}</p>`;
      return;
    }

    if (dados.frete_gratis) {
      if (!dados.opcoes || dados.opcoes.length === 0) {
        freteEscolhido = { texto: 'Grátis', preco: 0 };
        freteResultadoEl.innerHTML = `<p class="frete-gratis-aviso">🎉 ${dados.aviso}</p>`;
        return;
      }

      freteResultadoEl.innerHTML = `<p class="frete-gratis-aviso">🎉 ${dados.aviso}</p>`;
      dados.opcoes.forEach((opcao, i) => {
        const botao = document.createElement('button');
        botao.type = 'button';
        botao.className = 'frete-opcao';
        botao.setAttribute('aria-pressed', 'false');
        const prazo = opcao.prazo_dias ? `${opcao.prazo_dias} dia(s) úteis` : '';
        const rotulo = opcao.gratis
          ? '<span class="frete-opcao-gratis">Grátis</span>'
          : `<span class="frete-opcao-por">Por ${formatarPreco(opcao.preco_final)}</span>`;
        botao.innerHTML = `
          <div>
            <div class="frete-opcao-nome">${opcao.transportadora} — ${opcao.servico}</div>
            <div class="frete-opcao-prazo">${prazo}</div>
          </div>
          <div class="frete-opcao-preco">
            <span class="frete-opcao-preco-original">${formatarPreco(opcao.preco_original)}</span>
            ${rotulo}
          </div>
        `;
        const escolha = { texto: `${opcao.transportadora} ${opcao.servico} — Grátis`, preco: 0 };
        botao.addEventListener('click', () => selecionarOpcaoFrete(botao, escolha));
        freteResultadoEl.appendChild(botao);
        if (i === 0) selecionarOpcaoFrete(botao, escolha);
      });
      return;
    }

    if (!dados.opcoes || dados.opcoes.length === 0) {
      freteResultadoEl.innerHTML = '<p class="frete-erro">Nenhuma opção de frete encontrada para esse CEP.</p>';
      return;
    }

    freteResultadoEl.innerHTML = '';
    dados.opcoes.forEach((opcao, i) => {
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.className = 'frete-opcao';
      botao.setAttribute('aria-pressed', 'false');
      const prazo = opcao.prazo_dias ? `${opcao.prazo_dias} dia(s) úteis` : '';
      botao.innerHTML = `
        <div>
          <div class="frete-opcao-nome">${opcao.transportadora} — ${opcao.servico}</div>
          <div class="frete-opcao-prazo">${prazo}</div>
        </div>
        <div class="frete-opcao-preco">${formatarPreco(opcao.preco)}</div>
      `;
      const escolha = {
        texto: `${opcao.transportadora} ${opcao.servico} — ${formatarPreco(opcao.preco)}`,
        preco: opcao.preco,
      };
      botao.addEventListener('click', () => selecionarOpcaoFrete(botao, escolha));
      freteResultadoEl.appendChild(botao);
      if (i === 0) selecionarOpcaoFrete(botao, escolha);
    });
  }

  if (btnCalcularFrete) {
    btnCalcularFrete.addEventListener('click', async () => {
      const cep = (freteCepInput.value || '').replace(/\D/g, '');
      if (cep.length !== 8) {
        freteResultadoEl.innerHTML = '<p class="frete-erro">Digite um CEP válido.</p>';
        return;
      }
      btnCalcularFrete.disabled = true;
      btnCalcularFrete.textContent = 'Calculando...';
      await calcularFreteParaCep(cep);
      btnCalcularFrete.disabled = false;
      btnCalcularFrete.textContent = 'Calcular';
    });
  }

  // ---- cadastro + pagamento automatico (InfinitePay) ----

  function atualizarLabelDocumento() {
    if (!labelClienteDocumento) return;
    labelClienteDocumento.textContent = (tipoPessoaJuridica && tipoPessoaJuridica.checked) ? 'CNPJ' : 'CPF';
  }
  if (tipoPessoaFisica) tipoPessoaFisica.addEventListener('change', atualizarLabelDocumento);
  if (tipoPessoaJuridica) tipoPessoaJuridica.addEventListener('change', atualizarLabelDocumento);

  if (checkboxEntregaOutraPessoa && camposDestinatarioEl) {
    checkboxEntregaOutraPessoa.addEventListener('change', () => {
      camposDestinatarioEl.hidden = !checkboxEntregaOutraPessoa.checked;
      // desmarcou -- volta o frete a refletir o CEP do endereco
      // principal (pode ter ficado calculado pro CEP de entrega
      // enquanto a caixa estava marcada, ver destinatario-cep acima)
      if (!checkboxEntregaOutraPessoa.checked) {
        const cepPrincipal = (freteCepInput.value || '').replace(/\D/g, '');
        if (cepPrincipal.length === 8) calcularFreteParaCep(cepPrincipal);
      }
    });
  }

  if (formaPagamentoRadios.length && cadastroClienteEl && whatsappFinalizarWrapEl) {
    formaPagamentoRadios.forEach((radio) => {
      radio.addEventListener('change', () => {
        cadastroClienteEl.hidden = radio.value !== 'site';
        whatsappFinalizarWrapEl.hidden = radio.value !== 'whatsapp';
        if (radio.checked && radio.value === 'site') {
          cadastroClienteEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  function atualizarLabelDocumentoDestinatario() {
    if (!labelDestinatarioDocumento) return;
    labelDestinatarioDocumento.textContent =
      (destinatarioTipoPessoaJuridica && destinatarioTipoPessoaJuridica.checked) ? 'CNPJ' : 'CPF';
  }
  if (destinatarioTipoPessoaFisica) destinatarioTipoPessoaFisica.addEventListener('change', atualizarLabelDocumentoDestinatario);
  if (destinatarioTipoPessoaJuridica) destinatarioTipoPessoaJuridica.addEventListener('change', atualizarLabelDocumentoDestinatario);

  if (btnPagarAgora) {
    btnPagarAgora.addEventListener('click', async () => {
      if (!ultimoCalculo) return;

      if (!ultimoCalculo.atinge_minimo) {
        const faltamParaMinimo = ultimoCalculo.pedido_minimo_reais - ultimoCalculo.subtotal_total;
        mostrarToast(
          `⚠️ Faltam ${formatarPreco(faltamParaMinimo)} em produtos para o pedido mínimo de ` +
          `${formatarPreco(ultimoCalculo.pedido_minimo_reais)} (o frete é à parte).`
        );
        if (avisoMinimoEl) avisoMinimoEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
      if (!freteEscolhido) {
        mostrarToast('⚠️ Calcule o frete e escolha uma opção antes de pagar.');
        if (freteResultadoEl) freteResultadoEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }

      const cliente = {
        nome: (clienteNomeInput.value || '').trim(),
        tipo_pessoa: (tipoPessoaJuridica && tipoPessoaJuridica.checked) ? 'juridica' : 'fisica',
        documento: (clienteDocumentoInput.value || '').trim(),
        telefone: (clienteTelefoneInput.value || '').trim(),
        email: (clienteEmailInput.value || '').trim(),
      };
      const endereco = {
        cep: (freteCepInput.value || '').replace(/\D/g, ''),
        logradouro: (enderecoLogradouroInput.value || '').trim(),
        numero: (enderecoNumeroInput.value || '').trim(),
        complemento: (enderecoComplementoInput.value || '').trim(),
        bairro: (enderecoBairroInput.value || '').trim(),
        cidade: (enderecoCidadeInput.value || '').trim(),
        uf: (enderecoUfInput.value || '').trim(),
      };

      if (!cliente.nome || !cliente.documento || !cliente.telefone || !cliente.email) {
        mostrarToast('⚠️ Preencha seus dados completos antes de pagar.');
        return;
      }
      if (!endereco.cep || !endereco.logradouro || !endereco.numero || !endereco.bairro || !endereco.cidade || !endereco.uf) {
        mostrarToast('⚠️ Preencha o endereço completo (e o CEP no calculador de frete) antes de pagar.');
        return;
      }

      if (checkboxEntregaOutraPessoa && checkboxEntregaOutraPessoa.checked) {
        endereco.destinatario_nome = (destinatarioNomeInput.value || '').trim();
        endereco.destinatario_tipo_pessoa =
          (destinatarioTipoPessoaJuridica && destinatarioTipoPessoaJuridica.checked) ? 'juridica' : 'fisica';
        endereco.destinatario_documento = (destinatarioDocumentoInput.value || '').trim();
        if (!endereco.destinatario_nome || !endereco.destinatario_documento) {
          mostrarToast('⚠️ Preencha o nome e o documento de quem vai receber.');
          return;
        }

        // endereco de entrega diferente e´ opcional -- se nenhum campo
        // foi preenchido, a entrega usa o endereco principal acima
        // (mesmo destinatario, endereco igual). Se algum foi, todos
        // (menos complemento) precisam vir, senao falta dado na etiqueta.
        const enderecoDestCampos = {
          destinatario_cep: (destinatarioCepInput.value || '').replace(/\D/g, ''),
          destinatario_logradouro: (destinatarioLogradouroInput.value || '').trim(),
          destinatario_numero: (destinatarioNumeroInput.value || '').trim(),
          destinatario_bairro: (destinatarioBairroInput.value || '').trim(),
          destinatario_cidade: (destinatarioCidadeInput.value || '').trim(),
          destinatario_uf: (destinatarioUfInput.value || '').trim(),
        };
        const algumPreenchido = Object.values(enderecoDestCampos).some((v) => v);
        const todosPreenchidos = Object.values(enderecoDestCampos).every((v) => v);
        if (algumPreenchido && !todosPreenchidos) {
          mostrarToast('⚠️ Preencha o endereço de entrega completo (ou deixe tudo em branco pra usar o endereço principal).');
          return;
        }
        if (todosPreenchidos) {
          Object.assign(endereco, enderecoDestCampos);
          endereco.destinatario_complemento = (destinatarioComplementoInput.value || '').trim();
        }
      }

      btnPagarAgora.disabled = true;
      btnPagarAgora.textContent = 'Gerando pagamento...';
      try {
        const resposta = await fetch('/api/pedido/criar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ itens: ultimosItens, frete: freteEscolhido, cliente, endereco }),
        });
        const dados = await resposta.json();
        if (!resposta.ok || dados.erro) {
          mostrarToast(`⚠️ ${dados.erro || 'Não foi possível gerar o pagamento agora.'}`);
          return;
        }
        rastrearEventoGA4('begin_checkout', { currency: 'BRL', value: ultimoCalculo.subtotal_total });
        window.location.href = dados.url;
      } catch (e) {
        mostrarToast('⚠️ Não foi possível gerar o pagamento agora.');
      } finally {
        btnPagarAgora.disabled = false;
        btnPagarAgora.textContent = '💳 Pagar agora (Pix ou cartão)';
      }
    });
  }

  if (btnLimpar) {
    btnLimpar.addEventListener('click', () => {
      if (confirm('Limpar todo o carrinho?')) {
        carrinhoLimpar();
        render();
      }
    });
  }

  function rastrearConversao(valor) {
    // Conversao real desse site e "cliente manda o pedido pelo WhatsApp"
    // -- nao ha compra confirmada aqui (isso acontece la fora, na
    // conversa), entao o evento certo e "lead", nao "purchase".
    // begin_whatsapp_checkout e o evento de funil (diagnostico, granular);
    // generate_lead/Lead sao os sinais de conversao pros leiloes de anuncio
    // do Google/Meta -- os dois fazem sentido juntos, propositos diferentes.
    rastrearEventoGA4('begin_whatsapp_checkout', { currency: 'BRL', value: valor });
    if (typeof gtag === 'function') {
      gtag('event', 'generate_lead', { currency: 'BRL', value: valor });
    }
    if (typeof fbq === 'function') {
      fbq('track', 'Lead', { currency: 'BRL', value: valor });
    }
  }

  if (btnWhatsappFinalizar) {
    btnWhatsappFinalizar.addEventListener('click', () => {
      if (!ultimoCalculo) return;
      if (!ultimoCalculo.atinge_minimo) {
        const faltamParaMinimo = ultimoCalculo.pedido_minimo_reais - ultimoCalculo.subtotal_total;
        mostrarToast(
          `⚠️ Faltam ${formatarPreco(faltamParaMinimo)} em produtos para o pedido mínimo de ` +
          `${formatarPreco(ultimoCalculo.pedido_minimo_reais)} (o frete é à parte).`
        );
        if (avisoMinimoEl) avisoMinimoEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
      const mensagem =
        'Olá! Gostaria de fazer este pedido:\n\n' +
        montarCorpoPedido(ultimosItens, ultimoCalculo) +
        '\n\nGostaria de finalizar este pedido.';
      rastrearConversao(ultimoCalculo.subtotal_total);
      abrirWhatsApp(mensagem);
    });
  }

  if (btnWhatsappDuvida) {
    btnWhatsappDuvida.addEventListener('click', () => {
      if (!ultimoCalculo) return;
      const mensagem =
        'Olá! Estou montando este pedido e gostaria de tirar uma dúvida:\n\n' +
        montarCorpoPedido(ultimosItens, ultimoCalculo) +
        '\n\nMinha dúvida é:';
      rastrearEventoGA4('whatsapp_question', { currency: 'BRL', value: ultimoCalculo.subtotal_total });
      abrirWhatsApp(mensagem);
    });
  }

  render();
})();
