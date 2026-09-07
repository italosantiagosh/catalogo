// Modais simples de imagem/conteudo, carregados em base.html (disponiveis
// em toda pagina) -- guia de tamanhos (foto real com regua, aberto de
// /produto/<id> e /personalizada) e tabela de faixas de desconto (aberta
// pelo aviso do topo). Mesmo padrao pros dois: abre com uma funcao global,
// fecha no X, clicando fora ou com Esc.
function _configurarModalSimples(modalId, botaoFecharId) {
  const modal = document.getElementById(modalId);
  const btnFechar = document.getElementById(botaoFecharId);
  if (!modal || !btnFechar) return null;

  function fechar() {
    modal.hidden = true;
  }

  btnFechar.addEventListener('click', fechar);
  modal.addEventListener('click', (evento) => {
    if (evento.target === modal) fechar();
  });
  document.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape' && !modal.hidden) fechar();
  });

  return () => {
    modal.hidden = false;
  };
}

const _abrirGuia = _configurarModalSimples('modal-guia-tamanhos', 'btn-guia-tamanhos-fechar');
if (_abrirGuia) window.abrirGuiaTamanhos = _abrirGuia;

const _abrirTabela = _configurarModalSimples('modal-tabela-desconto', 'btn-tabela-desconto-fechar');
if (_abrirTabela) window.abrirTabelaDesconto = _abrirTabela;
