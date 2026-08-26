(function () {
  const btn = document.getElementById('btn-ativar-notificacoes');
  if (!btn) return;

  if (!('serviceWorker' in navigator) || !('PushManager' in window) || !window.VAPID_CHAVE_PUBLICA) {
    btn.hidden = true;
    return;
  }

  function base64UrlParaUint8Array(base64Url) {
    const padding = '='.repeat((4 - (base64Url.length % 4)) % 4);
    const base64 = (base64Url + padding).replace(/-/g, '+').replace(/_/g, '/');
    const raw = window.atob(base64);
    return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
  }

  async function atualizarEstadoBotao() {
    try {
      const registro = await navigator.serviceWorker.getRegistration();
      const subscription = registro ? await registro.pushManager.getSubscription() : null;
      btn.textContent = subscription ? '🔔 Notificações ativadas (desativar)' : '🔔 Ativar notificações de venda';
      btn.dataset.ativo = subscription ? '1' : '0';
    } catch (e) {
      // sem service worker registrado ainda -- estado inicial, nada a fazer
    }
  }

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    try {
      const registro = await navigator.serviceWorker.register('/sw.js');

      if (btn.dataset.ativo === '1') {
        const existente = await registro.pushManager.getSubscription();
        if (existente) {
          await fetch('/admin/push/desinscrever', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ endpoint: existente.endpoint }),
          });
          await existente.unsubscribe();
        }
        await atualizarEstadoBotao();
        return;
      }

      const permissao = await Notification.requestPermission();
      if (permissao !== 'granted') {
        alert('Permissão de notificação negada pelo navegador.');
        return;
      }

      const subscription = await registro.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: base64UrlParaUint8Array(window.VAPID_CHAVE_PUBLICA),
      });

      await fetch('/admin/push/inscrever', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscription.toJSON()),
      });
      await atualizarEstadoBotao();
    } catch (e) {
      alert('Não foi possível ativar as notificações agora.');
    } finally {
      btn.disabled = false;
    }
  });

  atualizarEstadoBotao();
})();
