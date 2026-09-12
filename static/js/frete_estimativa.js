// Estimativa de prazo por localizacao (IP) na pagina de produto -- ver
// conversa "loja mensageiros" e app.py:api_estimativa_frete_por_localizacao.
// So uma estimativa (geolocalizacao por IP nao acerta o CEP exato): o
// calculo de verdade continua no carrinho, por CEP digitado. Falha
// silenciosa -- se a rota devolver 204 (sem dados) ou der erro de rede,
// o paragrafo so continua escondido, nunca aparece mensagem de erro.
(function () {
  const el = document.getElementById('aviso-frete-estimativa');
  if (!el) return;

  // com logo, o nome so fica no alt (a logo ja "fala" a transportadora
  // visualmente -- ver conversa: repetir o nome do lado ficava
  // redundante); sem logo cadastrada, mostra o nome por extenso mesmo,
  // unico jeito de identificar a transportadora nesse caso.
  function nomeComLogo(opcao) {
    const logo = opcao.logo ? `<img class="frete-opcao-logo" src="${opcao.logo}" alt="${opcao.transportadora}">` : '';
    const nomeVisivel = logo ? '' : `${opcao.transportadora} `;
    return `${logo}${nomeVisivel}${opcao.servico || ''}`;
  }

  fetch('/api/frete/estimativa-por-localizacao')
    .then((resposta) => (resposta.status === 200 ? resposta.json() : null))
    .then((dados) => {
      if (!dados) return;
      el.innerHTML =
        `📍 <strong>${dados.cidade}, ${dados.estado}</strong>: receba com ${nomeComLogo(dados.economico)} ` +
        `até <strong>${dados.economico.data}</strong> no econômico, ou com ${nomeComLogo(dados.expresso)} ` +
        `até <strong>${dados.expresso.data}</strong> no expresso.`;
      el.hidden = false;
    })
    .catch(() => {});
})();
