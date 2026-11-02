'use strict';
window.MOST = window.MOST || {};

window.MOST.initLoginDialog = function () {
  const dialog = document.getElementById('login-dialog');
  const form = document.getElementById('login-form');
  if (!dialog || !form) return;
  const status = form.querySelector('[role="status"]');
  let opener;

  document.querySelectorAll('[data-login-open]').forEach(function (button) {
    button.addEventListener('click', function () {
      opener = button;
      status.hidden = true;
      dialog.showModal();
      document.dispatchEvent(new Event('most:dialogchange'));
    });
  });
  dialog.querySelector('[data-login-close]').addEventListener('click', function () { dialog.close(); });
  dialog.addEventListener('click', function (event) {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right ||
        event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
  dialog.addEventListener('close', function () {
    form.reset();
    status.hidden = true;
    if (opener) opener.focus();
    document.dispatchEvent(new Event('most:dialogchange'));
  });
  // Native form navigation opens the real respondent sign-in flow.
};
