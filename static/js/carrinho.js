/*
 * Modulo de dados do carrinho -- persistido em localStorage, carregado em
 * toda pagina (via base.html). Alem do contador do cabecalho, tambem
 * mantem a barra de progresso persistente (ETAPA 6): quantidade atual x
 * proxima faixa de desconto, visivel em qualquer pagina exceto o proprio
 * /carrinho (que ja tem o resumo detalhado).
 *
 * Tambem guarda o ID do pedido (secao 16 do briefing) -- gerado na hora
 * (sem backend, sem banco), estavel enquanto o carrinho tiver itens, e
 * renovado assim que o carrinho e limpo.
 */

// Dispara um evento pro GA4 (ver base.html -- gtag so existe se
// GA4_MEASUREMENT_ID estiver configurado) -- usado em todo lugar que
// precisa registrar um passo do funil (busca, add ao carrinho, faixa
// de atacado atingida etc), sem repetir o guard em cada arquivo.
function rastrearEventoGA4(nome, params) {
  if (typeof gtag === 'function') gtag('event', nome, params || {});
}

const CARRINHO_CHAVE = 'catalogo_medalhas_carrinho';
const PEDIDO_ID_CHAVE = 'catalogo_medalhas_pedido_id';
const PEDIDO_ID_CHARSET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // sem O/0, I/1 -- evita confusao ao ler em voz alta

function gerarPedidoId() {
  let id = '';
  for (let i = 0; i < 6; i++) {
    id += PEDIDO_ID_CHARSET[Math.floor(Math.random() * PEDIDO_ID_CHARSET.length)];
  }
  return id;
}

function obterOuCriarPedidoId() {
  let id = localStorage.getItem(PEDIDO_ID_CHAVE);
  if (!id) {
    id = gerarPedidoId();
    localStorage.setItem(PEDIDO_ID_CHAVE, id);
  }
  return id;
}

// Carrinhos salvos antes da adicao de chaveiros/entremeios so tinham
// `tamanho` (12mm/16mm), sempre medalha -- migra na leitura pra nao
// quebrar carrinhos de clientes ja em andamento (localStorage, sem backend).
function _migrarItemLegado(item) {
  if (item.chave_preco) return item;
  return { ...item, formato: item.formato || 'medalha', chave_preco: item.tamanho };
}

function carrinhoObterItens() {
  try {
    const bruto = localStorage.getItem(CARRINHO_CHAVE);
    const itens = bruto ? JSON.parse(bruto) : [];
    return Array.isArray(itens) ? itens.map(_migrarItemLegado) : [];
  } catch (e) {
    return [];
  }
}

function carrinhoSalvarItens(itens) {
  localStorage.setItem(CARRINHO_CHAVE, JSON.stringify(itens));
  carrinhoAtualizarContador();
  carrinhoAtualizarBarraPersistente();
}

function carrinhoAdicionarItem(novoItem) {
  const itens = carrinhoObterItens();
  const existente = itens.find((i) => i.chave === novoItem.chave);
  if (existente) {
    existente.quantidade += novoItem.quantidade;
  } else {
    itens.push(novoItem);
  }
  carrinhoSalvarItens(itens);
  // um so lugar pro evento -- cobre tanto o catalogo (produto.js) quanto
  // a personalizada (personalizada.js), os dois unicos jeitos de item
  // entrar no carrinho.
  rastrearEventoGA4('add_to_cart', {
    item_id: novoItem.produtoId || novoItem.tipo,
    item_name: novoItem.produtoNome || 'Medalha personalizada',
    quantity: novoItem.quantidade,
  });
  return itens;
}

function carrinhoRemoverItem(chave) {
  const todos = carrinhoObterItens();
  const removido = todos.find((i) => i.chave === chave);
  const itens = todos.filter((i) => i.chave !== chave);
  carrinhoSalvarItens(itens);
  if (removido) {
    rastrearEventoGA4('remove_from_cart', {
      item_id: removido.produtoId || removido.tipo,
      item_name: removido.produtoNome || 'Medalha personalizada',
      quantity: removido.quantidade,
    });
  }
  return itens;
}

