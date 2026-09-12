// Captura de onde a pessoa veio (referrer + utm_*) na PRIMEIRA pagina
// que ela abre nesse navegador -- guarda em localStorage e nunca
// sobrescreve depois (atribuicao "primeiro toque": se ela chegou pelo
// Instagram e depois voltou direto pelo favorito, o pedido continua
// contando como Instagram). Usado em static/js/carrinho_pagina.js na
// hora de criar o pedido (ver conversa: "tem como ver origem do
// comprador?"). Carregado global (base.html) pra capturar em QUALQUER
// pagina de entrada, nao so a home.
(function () {
  const CHAVE = 'catalogo_medalhas_origem_visita';

  if (!localStorage.getItem(CHAVE)) {
    const params = new URLSearchParams(window.location.search);
    const dados = {
      referrer: document.referrer || '',
      utm_source: params.get('utm_source') || '',
      utm_medium: params.get('utm_medium') || '',
      utm_campaign: params.get('utm_campaign') || '',
    };
    try {
      localStorage.setItem(CHAVE, JSON.stringify(dados));
    } catch (e) {
      // localStorage bloqueado (aba anonima/privacidade) -- sem
      // atribuicao de origem pra essa visita, mas o site continua
      // funcionando normal.
    }
  }

  window.obterOrigemVisita = function () {
    try {
      const bruto = localStorage.getItem(CHAVE);
      return bruto ? JSON.parse(bruto) : null;
    } catch (e) {
      return null;
    }
  };
})();
