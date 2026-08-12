(function () {
  const input = document.getElementById('input-imagem');
  const nomeDiv = document.getElementById('nome-arquivo');
  const botao = document.getElementById('botao-enviar');
  const form = document.getElementById('form-upload');

  if (input) {
    input.addEventListener('change', () => {
      if (input.files.length === 0) {
        nomeDiv.textContent = '';
        botao.disabled = true;
        botao.textContent = 'Selecione uma imagem primeiro';
        return;
      }
      nomeDiv.textContent = input.files[0].name;
      botao.disabled = false;
      botao.textContent = 'Gerar simulação';
    });
  }

  if (form) {
    form.addEventListener('submit', () => {
      botao.disabled = true;
      botao.textContent = 'Gerando simulação...';
    });
  }

  const qtdMenos = document.getElementById('qtd-menos');
  const qtdMais = document.getElementById('qtd-mais');
  const quantidadeInput = document.getElementById('sel-quantidade');

  function ajustarQuantidade(delta) {
    const atual = parseInt(quantidadeInput.value, 10) || 1;
    quantidadeInput.value = Math.max(1, atual + delta);
  }

  if (qtdMenos) qtdMenos.addEventListener('click', () => ajustarQuantidade(-1));
  if (qtdMais) qtdMais.addEventListener('click', () => ajustarQuantidade(1));
})();
