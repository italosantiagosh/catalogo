(function () {
  // Popup opcional "Quer ajuda pra fazer seu pedido?" -- so na primeira
  // visita (ver conversa), some pra sempre depois de qualquer resposta
  // (nao insiste a cada visita nova). O botao "❓ Como funciona" ao lado
  // continua disponivel pra sempre pra quem quiser essa ajuda depois.
  const CHAVE_VISTO = 'catalogo_medalhas_ajuda_popup_visto';
  if (localStorage.getItem(CHAVE_VISTO)) return;

  const popup = document.getElementById('popup-ajuda-inicial');
  const botaoSim = document.getElementById('popup-ajuda-sim');
  const botaoNao = document.getElementById('popup-ajuda-nao');
  if (!popup || !botaoSim || !botaoNao) return;

  function fechar() {
    popup.hidden = true;
    localStorage.setItem(CHAVE_VISTO, '1');
  }

  setTimeout(() => {
    popup.hidden = false;
  }, 1500);

  botaoSim.addEventListener('click', () => {
    fechar();
    if (typeof abrirAjudaHome === 'function') abrirAjudaHome();
  });
  botaoNao.addEventListener('click', fechar);
})();
