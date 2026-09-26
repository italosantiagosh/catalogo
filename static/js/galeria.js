// Galeria da buybox (produto.html): miniaturas trocam a foto grande, e
// escolher outro modelo na grade troca todas as fotos pelas daquele
// modelo (mesmas chaves do data-imagens de .modelo-card). Sem zoom --
// pedido do usuario ("cancela o zoom").
(function () {
  const galeria = document.getElementById('galeria');
  if (!galeria) return;
  const fotoGrande = document.getElementById('galeria-img');
  const miniaturas = [...galeria.querySelectorAll('.galeria-mini')];
  const nomeProduto = document.getElementById('modelos-grid')?.dataset.produtoNome || '';

  const mostrar = (mini) => {
    miniaturas.forEach((m) => m.classList.toggle('ativa', m === mini));
    fotoGrande.src = mini.querySelector('img').src;
    fotoGrande.alt = `${nomeProduto} — ${mini.dataset.rotulo}`;
  };

  miniaturas.forEach((mini) => mini.addEventListener('click', () => mostrar(mini)));

  document.getElementById('modelos-grid')?.addEventListener('click', (evento) => {
    const card = evento.target.closest('.modelo-card');
    if (!card) return;
    let imagens;
    try { imagens = JSON.parse(card.dataset.imagens); } catch (e) { return; }
    miniaturas.forEach((mini) => {
      const chave = mini.dataset.chave;
      if (chave === 'verso') return; // verso inox e´ igual em todos os modelos
      const url = imagens[chave];
      mini.hidden = !url;
      if (url) mini.querySelector('img').src = url;
    });
    const ativa = miniaturas.find((m) => m.classList.contains('ativa') && !m.hidden) || miniaturas[0];
    mostrar(ativa);
  });
})();
