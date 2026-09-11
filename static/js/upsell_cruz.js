// Upsell "Cruz para Terço" (pedido em 2026-09-11): quando o cliente
// adiciona um entremeio prata ou ouro velho (produto.js/personalizada.js
// chamam window.ofertarUpsellCruz(cor) logo depois do add-to-cart), oferece
// completar o terço com a cruz da mesma cor. So existem cores
// prata/ouro_velho aqui -- o entremeio classico (formato "entremeio") nao
// tem opcao dourada no site, entao a cruz dourada fica de fora desse
// popup (so vendida direto na pagina /cruz-para-terco).
(function () {
  const modal = document.getElementById('modal-upsell-cruz');
  const imagemEl = document.getElementById('upsell-cruz-imagem');
  const corNomeEl = document.getElementById('upsell-cruz-cor-nome');
  const precoEl = document.getElementById('upsell-cruz-preco');
  const btnAdicionar = document.getElementById('upsell-cruz-adicionar');
  const btnNao = document.getElementById('upsell-cruz-nao');
  const btnFechar = document.getElementById('btn-upsell-cruz-fechar');
  if (!modal || !imagemEl || !corNomeEl || !precoEl || !btnAdicionar || !btnNao || !btnFechar) return;

  const DADOS_COR = {
    prata: { nome: 'prata', preco: 2.5, imagem: '/static/img/produtos/cruz_terco_prata_frente.jpg' },
    ouro_velho: { nome: 'ouro velho', preco: 2.5, imagem: '/static/img/produtos/cruz_terco_ouro_velho_frente.jpg' },
  };

  let corAtual = null;

  function fechar() {
    modal.hidden = true;
    corAtual = null;
  }

  btnNao.addEventListener('click', fechar);
  btnFechar.addEventListener('click', fechar);
  modal.addEventListener('click', (evento) => {
    if (evento.target === modal) fechar();
  });

  btnAdicionar.addEventListener('click', () => {
    if (!corAtual || typeof carrinhoAdicionarItem !== 'function') return;
    const dados = DADOS_COR[corAtual];
    carrinhoAdicionarItem({
      chave: `cruz-terco-${corAtual}`,
      tipo: 'catalogo',
      produtoId: 'cruz-para-terco',
      produtoNome: 'Cruz para Terço',
      modeloId: '',
      modeloNome: '',
      imagem: dados.imagem,
      formato: 'cruz_terco',
      chave_preco: `cruz_terco_${corAtual}`,
      tamanho: '',
      cor: corAtual,
      quantidade: 1,
    });
    if (typeof carrinhoAtualizarContador === 'function') carrinhoAtualizarContador();
    if (typeof carrinhoAtualizarBarraPersistente === 'function') carrinhoAtualizarBarraPersistente();
    rastrearEventoGA4('select_promotion', { promotion_name: 'upsell_cruz_terco', item_id: `cruz_terco_${corAtual}` });
    fechar();
  });

  window.ofertarUpsellCruz = function (cor) {
    const dados = DADOS_COR[cor];
    if (!dados || typeof carrinhoObterItens !== 'function') return;
    // ja tem essa cruz no carrinho -- nao insiste de novo.
    const jaTem = carrinhoObterItens().some((item) => item.chave_preco === `cruz_terco_${cor}`);
    if (jaTem) return;

    corAtual = cor;
    imagemEl.src = dados.imagem;
    corNomeEl.textContent = dados.nome;
    precoEl.textContent = `R$ ${dados.preco.toFixed(2).replace('.', ',')}`;
    modal.hidden = false;
  };
})();
