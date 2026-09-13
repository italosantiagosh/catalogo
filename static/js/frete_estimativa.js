// Estimativa de prazo por localizacao (IP) na pagina de produto -- ver
// conversa "loja mensageiros" e app.py:api_estimativa_frete_por_localizacao.
// So uma estimativa (geolocalizacao por IP nao acerta o CEP exato): o
// calculo de verdade continua no carrinho, por CEP digitado. Falha
// silenciosa -- se a rota devolver 204 (sem dados) ou der erro de rede,
// o paragrafo so continua escondido, nunca aparece mensagem de erro.
//
// Cache no navegador (localStorage) -- ver conversa 2026-09-13: o
// ipwho.is (servico gratis usado no servidor pra geolocalizar o IP)
// estourou o limite diario dele (429 "Rate limit exceeded") porque essa
// rota era chamada em TODA visita a uma pagina de produto, sem cache
// nenhum do lado do navegador -- a mesma pessoa vendo 5 produtos numa
// sessao gerava 5 chamadas pro servidor (que ja tem cache por IP, mas
// isso nao ajuda dentro da MESMA janela de cache: e´ 1 chamada real ao
// ipwho.is por IP novo de qualquer forma). Guardando o resultado aqui,
// a mesma pessoa passa a gerar 1 chamada por sessao de navegacao (nao 1
// por pagina), cortando a maior parte do volume que estava estourando o
// limite gratis.
(function () {
  const el = document.getElementById('aviso-frete-estimativa');
  if (!el) return;

  const CHAVE_CACHE = 'freteEstimativaLocalizacao';
  // Mesmo criterio de TTL do cache por IP no servidor (ver app.py:
  // _TTL_CACHE_LOCALIZACAO_SEGUNDOS / _TTL_CACHE_LOCALIZACAO_FALHA_
  // SEGUNDOS) -- sucesso fica valido bem mais tempo que falha, pra uma
  // falha pontual nao prender a pessoa sem ver a barra a sessao toda.
  const TTL_SUCESSO_MS = 6 * 60 * 60 * 1000;
  const TTL_FALHA_MS = 3 * 60 * 1000;

  // com logo, o nome so fica no alt (a logo ja "fala" a transportadora
  // visualmente -- ver conversa: repetir o nome do lado ficava
  // redundante); sem logo cadastrada, mostra o nome por extenso mesmo,
  // unico jeito de identificar a transportadora nesse caso.
  function nomeComLogo(opcao) {
    const logo = opcao.logo ? `<img class="frete-opcao-logo" src="${opcao.logo}" alt="${opcao.transportadora}">` : '';
    const nomeVisivel = logo ? '' : `${opcao.transportadora} `;
    return `${logo}${nomeVisivel}${opcao.servico || ''}`;
  }

  function mostrar(dados) {
    el.innerHTML =
      `📍 <strong>${dados.cidade}, ${dados.estado}</strong>: receba com ${nomeComLogo(dados.economico)} ` +
      `até <strong>${dados.economico.data}</strong> no econômico, ou com ${nomeComLogo(dados.expresso)} ` +
      `até <strong>${dados.expresso.data}</strong> no expresso.`;
    el.hidden = false;
  }

  // localStorage pode estar bloqueado (modo privado, cookies
  // desativados) ou o valor guardado pode estar corrompido -- qualquer
  // problema aqui so significa "sem cache", nunca quebra a pagina.
  function lerCache() {
    try {
      const registro = JSON.parse(localStorage.getItem(CHAVE_CACHE));
      if (!registro || typeof registro.quando !== 'number') return null;
      const ttl = registro.dados ? TTL_SUCESSO_MS : TTL_FALHA_MS;
      if (Date.now() - registro.quando > ttl) return null;
      return registro;
    } catch (e) {
      return null;
    }
  }

  function salvarCache(dados) {
    try {
      localStorage.setItem(CHAVE_CACHE, JSON.stringify({ quando: Date.now(), dados }));
    } catch (e) {
      // sem cache nesse caso -- proxima pagina so volta a chamar o servidor.
    }
  }

  const emCache = lerCache();
  if (emCache) {
    if (emCache.dados) mostrar(emCache.dados);
    return; // dentro do TTL (com ou sem sucesso) -- nao chama o servidor de novo
  }

  fetch('/api/frete/estimativa-por-localizacao')
    .then((resposta) => (resposta.status === 200 ? resposta.json() : null))
    .then((dados) => {
      salvarCache(dados);
      if (dados) mostrar(dados);
    })
    .catch(() => {});
})();
