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
  const erroClienteDocumentoEl = document.getElementById('erro-cliente-documento');
  const clienteIeWrap = document.getElementById('cliente-ie-wrap');
  const clienteIeInput = document.getElementById('cliente-ie');
  const clienteIeIsentoCheckbox = document.getElementById('cliente-ie-isento');
  const clienteIeNaoContribuinteCheckbox = document.getElementById('cliente-ie-nao-contribuinte');
  const clienteTelefoneInput = document.getElementById('cliente-telefone');
  const clienteEmailInput = document.getElementById('cliente-email');
  const enderecoCepProprioWrap = document.getElementById('endereco-cep-proprio-wrap');
  const enderecoCepProprioInput = document.getElementById('endereco-cep-proprio');
  const btnBuscarCepProprio = document.getElementById('btn-buscar-cep-proprio');
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
  const erroDestinatarioDocumentoEl = document.getElementById('erro-destinatario-documento');
  const destinatarioCepInput = document.getElementById('destinatario-cep');
  const btnBuscarCepDestinatario = document.getElementById('btn-buscar-cep-destinatario');
  const destinatarioLogradouroInput = document.getElementById('destinatario-logradouro');
  const destinatarioNumeroInput = document.getElementById('destinatario-numero');
  const destinatarioComplementoInput = document.getElementById('destinatario-complemento');
  const destinatarioBairroInput = document.getElementById('destinatario-bairro');
  const destinatarioCidadeInput = document.getElementById('destinatario-cidade');
  const destinatarioUfInput = document.getElementById('destinatario-uf');
  const btnPagarAgora = document.getElementById('btn-pagar-agora');
  const btnGerarBoleto = document.getElementById('btn-gerar-boleto');
  const boletoAviso2DiasEl = document.getElementById('boleto-aviso-2dias');
  if (!listaEl) return;

  const TAMANHO_LABEL = { '12mm': '1,2 cm', '16mm': '1,6 cm' };
  const COR_LABEL = { prata: 'Prata', ouro_velho: 'Ouro velho' };
  const FORMATO_LABEL = { medalha: 'Medalha', entremeio: 'Entremeio', chaveiro: 'Chaveiro' };
  const GRUPO_LABEL = { padrao: 'medalhas/entremeios', chaveiro: 'chaveiros' };
  // mesmo texto usado em app.py (FRETE_RETIRADA_DESCRICAO) pra detectar
  // esse tipo de frete e trocar os rotulos da timeline ("enviado" nao
  // faz sentido pra quem vai retirar -- ver conversa).
  const FRETE_RETIRADA_TEXTO = 'Retirada no local';

  // mesmo algoritmo (digito verificador modulo-11 da Receita Federal)
  // que services/documentos.py -- valida SO o formato/digito, nao
  // confirma que o CPF/CNPJ existe cadastrado de verdade (ver
  // conversa "verificar CPF ou CNPJ...pra saber se e existente" --
  // isso e´ sobre pegar erro de digitacao, uma consulta real exigiria
  // API paga de terceiro). O servidor SEMPRE reconfere isso tambem
  // (nunca confia so na validacao do navegador).
  function cpfValido(cpf) {
    const digitos = (cpf || '').replace(/\D/g, '');
    if (digitos.length !== 11 || /^(\d)\1{10}$/.test(digitos)) return false;
    for (const i of [9, 10]) {
      let soma = 0;
      for (let num = 0; num < i; num++) soma += parseInt(digitos[num], 10) * ((i + 1) - num);
      const digito = ((soma * 10) % 11) % 10;
      if (digito !== parseInt(digitos[i], 10)) return false;
    }
    return true;
  }

  function cnpjValido(cnpj) {
    const digitos = (cnpj || '').replace(/\D/g, '');
    if (digitos.length !== 14 || /^(\d)\1{13}$/.test(digitos)) return false;
    const pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    const pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    let soma1 = 0;
    for (let i = 0; i < 12; i++) soma1 += parseInt(digitos[i], 10) * pesos1[i];
    let d1 = 11 - (soma1 % 11);
    d1 = d1 >= 10 ? 0 : d1;
    if (d1 !== parseInt(digitos[12], 10)) return false;
    let soma2 = 0;
    for (let i = 0; i < 13; i++) soma2 += parseInt(digitos[i], 10) * pesos2[i];
    let d2 = 11 - (soma2 % 11);
    d2 = d2 >= 10 ? 0 : d2;
    if (d2 !== parseInt(digitos[13], 10)) return false;
    return true;
  }

  function documentoValido(tipoPessoa, documento) {
    return tipoPessoa === 'juridica' ? cnpjValido(documento) : cpfValido(documento);
  }

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
            : 'Foto: já anexada ao pedido, disponível no painel';
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

  function montarCorpoPedido(itens, calculo, codigo) {
    return [
      `PEDIDO #${codigo || obterOuCriarPedidoId()}`,
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

  function abrirWhatsApp(mensagem, janelaExistente) {
    const url = `https://wa.me/${window.WHATSAPP_NUMBER}?text=${encodeURIComponent(mensagem)}`;
    // se ja tem uma aba aberta (ver btnWhatsappFinalizar -- aberta em
    // branco ANTES do "await" pra nao ser bloqueada como pop-up pelo
    // Safari/iOS, que so permite window.open sincrono dentro do gesto
    // de clique), so navega ela em vez de abrir uma nova.
    if (janelaExistente) {
      janelaExistente.location.href = url;
    } else {
      window.open(url, '_blank');
    }
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
        : '<p class="item-aviso-foto">✅ Foto salva junto com o pedido</p>';
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

  // destrava os campos preenchidos por CEP (ver preencherEnderecoPorCep
  // abaixo) -- chamado assim que o cliente comeca a mexer de novo no
  // CEP, antes mesmo da busca terminar, pra nunca deixar campo travado
  // com um endereco que nao bate mais com o CEP mostrado.
  function destravarCamposEndereco(inputs) {
    [inputs.logradouro, inputs.bairro, inputs.cidade, inputs.uf].forEach((campo) => {
      if (campo) campo.readOnly = false;
    });
  }

  // preenche endereco/bairro/cidade/UF automaticamente a partir do CEP
  // (ViaCEP -- servico publico gratuito, sem chave) e trava esses 4
  // campos (readonly) pra nao dar pra digitar um endereco que nao bate
  // com o CEP escolhido (ver conversa) -- numero/complemento continuam
  // editaveis, o ViaCEP nunca devolve isso. Falha silenciosamente (CEP
  // nao encontrado, ou servico fora do ar) e NAO trava nesse caso -- o
  // cliente sempre pode preencher esses campos na mao quando o
  // autopreenchimento nao funciona. Recebe os inputs de destino
  // (endereco principal ou destinatario) pra reaproveitar a mesma
  // logica nos tres lugares que usam CEP (frete-cep, endereco-cep-proprio,
  // destinatario-cep).
  async function preencherEnderecoPorCep(cep, inputs) {
    try {
      const resposta = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const dados = await resposta.json();
      if (dados.erro) return;
      if (inputs.logradouro) inputs.logradouro.value = dados.logradouro || '';
      if (inputs.bairro) inputs.bairro.value = dados.bairro || '';
      if (inputs.cidade) inputs.cidade.value = dados.localidade || '';
      if (inputs.uf) inputs.uf.value = dados.uf || '';
      [inputs.logradouro, inputs.bairro, inputs.cidade, inputs.uf].forEach((campo) => {
        if (campo && campo.value) campo.readOnly = true;
      });
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
      if (!dados.erro) rastrearEventoGA4('calculate_shipping', {});
    } catch (e) {
      if (freteResultadoEl) freteResultadoEl.innerHTML = '<p class="frete-erro">Não foi possível calcular o frete agora.</p>';
    }
  }

  // mesmos 4 campos (endereco-logradouro/bairro/cidade/uf) sao
  // preenchidos tanto pelo CEP la em cima ("Calcular frete", endereco =
  // entrega quando NAO tem destinatario diferente) quanto pelo campo
  // dedicado "Seu CEP" que aparece dentro do cadastro quando o
  // checkbox de entrega-outra-pessoa e´ marcado (ver mais abaixo) --
  // e´ sempre o MESMO endereco do comprador, so muda de onde vem o CEP.
  const INPUTS_ENDERECO_PROPRIO = {
    logradouro: enderecoLogradouroInput, bairro: enderecoBairroInput,
    cidade: enderecoCidadeInput, uf: enderecoUfInput,
  };
  const INPUTS_ENDERECO_DESTINATARIO = {
    logradouro: destinatarioLogradouroInput, bairro: destinatarioBairroInput,
    cidade: destinatarioCidadeInput, uf: destinatarioUfInput,
  };

  if (freteCepInput) {
    freteCepInput.addEventListener('input', () => {
      freteCepInput.value = mascararCep(freteCepInput.value);
      // com entrega-outra-pessoa marcado, o endereco do comprador vem
      // do campo dedicado (endereco-cep-proprio) -- esse CEP aqui em
      // cima passa a servir so pra estimar o frete antes de saber quem
      // recebe, nao mexe mais no endereco do comprador nesse caso (ver
      // conversa: misturar os dois e´ o que causava o erro de "CEP do
      // comprador diferente do CEP de entrega").
      if (checkboxEntregaOutraPessoa && checkboxEntregaOutraPessoa.checked) return;
      destravarCamposEndereco(INPUTS_ENDERECO_PROPRIO);
      const digitos = freteCepInput.value.replace(/\D/g, '');
      if (digitos.length === 8) preencherEnderecoPorCep(digitos, INPUTS_ENDERECO_PROPRIO);
    });
  }

  if (enderecoCepProprioInput) {
    enderecoCepProprioInput.addEventListener('input', () => {
      enderecoCepProprioInput.value = mascararCep(enderecoCepProprioInput.value);
      destravarCamposEndereco(INPUTS_ENDERECO_PROPRIO);
      const digitos = enderecoCepProprioInput.value.replace(/\D/g, '');
      if (digitos.length === 8) preencherEnderecoPorCep(digitos, INPUTS_ENDERECO_PROPRIO);
    });
  }
  if (btnBuscarCepProprio) {
    btnBuscarCepProprio.addEventListener('click', () => {
      const digitos = (enderecoCepProprioInput.value || '').replace(/\D/g, '');
      if (digitos.length !== 8) { mostrarToast('⚠️ Digite um CEP válido.'); return; }
      preencherEnderecoPorCep(digitos, INPUTS_ENDERECO_PROPRIO);
    });
  }

  if (destinatarioCepInput) {
    destinatarioCepInput.addEventListener('input', () => {
      destinatarioCepInput.value = mascararCep(destinatarioCepInput.value);
      destravarCamposEndereco(INPUTS_ENDERECO_DESTINATARIO);
      const digitos = destinatarioCepInput.value.replace(/\D/g, '');
      if (digitos.length === 8) {
        preencherEnderecoPorCep(digitos, INPUTS_ENDERECO_DESTINATARIO);
        // entrega vai pra esse CEP, entao o frete precisa ser
        // recalculado com base nele, nao no CEP do endereco principal
        calcularFreteParaCep(digitos);
      }
    });
  }
  if (btnBuscarCepDestinatario) {
    btnBuscarCepDestinatario.addEventListener('click', () => {
      const digitos = (destinatarioCepInput.value || '').replace(/\D/g, '');
      if (digitos.length !== 8) { mostrarToast('⚠️ Digite um CEP válido.'); return; }
      preencherEnderecoPorCep(digitos, INPUTS_ENDERECO_DESTINATARIO);
      calcularFreteParaCep(digitos);
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

  // opcao de retirada no local -- sempre por ultimo entre as opcoes de
  // frete (ver conversa: "essa opção de retirada deve ser a última dos
  // fretes"), reaproveitando o mesmo botao .frete-opcao e a mesma
  // selecionarOpcaoFrete pra entrar no rodizio de selecao/deselecao.
  // So aparece depois de calcular o frete pra um CEP (nao antes), porque
  // ela e´ mais uma opcao dentro da lista, nao um atalho separado.
  function adicionarOpcaoRetirada() {
    if (!freteResultadoEl) return;
    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = 'frete-opcao';
    botao.setAttribute('aria-pressed', 'false');
    botao.innerHTML = `
      <div>
        <div class="frete-opcao-nome">🏬 Retirar no local</div>
        <div class="frete-opcao-prazo">Combina o horário depois que o pedido ficar pronto — Rua Furnas, 4835, Neópolis, Natal/RN</div>
      </div>
      <div class="frete-opcao-preco"><span class="frete-opcao-gratis">Grátis</span></div>
    `;
    const escolha = { texto: FRETE_RETIRADA_TEXTO, preco: 0, prazo_dias: null };
    botao.addEventListener('click', () => selecionarOpcaoFrete(botao, escolha));
    freteResultadoEl.appendChild(botao);
  }

  function renderizarFrete(dados) {
    freteEscolhido = null;
    if (!freteResultadoEl) return;

    if (dados.erro) {
      freteResultadoEl.innerHTML = `<p class="frete-erro">${dados.erro}</p>`;
      adicionarOpcaoRetirada();
      return;
    }

    if (dados.frete_gratis) {
      if (!dados.opcoes || dados.opcoes.length === 0) {
        freteEscolhido = { texto: 'Grátis', preco: 0 };
        freteResultadoEl.innerHTML = `<p class="frete-gratis-aviso">🎉 ${dados.aviso}</p>`;
        adicionarOpcaoRetirada();
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
        const escolha = { texto: `${opcao.transportadora} ${opcao.servico} — Grátis`, preco: 0, prazo_dias: opcao.prazo_dias || null };
        botao.addEventListener('click', () => selecionarOpcaoFrete(botao, escolha));
        freteResultadoEl.appendChild(botao);
        if (i === 0) selecionarOpcaoFrete(botao, escolha);
      });
      adicionarOpcaoRetirada();
      return;
    }

    if (!dados.opcoes || dados.opcoes.length === 0) {
      freteResultadoEl.innerHTML = '<p class="frete-erro">Nenhuma opção de frete encontrada para esse CEP.</p>';
      adicionarOpcaoRetirada();
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
        prazo_dias: opcao.prazo_dias || null,
      };
      botao.addEventListener('click', () => selecionarOpcaoFrete(botao, escolha));
      freteResultadoEl.appendChild(botao);
      if (i === 0) selecionarOpcaoFrete(botao, escolha);
    });
    adicionarOpcaoRetirada();
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
    const ehJuridica = tipoPessoaJuridica && tipoPessoaJuridica.checked;
    if (labelClienteDocumento) labelClienteDocumento.textContent = ehJuridica ? 'CNPJ' : 'CPF';
    // Inscricao Estadual so faz sentido pra pessoa juridica (ver
    // conversa) -- some junto quando volta pra fisica, senao ficaria
    // um campo de IE preenchido junto de um CPF.
    if (clienteIeWrap) clienteIeWrap.hidden = !ehJuridica;
    if (!ehJuridica && clienteIeInput) clienteIeInput.value = '';
    if (!ehJuridica && clienteIeIsentoCheckbox) clienteIeIsentoCheckbox.checked = false;
    if (!ehJuridica && clienteIeNaoContribuinteCheckbox) clienteIeNaoContribuinteCheckbox.checked = false;
    if (erroClienteDocumentoEl) erroClienteDocumentoEl.hidden = true;
  }
  if (tipoPessoaFisica) tipoPessoaFisica.addEventListener('change', atualizarLabelDocumento);
  if (tipoPessoaJuridica) tipoPessoaJuridica.addEventListener('change', atualizarLabelDocumento);

  // "Isento" e "informar o numero da IE" sao mutuamente exclusivos --
  // marcar isento fecha/limpa o campo (ver conversa: "botão de marcar
  // isento, vai fechar o campo de IE"). "Não contribuinte" e´
  // independente: uma empresa pode ter IE e ainda assim ser
  // classificada como não contribuinte de ICMS (ver
  // services/pedidos.py -- os dois sao gravados separados).
  if (clienteIeIsentoCheckbox && clienteIeInput) {
    clienteIeIsentoCheckbox.addEventListener('change', () => {
      clienteIeInput.disabled = clienteIeIsentoCheckbox.checked;
      if (clienteIeIsentoCheckbox.checked) clienteIeInput.value = '';
    });
  }

  if (checkboxEntregaOutraPessoa && camposDestinatarioEl) {
    checkboxEntregaOutraPessoa.addEventListener('change', () => {
      camposDestinatarioEl.hidden = !checkboxEntregaOutraPessoa.checked;
      if (checkboxEntregaOutraPessoa.checked) {
        // abre o campo dedicado de CEP do comprador (ver conversa: "ao
        // apertar na opção de endereço de entrega diferente, abra um
        // campo de CEP na parte de cima no endereço do comprador") --
        // a partir daqui o endereco do comprador vem DESSE campo, nao
        // mais do CEP la em cima (que passa a servir so pro frete
        // estimado antes de saber quem recebe).
        if (enderecoCepProprioWrap) enderecoCepProprioWrap.hidden = false;
        if (enderecoCepProprioInput && !enderecoCepProprioInput.value) {
          enderecoCepProprioInput.value = freteCepInput ? freteCepInput.value : '';
        }
      } else {
        if (enderecoCepProprioWrap) enderecoCepProprioWrap.hidden = true;
        // desmarcou -- volta o frete e o endereco do comprador a
        // refletir o CEP la em cima (podem ter ficado calculados pro
        // CEP de entrega/CEP proprio enquanto a caixa estava marcada)
        const cepPrincipal = (freteCepInput.value || '').replace(/\D/g, '');
        if (cepPrincipal.length === 8) {
          calcularFreteParaCep(cepPrincipal);
          destravarCamposEndereco(INPUTS_ENDERECO_PROPRIO);
          preencherEnderecoPorCep(cepPrincipal, INPUTS_ENDERECO_PROPRIO);
        }
      }
    });
  }

  if (formaPagamentoRadios.length && cadastroClienteEl && whatsappFinalizarWrapEl) {
    formaPagamentoRadios.forEach((radio) => {
      radio.addEventListener('change', () => {
        // boleto usa o MESMO cadastro (nome/documento/endereco) que o
        // pagamento direto no site -- so troca qual botao final aparece.
        cadastroClienteEl.hidden = radio.value !== 'site' && radio.value !== 'boleto';
        whatsappFinalizarWrapEl.hidden = radio.value !== 'whatsapp';
        if (btnPagarAgora) btnPagarAgora.hidden = radio.value !== 'site';
        if (btnGerarBoleto) btnGerarBoleto.hidden = radio.value !== 'boleto';
        if (boletoAviso2DiasEl) boletoAviso2DiasEl.hidden = radio.value !== 'boleto';
        if (radio.checked && (radio.value === 'site' || radio.value === 'boleto')) {
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

  // valida tudo que os dois fluxos de pagamento no site (Pix/cartao via
  // InfinitePay, boleto via Inter) precisam em comum -- devolve
  // {cliente, endereco} ou null (ja mostrou o toast de erro certo).
  function coletarClienteEEndereco() {
    if (!ultimoCalculo) return null;

    if (!ultimoCalculo.atinge_minimo) {
      const faltamParaMinimo = ultimoCalculo.pedido_minimo_reais - ultimoCalculo.subtotal_total;
      mostrarToast(
        `⚠️ Faltam ${formatarPreco(faltamParaMinimo)} em produtos para o pedido mínimo de ` +
        `${formatarPreco(ultimoCalculo.pedido_minimo_reais)} (o frete é à parte).`
      );
      if (avisoMinimoEl) avisoMinimoEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return null;
    }
    if (!freteEscolhido) {
      mostrarToast('⚠️ Calcule o frete e escolha uma opção antes de pagar.');
      if (freteResultadoEl) freteResultadoEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return null;
    }

    const clienteEhJuridica = tipoPessoaJuridica && tipoPessoaJuridica.checked;
    const cliente = {
      nome: (clienteNomeInput.value || '').trim(),
      tipo_pessoa: clienteEhJuridica ? 'juridica' : 'fisica',
      documento: (clienteDocumentoInput.value || '').trim(),
      telefone: (clienteTelefoneInput.value || '').trim(),
      email: (clienteEmailInput.value || '').trim(),
    };
    if (clienteEhJuridica) {
      cliente.ie_isento = !!(clienteIeIsentoCheckbox && clienteIeIsentoCheckbox.checked);
      cliente.ie_nao_contribuinte = !!(clienteIeNaoContribuinteCheckbox && clienteIeNaoContribuinteCheckbox.checked);
      cliente.inscricao_estadual = cliente.ie_isento ? '' : (clienteIeInput ? clienteIeInput.value.trim() : '');
    }
    // com entrega-outra-pessoa marcado, o CEP do comprador vem do
    // campo dedicado que abre dentro do cadastro (endereco-cep-proprio)
    // -- nunca do CEP la em cima, que nesse caso serve so pra estimar
    // frete antes de ter o CEP de entrega de verdade (ver conversa,
    // esse era o motivo do erro "CEP diferente do CEP de entrega").
    const usaEnderecoProprioDedicado = checkboxEntregaOutraPessoa && checkboxEntregaOutraPessoa.checked;
    const cepProprioInput = usaEnderecoProprioDedicado ? enderecoCepProprioInput : freteCepInput;
    const endereco = {
      cep: (cepProprioInput && cepProprioInput.value || '').replace(/\D/g, ''),
      logradouro: (enderecoLogradouroInput.value || '').trim(),
      numero: (enderecoNumeroInput.value || '').trim(),
      complemento: (enderecoComplementoInput.value || '').trim(),
      bairro: (enderecoBairroInput.value || '').trim(),
      cidade: (enderecoCidadeInput.value || '').trim(),
      uf: (enderecoUfInput.value || '').trim(),
    };

    if (!cliente.nome || !cliente.documento || !cliente.telefone || !cliente.email) {
      mostrarToast('⚠️ Preencha seus dados completos antes de pagar.');
      return null;
    }
    if (erroClienteDocumentoEl) erroClienteDocumentoEl.hidden = true;
    if (!documentoValido(cliente.tipo_pessoa, cliente.documento)) {
      const rotulo = cliente.tipo_pessoa === 'juridica' ? 'CNPJ' : 'CPF';
      mostrarToast(`⚠️ ${rotulo} inválido. Confira o número digitado.`);
      if (erroClienteDocumentoEl) {
        erroClienteDocumentoEl.textContent = `${rotulo} inválido.`;
        erroClienteDocumentoEl.hidden = false;
      }
      clienteDocumentoInput.focus();
      return null;
    }
    if (!endereco.cep || !endereco.logradouro || !endereco.numero || !endereco.bairro || !endereco.cidade || !endereco.uf) {
      mostrarToast('⚠️ Preencha seu CEP e endereço completo antes de pagar.');
      return null;
    }

    if (checkboxEntregaOutraPessoa && checkboxEntregaOutraPessoa.checked) {
      endereco.destinatario_nome = (destinatarioNomeInput.value || '').trim();
      endereco.destinatario_tipo_pessoa =
        (destinatarioTipoPessoaJuridica && destinatarioTipoPessoaJuridica.checked) ? 'juridica' : 'fisica';
      endereco.destinatario_documento = (destinatarioDocumentoInput.value || '').trim();
      if (!endereco.destinatario_nome || !endereco.destinatario_documento) {
        mostrarToast('⚠️ Preencha o nome e o documento de quem vai receber.');
        return null;
      }
      if (erroDestinatarioDocumentoEl) erroDestinatarioDocumentoEl.hidden = true;
      if (!documentoValido(endereco.destinatario_tipo_pessoa, endereco.destinatario_documento)) {
        const rotuloDest = endereco.destinatario_tipo_pessoa === 'juridica' ? 'CNPJ' : 'CPF';
        mostrarToast(`⚠️ ${rotuloDest} de quem recebe é inválido. Confira o número digitado.`);
        if (erroDestinatarioDocumentoEl) {
          erroDestinatarioDocumentoEl.textContent = `${rotuloDest} inválido.`;
          erroDestinatarioDocumentoEl.hidden = false;
        }
        destinatarioDocumentoInput.focus();
        return null;
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
        return null;
      }
      if (todosPreenchidos) {
        Object.assign(endereco, enderecoDestCampos);
        endereco.destinatario_complemento = (destinatarioComplementoInput.value || '').trim();
      }
    }

    return { cliente, endereco };
  }

  if (btnPagarAgora) {
    btnPagarAgora.addEventListener('click', async () => {
      const dadosColetados = coletarClienteEEndereco();
      if (!dadosColetados) return;
      const { cliente, endereco } = dadosColetados;

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

  if (btnGerarBoleto) {
    btnGerarBoleto.addEventListener('click', async () => {
      const dadosColetados = coletarClienteEEndereco();
      if (!dadosColetados) return;
      const { cliente, endereco } = dadosColetados;

      btnGerarBoleto.disabled = true;
      btnGerarBoleto.textContent = 'Gerando boleto...';
      try {
        const resposta = await fetch('/api/pedido/criar-boleto', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ itens: ultimosItens, frete: freteEscolhido, cliente, endereco }),
        });
        const dados = await resposta.json();
        if (!resposta.ok || dados.erro) {
          mostrarToast(`⚠️ ${dados.erro || 'Não foi possível gerar o boleto agora.'}`);
          return;
        }
        rastrearEventoGA4('begin_checkout', { currency: 'BRL', value: ultimoCalculo.subtotal_total });
        window.location.href = `/pedido/${dados.token}`;
      } catch (e) {
        mostrarToast('⚠️ Não foi possível gerar o boleto agora.');
      } finally {
        btnGerarBoleto.disabled = false;
        btnGerarBoleto.textContent = '📄 Gerar boleto';
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
    btnWhatsappFinalizar.addEventListener('click', async () => {
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

      // registra o pedido no painel admin (status "whatsapp") antes de
      // abrir a conversa, pra quem vende poder acompanhar e preencher os
      // dados na mao se a venda fechar (ver conversa) -- best-effort: se
      // essa chamada falhar, abre o WhatsApp do mesmo jeito com o codigo
      // local, a conversao nunca fica bloqueada por isso.
      //
      // A aba e´ aberta em branco AGORA (ainda sincrono dentro do gesto
      // de clique) e so navegada pra URL certa depois do fetch abaixo --
      // Safari/iOS bloqueia window.open() chamado depois de um "await".
      const janela = window.open('', '_blank');
      let codigoPedido = null;
      try {
        const resposta = await fetch('/api/pedido/criar-whatsapp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            itens: ultimosItens,
            frete: freteEscolhido || {},
            cep_informado: freteCepInput ? freteCepInput.value.trim() : '',
          }),
        });
        const dados = await resposta.json();
        if (resposta.ok && dados.codigo) codigoPedido = dados.codigo;
      } catch (e) {
        // segue sem o registro no painel -- abrir o WhatsApp e´ o que importa
      }

      const mensagem =
        'Olá! Gostaria de fazer este pedido:\n\n' +
        montarCorpoPedido(ultimosItens, ultimoCalculo, codigoPedido) +
        '\n\nGostaria de finalizar este pedido.';
      rastrearConversao(ultimoCalculo.subtotal_total);
      abrirWhatsApp(mensagem, janela);
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
