(function () {
  // busca da home nao filtra nada localmente (a grade completa saiu da
  // home, ver /catalogo) -- so leva pra la com o termo digitado.
  const input = document.getElementById('busca-home');
  if (!input) return;

  input.addEventListener('keydown', (evento) => {
    if (evento.key !== 'Enter') return;
    evento.preventDefault();
    const termo = input.value.trim();
    window.location.href = termo ? `/catalogo?q=${encodeURIComponent(termo)}` : '/catalogo';
  });
})();
