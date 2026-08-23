(function () {
  const btn = document.getElementById('btn-video-flutuante');
  const fechar = document.getElementById('btn-video-fechar');
  const modal = document.getElementById('video-modal');
  const modalFechar = document.getElementById('btn-video-modal-fechar');
  const player = document.getElementById('video-modal-player');
  if (!btn || !modal || !player) return;

  function abrirModal() {
    player.src = window.VIDEO_APRESENTACAO_URL;
    modal.hidden = false;
    player.muted = false;
    player.play().catch(() => {});
  }

  function fecharModal() {
    player.pause();
    player.removeAttribute('src');
    player.load();
    modal.hidden = true;
  }

  btn.addEventListener('click', abrirModal);
  modalFechar.addEventListener('click', fecharModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) fecharModal();
  });

  // fecha a bolinha por 2 minutos (nao permanente -- ainda e uma
  // oportunidade de conversao, so nao insiste na hora)
  fechar.addEventListener('click', (e) => {
    e.stopPropagation();
    btn.hidden = true;
    fechar.hidden = true;
    setTimeout(() => {
      btn.hidden = false;
      fechar.hidden = false;
    }, 120000);
  });
})();
