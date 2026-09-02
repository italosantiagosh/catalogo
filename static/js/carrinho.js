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

function _percentualBarra(atual, inicioFaixa, alvo) {
  if (alvo == null) return 100;
  const total = alvo - inicioFaixa;
  if (total <= 0) return 100;
  return Math.min(100, Math.max(0, ((atual - inicioFaixa) / total) * 100));
}

// Espelha services/pricing.py: GRUPO_DE_CHAVE / GRUPOS -- cada chave_preco
// pertence a um grupo de atacado, e chaveiro NAO se mistura com
// medalha/entremeio pra faixa de desconto.
const GRUPO_DE_CHAVE = {
  '12mm': 'padrao',
  '16mm': 'padrao',
  entremeio: 'padrao',
  chaveiro: 'chaveiro',
  medalha_2lados: 'duas_faces',
  entremeio_2lados: 'duas_faces',
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
    texto =
      `${grupo.quantidade_total} / ${grupo.proxima_faixa.quantidade} ${label} — ` +
      `faltam ${grupo.proxima_faixa.faltam} para o próximo desconto (${formatarPreco(grupo.proxima_faixa.preco)}/un)`;
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

document.addEventListener('DOMContentLoaded', () => {
  carrinhoAtualizarContador();
  carrinhoAtualizarBarraPersistente();
});
