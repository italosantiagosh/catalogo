/*
 * Modulo de dados do carrinho -- persistido em localStorage, carregado em
 * toda pagina (via base.html) para que o contador do cabecalho funcione em
 * qualquer lugar. Preco e faixa de atacado ainda nao entram aqui (ETAPA 5);
 * por enquanto cada item so guarda quantidade e os dados de identificacao.
 */

const CARRINHO_CHAVE = 'catalogo_medalhas_carrinho';

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
}

function carrinhoQuantidadeTotal() {
  return carrinhoObterItens().reduce((soma, item) => soma + item.quantidade, 0);
}

function carrinhoAtualizarContador() {
  const el = document.getElementById('contador-carrinho');
  if (el) el.textContent = String(carrinhoQuantidadeTotal());
}

document.addEventListener('DOMContentLoaded', carrinhoAtualizarContador);
