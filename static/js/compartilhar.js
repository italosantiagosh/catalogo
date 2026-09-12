// Botao "Copiar link" reusavel (produto.html por enquanto, ver conversa
// "loja mensageiros") -- delegado no document pra funcionar em qualquer
// pagina que tenha um [data-copiar-link], mesmo carregado global.
document.addEventListener('click', (evento) => {
  const botao = evento.target.closest('[data-copiar-link]');
  if (!botao) return;
  const url = botao.getAttribute('data-copiar-link');
  const textoOriginal = botao.textContent;
  navigator.clipboard
    .writeText(url)
    .then(() => {
      botao.textContent = '✅ Link copiado!';
      setTimeout(() => {
        botao.textContent = textoOriginal;
      }, 2000);
    })
    .catch(() => {
      botao.textContent = '⚠️ Não deu pra copiar';
      setTimeout(() => {
        botao.textContent = textoOriginal;
      }, 2000);
    });
});
