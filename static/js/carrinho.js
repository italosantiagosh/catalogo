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

function carrinhoObterItens() {
  try {
    const bruto = localStorage.getItem(CARRINHO_CHAVE);
    const itens = bruto ? JSON.parse(bruto) : [];
    return Array.isArray(itens) ? itens : [];
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
  return itens;
}

function carrinhoRemoverItem(chave) {
  const itens = carrinhoObterItens().filter((i) => i.chave !== chave);
  carrinhoSalvarItens(itens);
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
        itens: itens.map((item) => ({ tamanho: item.tamanho, quantidade: item.quantidade })),
      }),
    });
    const dados = await resposta.json();

    const textoEl = document.getElementById('barra-persistente-texto');
    const preenchimentoEl = document.getElementById('barra-persistente-preenchimento');

    if (dados.proxima_faixa) {
      textoEl.textContent =
        `${dados.quantidade_total} / ${dados.proxima_faixa.quantidade} medalhas — ` +
        `faltam ${dados.proxima_faixa.faltam} para o próximo desconto (${formatarPreco(dados.proxima_faixa.preco)}/un)`;
      preenchimentoEl.style.width =
        _percentualBarra(dados.quantidade_total, dados.faixa_atual_inicio, dados.proxima_faixa.quantidade) + '%';
    } else {
      const precoAtual = dados.itens[0] ? dados.itens[0].preco_unitario : 0;
      textoEl.textContent = `🎉 Você já está na melhor faixa de preço (${formatarPreco(precoAtual)}/un)`;
      preenchimentoEl.style.width = '100%';
    }

    container.hidden = false;
  } catch (e) {
    container.hidden = true;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  carrinhoAtualizarContador();
  carrinhoAtualizarBarraPersistente();
});
