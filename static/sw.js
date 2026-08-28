// Service worker minimo -- so existe pra receber notificacao push (ver
// static/js/push.js e services/push.py). Servido em /sw.js (rota
// dedicada em app.py, nao em /static/) de proposito: o escopo padrao
// de um service worker e´ limitado a partir de onde ele e´ servido, e
// /static/sw.js so teria escopo dentro de /static/.

self.addEventListener('push', (event) => {
  let dados = {};
  try {
    dados = event.data ? event.data.json() : {};
  } catch (e) {
    dados = {};
  }
  const titulo = dados.titulo || 'Nove de Julho';
  const opcoes = {
    body: dados.corpo || '',
    icon: dados.icone || '/static/img/logo-icone.png',
    badge: '/static/img/logo-icone.png',
    data: { url: dados.url || '/' },
  };
  event.waitUntil(self.registration.showNotification(titulo, opcoes));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(clients.openWindow(url));
});
