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
  const btnLimpar = document.getElementById('btn-limpar');
  const freteCepInput = document.getElementById('frete-cep');
  const btnCalcularFrete = document.getElementById('btn-calcular-frete');
  const freteResultadoEl = document.getElementById('frete-resultado');
  const btnGerarPix = document.getElementById('btn-gerar-pix');
  const pixResultadoEl = document.getElementById('pix-resultado');
  const pixQrEl = document.getElementById('pix-qr');
  const pixCopiaColaEl = document.getElementById('pix-copia-cola');
  const btnCopiarPix = document.getElementById('btn-copiar-pix');
  const pixCopiadoEl = document.getElementById('pix-copiado');
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
    if (!freteEscolhido) return [];
    return ['Frete:', freteEscolhido.texto, ''];
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
      } else if (dados.frete_gratis_atingido && !freteAnteriorAtingido) {
        mostrarToast('🎉 Frete grátis desbloqueado!');
      }
    }
    faixasAnteriores = Object.fromEntries(
      Object.keys(dados.grupos).map((g) => [g, dados.grupos[g].faixa_label])
    );
    freteAnteriorAtingido = dados.frete_gratis_atingido;
    primeiraRenderizacao = false;

    if (!dados.atinge_minimo) {
      avisoMinimoEl.hidden = false;
      avisoMinimoEl.textContent =
        `Pedido mínimo de ${formatarPreco(dados.pedido_minimo_reais)} -- adicione mais itens para finalizar.`;
    } else {
      avisoMinimoEl.hidden = true;
    }

    // cart mudou -- qualquer frete calculado antes nao vale mais (peso/
    // faixa de frete gratis podem ter mudado), pede pra recalcular.
    freteEscolhido = null;
    if (freteResultadoEl) freteResultadoEl.innerHTML = '';

    // idem pro Pix -- o valor mudou, o QR/copia-e-cola gerado antes
    // nao serve mais pro novo total.
    if (pixResultadoEl) pixResultadoEl.hidden = true;

    ultimosItens = itens;
    ultimoCalculo = dados;
    pedidoIdTexto.textContent = `Pedido #${obterOuCriarPedidoId()}`;
  }

  // ---- calculadora de frete (Frenet) ----

  function mascararCep(valor) {
    const digitos = valor.replace(/\D/g, '').slice(0, 8);
    return digitos.length > 5 ? `${digitos.slice(0, 5)}-${digitos.slice(5)}` : digitos;
  }

  if (freteCepInput) {
    freteCepInput.addEventListener('input', () => {
      freteCepInput.value = mascararCep(freteCepInput.value);
    });
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
        const linha = document.createElement('div');
        linha.className = 'frete-opcao';
        const prazo = opcao.prazo_dias ? `${opcao.prazo_dias} dia(s) úteis` : '';
        const rotulo = opcao.gratis
          ? '<span class="frete-opcao-gratis">Grátis</span>'
          : `<span class="frete-opcao-por">Por ${formatarPreco(opcao.preco_final)}</span>`;
        linha.innerHTML = `
          <div>
            <div class="frete-opcao-nome">${opcao.transportadora} — ${opcao.servico}</div>
            <div class="frete-opcao-prazo">${prazo}</div>
          </div>
          <div class="frete-opcao-preco">
            <span class="frete-opcao-preco-original">${formatarPreco(opcao.preco_original)}</span>
            ${rotulo}
          </div>
        `;
        freteResultadoEl.appendChild(linha);
        if (i === 0) {
          freteEscolhido = {
            texto: `${opcao.transportadora} ${opcao.servico} — Grátis`,
            preco: 0,
          };
        }
      });
      return;
    }

    if (!dados.opcoes || dados.opcoes.length === 0) {
      freteResultadoEl.innerHTML = '<p class="frete-erro">Nenhuma opção de frete encontrada para esse CEP.</p>';
      return;
    }

    freteResultadoEl.innerHTML = '';
    dados.opcoes.forEach((opcao, i) => {
      const linha = document.createElement('div');
      linha.className = 'frete-opcao';
      const prazo = opcao.prazo_dias ? `${opcao.prazo_dias} dia(s) úteis` : '';
      linha.innerHTML = `
        <div>
          <div class="frete-opcao-nome">${opcao.transportadora} — ${opcao.servico}</div>
          <div class="frete-opcao-prazo">${prazo}</div>
        </div>
        <div class="frete-opcao-preco">${formatarPreco(opcao.preco)}</div>
      `;
      freteResultadoEl.appendChild(linha);
      if (i === 0) {
        freteEscolhido = {
          texto: `${opcao.transportadora} ${opcao.servico} — ${formatarPreco(opcao.preco)}`,
          preco: opcao.preco,
        };
      }
    });
  }

  if (btnCalcularFrete) {
    btnCalcularFrete.addEventListener('click', async () => {
      const cep = (freteCepInput.value || '').replace(/\D/g, '');
      if (cep.length !== 8) {
        freteResultadoEl.innerHTML = '<p class="frete-erro">Digite um CEP válido.</p>';
        return;
      }
      const itens = carrinhoObterItens();
      if (itens.length === 0) return;

      btnCalcularFrete.disabled = true;
      btnCalcularFrete.textContent = 'Calculando...';
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
        freteResultadoEl.innerHTML = '<p class="frete-erro">Não foi possível calcular o frete agora.</p>';
      } finally {
        btnCalcularFrete.disabled = false;
        btnCalcularFrete.textContent = 'Calcular';
      }
    });
  }

  if (btnGerarPix) {
    btnGerarPix.addEventListener('click', async () => {
      if (!ultimoCalculo) return;
      const valorFrete = freteEscolhido && freteEscolhido.preco ? freteEscolhido.preco : 0;
      const valor = ultimoCalculo.subtotal_total + valorFrete;

      btnGerarPix.disabled = true;
      btnGerarPix.textContent = 'Gerando...';
      try {
        const resposta = await fetch('/api/pix/gerar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ valor, txid: obterOuCriarPedidoId() }),
        });
        const dados = await resposta.json();
        if (dados.erro) {
          mostrarToast(dados.erro);
          return;
        }
        pixQrEl.src = dados.qr_data_uri;
        pixCopiaColaEl.value = dados.copia_cola;
        pixResultadoEl.hidden = false;
        pixCopiadoEl.hidden = true;
      } catch (e) {
        mostrarToast('Não foi possível gerar o Pix agora.');
      } finally {
        btnGerarPix.disabled = false;
        btnGerarPix.textContent = '💠 Gerar QR Code Pix';
      }
    });
  }

  if (btnCopiarPix) {
    btnCopiarPix.addEventListener('click', async () => {
      const texto = pixCopiaColaEl.value;
      try {
        await navigator.clipboard.writeText(texto);
      } catch (e) {
        pixCopiaColaEl.select();
        document.execCommand('copy');
      }
      pixCopiadoEl.hidden = false;
      clearTimeout(btnCopiarPix._timer);
      btnCopiarPix._timer = setTimeout(() => {
        pixCopiadoEl.hidden = true;
      }, 2000);
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

  if (btnWhatsappFinalizar) {
    btnWhatsappFinalizar.addEventListener('click', () => {
      if (!ultimoCalculo) return;
      const mensagem =
        'Olá! Gostaria de fazer este pedido:\n\n' +
        montarCorpoPedido(ultimosItens, ultimoCalculo) +
        '\n\nGostaria de finalizar este pedido.';
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
      abrirWhatsApp(mensagem);
    });
  }

  render();
})();