function carrinhoAtualizarQuantidade(chave, quantidade) {
  const itens = carrinhoObterItens();
  const item = itens.find((i) => i.chave === chave);
  if (item) {
    item.quantidade = Math.max(1, quantidade);
    carrinhoSalvarItens(itens);
  }
  return itens;
}

// Tamanho (12/16mm medalha 1 lado, 14/18mm medalha 2 lados) e´ o MESMO
// preco/imagem nas duas opcoes (ver conversa: "clicar na variação e
// poder mudar") -- da pra editar direto no carrinho, sem voltar no
// produto/personalizada pra recriar o item do zero.
function carrinhoAtualizarTamanho(chave, novoTamanho) {
  const itens = carrinhoObterItens();
  const item = itens.find((i) => i.chave === chave);
  if (item) {
    item.tamanho = novoTamanho;
    // medalha 1 lado usa o proprio tamanho como chave_preco (12mm/16mm,
    // ver static/js/produto.js e personalizada.js); medalha_2lados tem
    // chave_preco fixo "medalha_2lados" -- tamanho ali e´ so descritivo.
    if (item.formato !== 'medalha_2lados') {
      item.chave_preco = novoTamanho;
    }
    carrinhoSalvarItens(itens);
  }
  return itens;
}

// Cor do entremeio (1 lado, prata/ouro velho) e´ o MESMO preco (ver
// services/pricing.py -- cor nao entra na chave_preco desse formato) e
// so muda a imagem "estatica" do modelo (nao depende de foto do
// cliente) -- da pra editar direto no carrinho, igual tamanho acima,
// usando as 2 URLs guardadas no item (imagensCor, preenchido em
// static/js/produto.js na hora de adicionar). Chaveiro/medalha nao tem
// cor; medalha_2lados/entremeio_2lados sao gerados com a foto do
// cliente (personalizada) -- trocar cor exigiria recompor a imagem no
// servidor, fora de escopo aqui. cruz_terco tambem fica de fora: cor
// MUDA o preco (dourado custa mais que prata/ouro velho), entao nao e´
// uma troca "segura" feita so no navegador.
function carrinhoAtualizarCor(chave, novaCor) {
  const itens = carrinhoObterItens();
  const item = itens.find((i) => i.chave === chave);
  if (item && item.imagensCor && item.imagensCor[novaCor]) {
    item.cor = novaCor;
    item.imagem = item.imagensCor[novaCor];
    carrinhoSalvarItens(itens);
  }
  return itens;
}

// Cor da Cruz para Terco MUDA o preco de verdade (dourado custa mais
// que prata/ouro velho, ver data/precos.json) -- diferente da troca
// "segura" de cor do entremeio acima, aqui tambem precisa trocar
// chave_preco (cruz_terco_prata/ouro_velho/dourado) pra recalcular o
// preco certo (calcular_carrinho ja faz isso sozinho a partir do
// chave_preco novo, ver services/pricing.py). Imagem por cor e´ sempre
// a mesma peca fisica com nome de arquivo previsivel (ver
// app.py:_cores_cruz_terco), entao monta a URL aqui direto, sem
// precisar guardar as 3 no item.
function carrinhoAtualizarCorCruz(chave, novaCor) {
  const itens = carrinhoObterItens();
  const item = itens.find((i) => i.chave === chave);
  if (item) {
    item.cor = novaCor;
    item.chave_preco = `cruz_terco_${novaCor}`;
    item.imagem = `/static/img/produtos/cruz_terco_${novaCor}_frente.jpg`;
    carrinhoSalvarItens(itens);
  }
  return itens;
}

function carrinhoLimpar() {
  carrinhoSalvarItens([]);
  // proximo pedido comeca com um ID novo, nao reaproveita o de um pedido
  // ja finalizado/abandonado.
  localStorage.removeItem(PEDIDO_ID_CHAVE);
}

