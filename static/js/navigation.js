'use strict';
window.MOST = window.MOST || {};

window.MOST.initNavigation = function () {
  const toggle = document.querySelector('[data-menu-toggle]');
  const menu = document.getElementById('mobile-nav');
  if (!toggle || !menu) return;

  function closeMenu() {
    menu.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
  }
  toggle.addEventListener('click', function () {
    menu.hidden = !menu.hidden;
    toggle.setAttribute('aria-expanded', String(!menu.hidden));
  });
  menu.addEventListener('click', function (event) {
    if (event.target.closest('a')) closeMenu();
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && !menu.hidden) {
      closeMenu();
      toggle.focus();
    }
  });
  window.matchMedia('(min-width: 48rem)').addEventListener('change', closeMenu);
};
