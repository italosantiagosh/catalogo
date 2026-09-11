// Trava zoom por pinça/duplo toque no mobile (ver conversa: o
// `maximum-scale=1, user-scalable=no` do viewport, sozinho, nao basta --
// iOS Safari e navegadores recentes ignoram isso de proposito por
// acessibilidade). Nao afeta o editor de recorte da /personalizada: o
// canvas de la usa Pointer Events + `touch-action: none` (ver
// static/js/personalizada.js) pra pinça-zoom PROPRIA da ferramenta,
// que ja e´ resolvida antes desses listeners rodarem (pointermove
// dispara antes do touchmove equivalente) -- so bloqueia o gesto
// NATIVO do navegador de dar zoom na pagina inteira.
document.addEventListener('touchmove', (evento) => {
  if (evento.touches.length > 1) evento.preventDefault();
}, { passive: false });

// Gesto de pinca do Safari (fora do padrao Touch Events).
document.addEventListener('gesturestart', (evento) => evento.preventDefault());

// Duplo toque rapido tambem da zoom nativo -- bloqueia so quando os 2
// toques sao bem proximos no tempo (duplo toque de verdade), sem
// atrapalhar 2 toques normais em sequencia (ex: 2 cliques em botoes
// diferentes).
let ultimoToqueEm = 0;
document.addEventListener('touchend', (evento) => {
  const agora = Date.now();
  if (agora - ultimoToqueEm <= 300) evento.preventDefault();
  ultimoToqueEm = agora;
}, { passive: false });