function carrinhoQuantidadeTotal() {
  return carrinhoObterItens().reduce((soma, item) => soma + item.quantidade, 0);
}

function carrinhoAtualizarContador() {
  const el = document.getElementById('contador-carrinho');
  if (el) el.textContent = String(carrinhoQuantidadeTotal());
}

function formatarPreco(valor) {
  return 'R$ ' + valor.toFixed(2).replace('.', ',');
}

// Logo por transportadora (ver conversa: "logo oficial miniatura de cada
// transportadora antes do nome na simulação do frete") -- espelha
// services/frete.py:LOGO_POR_TRANSPORTADORA/logo_transportadora, mesmo
// criterio de match por trecho do nome ja normalizado. Cobre quem
// aparece na cotacao hoje (Correios, Azul Cargo Express, LATAM Cargo,
// J&T Express, Loggi, Jadlog, Total Express).
const LOGO_POR_TRANSPORTADORA = {
  correios: 'correios.svg',
  azul: 'azul-cargo.png',
  latam: 'latam-cargo.svg',
  jt: 'jt-express.svg',
  loggi: 'loggi.png',
  jadlog: 'jadlog.png',
  total: 'total-express.png',
};

function logoTransportadoraHtml(nomeTransportadora) {
  const nomeNormalizado = (nomeTransportadora || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const chave = Object.keys(LOGO_POR_TRANSPORTADORA).find((c) => nomeNormalizado.includes(c));
  if (!chave) return '';
  // alt leva o nome (a logo ja diz visualmente quem e, mas o nome
  // continua "no ar" pra leitor de tela/acessibilidade -- ver conversa:
  // tirar o nome repetido do texto visivel, sem perder ele de vez).
  return `<img class="frete-opcao-logo" src="/static/img/transportadoras/${LOGO_POR_TRANSPORTADORA[chave]}" alt="${nomeTransportadora || ''}">`;
}

// Nome da transportadora + modalidade (ex: "SEDEX"), sem repetir o nome
// em texto quando ja tem logo -- a logo ja "fala" o nome (ver conversa:
// "a logo ja e o nome, ficava repetido"). Sem logo cadastrada, mostra o
// nome por extenso mesmo (unico jeito de identificar a transportadora
// nesse caso).
function nomeTransportadoraComLogoHtml(nomeTransportadora, servico) {
  const logo = logoTransportadoraHtml(nomeTransportadora);
  const nomeVisivel = logo ? '' : `${nomeTransportadora} — `;
  return `${logo}${nomeVisivel}${servico}`;
}

function _percentualBarra(atual, inicioFaixa, alvo) {
  if (alvo == null) return 100;
  const total = alvo - inicioFaixa;
  if (total <= 0) return 100;
  return Math.min(100, Math.max(0, ((atual - inicioFaixa) / total) * 100));
}

// Espelha services/pricing.py: GRUPO_DE_CHAVE / GRUPOS -- cada chave_preco
// pertence a um grupo de atacado, e chaveiro NAO se mistura com
// medalha/entremeio pra faixa de desconto. cruz_terco_* entra aqui so
// pra esse filtro nao quebrar (ver carrinhoAtualizarBarraPersistente
// abaixo) -- o GRUPO em si e´ pulado na hora de montar a barra, ja que
// tem preco fixo/sem faixa nenhuma (ver GRUPO_DE_CHAVE de verdade em
// services/pricing.py).
const GRUPO_DE_CHAVE = {
  '12mm': 'padrao',
  '16mm': 'padrao',
  entremeio: 'padrao',
  chaveiro: 'chaveiro',
  chaveiro_2lados: 'chaveiro',
  medalha_2lados: 'duas_faces',
  entremeio_2lados: 'duas_faces',
  cruz_terco_prata: 'cruz_terco',
  cruz_terco_ouro_velho: 'cruz_terco',
  cruz_terco_dourado: 'cruz_terco',
};

const GRUPO_LABEL = {
  padrao: 'medalhas/entremeios',
  chaveiro: 'chaveiros',
  duas_faces: 'medalhas/entremeios de 2 lados',
};

function _blocoBarraGrupo(nomeGrupo, grupo, itensDoGrupo) {
  const label = GRUPO_LABEL[nomeGrupo] || nomeGrupo;
  let texto;
  let percentual;
  if (grupo.proxima_faixa) {
    // so a quantidade que falta, sem o "X / Y" antes -- ver conversa:
    // esse numero total (X) confundia mais do que ajudava.
    texto = `faltam ${grupo.proxima_faixa.faltam} ${label} para o próximo desconto (${formatarPreco(grupo.proxima_faixa.preco)}/un)`;
    percentual = _percentualBarra(grupo.quantidade_total, grupo.faixa_atual_inicio, grupo.proxima_faixa.quantidade);
  } else {
    const precoAtual = itensDoGrupo[0] ? itensDoGrupo[0].preco_unitario : 0;
    texto = `🎉 Você já está na melhor faixa de ${label} (${formatarPreco(precoAtual)}/un)`;
    percentual = 100;
  }
  return (
    '<div class="barra-persistente-grupo">' +
    `<p class="barra-persistente-texto">${texto}</p>` +
    '<div class="barra-progresso"><div class="barra-progresso-preenchimento" style="width:' +
    percentual +
    '%"></div></div>' +
    '</div>'
  );
}

async function carrinhoAtualizarBarraPersistente() {
  const container = document.getElementById('barra-persistente');
  if (!container) return;

  // a propria pagina do carrinho ja mostra o resumo detalhado -- evita
  // duplicar a chamada a API e a mensagem.
  if (document.getElementById('resumo-carrinho')) {
    container.hidden = true;
    return;
  }

  const itens = carrinhoObterItens();
  if (itens.length === 0) {
    container.hidden = true;
    return;
  }

  try {
    const resposta = await fetch('/api/carrinho/calcular', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        itens: itens.map((item) => ({ chave_preco: item.chave_preco, quantidade: item.quantidade })),
      }),
    });
    const dados = await resposta.json();

    let html = '';
    for (const nomeGrupo of Object.keys(dados.grupos)) {
      // cruz_terco tem preco fixo, sem faixa de atacado nenhuma (ver
      // GRUPO_DE_CHAVE em services/pricing.py) -- mostrar uma barra de
      // "melhor faixa" pra ela sugeriria um desconto que nao existe
      // (bug real: aparecia "melhor faixa de cruz_terco R$0,00/un",
      // ver conversa/print).
      if (nomeGrupo === 'cruz_terco') continue;
      const grupo = dados.grupos[nomeGrupo];
      if (grupo.quantidade_total === 0) continue;
      const itensDoGrupo = dados.itens.filter((i) => GRUPO_DE_CHAVE[i.chave_preco] === nomeGrupo);
      html += _blocoBarraGrupo(nomeGrupo, grupo, itensDoGrupo);
    }
    container.innerHTML = html;
    container.hidden = html === '';
  } catch (e) {
    container.hidden = true;
  }
}

// Chamado direto aqui (sem esperar DOMContentLoaded) de proposito: esse
// script e´ um <script src> comum (sem defer/async) colocado DEPOIS do
// cabecalho no HTML (ver base.html), entao o span do contador e a
// barra persistente ja existem no DOM nesse ponto -- rodar aqui atualiza
// o numero assim que esse script executa, em vez de esperar a pagina
// INTEIRA terminar de parsear (imagens, resto do body, scripts de bloco
// de cada pagina). Ver conversa: sem isso, todo carregamento de pagina
// mostrava rapidamente o "0" fixo que ja vem escrito no HTML antes do
// numero de verdade aparecer -- e´ o motivo do "Carrinho 10 -> Carrinho 0
// -> Carrinho 10" visto na auditoria externa, nao um bug de dominio
// duplicado como se suspeitava antes.
carrinhoAtualizarContador();
carrinhoAtualizarBarraPersistente();
