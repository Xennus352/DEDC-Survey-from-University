'use strict';

// Credentials remain in the HttpOnly cookie. Revalidate private views with the
// backend on history restore and tab activation, including after expiry/logout.
(() => {
  if (!document.body.hasAttribute('data-admin-workspace')) return;
  const channel = typeof BroadcastChannel === 'function'
    ? new BroadcastChannel('dedc-admin-session') : null;
  const loginUrl = document.body.dataset.loginUrl || '/portal';
  const sessionEndpoint = document.body.dataset.sessionEndpoint || '/api/admin/session';
  let signingOut = false;
  let checking;
  function leaveWorkspace() {
    document.body.hidden = true;
    window.location.replace(loginUrl);
  }
  function announceLogout() {
    if (channel) channel.postMessage('logout');
    // Fallback signal contains no identity, credentials, or survey data.
    try { localStorage.setItem('dedc-logout', String(Date.now())); } catch (_) { /* Storage may be disabled. */ }
  }
  async function verifySession() {
    if (signingOut) return;
    document.body.hidden = true;
    if (checking) return checking;
    checking = (async () => {
      try {
        const response = await fetch(sessionEndpoint, {
          credentials: 'same-origin', cache: 'no-store',
        });
        if (!response.ok) return leaveWorkspace();
        if (!signingOut && !document.hidden) document.body.hidden = false;
      } catch (_) {
        leaveWorkspace();
      } finally {
        checking = null;
      }
    })();
    return checking;
  }
  if (channel) channel.addEventListener('message', event => {
    if (event.data === 'logout') leaveWorkspace();
  });
  window.addEventListener('storage', event => {
    if (event.key === 'dedc-logout' && event.newValue) leaveWorkspace();
  });
  window.addEventListener('pagehide', () => { document.body.hidden = true; });
  window.addEventListener('pageshow', event => {
    if (signingOut) leaveWorkspace();
    // Fresh responses already passed server authorization; revalidate cached restores.
    else if (event.persisted) verifySession();
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) document.body.hidden = true;
    else verifySession();
  });
  document.querySelectorAll('form[action$="/portal/logout"]').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (signingOut) return;
      signingOut = true;
      const button = form.querySelector('button');
      const error = document.querySelector('[data-session-error]');
      if (error) error.hidden = true;
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      try {
        const response = await fetch(form.action, {
          method: 'POST', credentials: 'same-origin', cache: 'no-store',
          body: new URLSearchParams(new FormData(form)),
        });
        if (!response.ok || !response.redirected || new URL(response.url).pathname !== '/portal') {
          throw new Error('Sign out could not be confirmed. Please retry.');
        }
        announceLogout();
        leaveWorkspace();
      } catch (_) {
        signingOut = false;
        button.disabled = false;
        button.removeAttribute('aria-busy');
        await verifySession();
        if (error && !document.body.hidden) {
          error.textContent = 'Sign out could not be confirmed. Check your connection and try again.';
          error.hidden = false;
          error.focus();
        }
      }
    });
  });
})();
