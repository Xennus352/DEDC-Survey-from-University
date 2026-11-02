'use strict';
window.MOST = window.MOST || {};

window.MOST.initCarousel = function () {
  const carousel = document.querySelector('[data-carousel]');
  if (!carousel) return;
  const slides = Array.from(carousel.querySelectorAll('[data-slide]'));
  const dots = Array.from(carousel.querySelectorAll('[data-slide-to]'));
  const copy = carousel.querySelector('[data-slide-copy]');
  const pauseButton = carousel.querySelector('[data-slide-pause]');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const dialog = document.getElementById('login-dialog');
  const interval = 6000;
  let current = 0;
  let timer;
  let manuallyPaused = reducedMotion.matches;
  let hovered = false;

  // Caption elements are optional: the current markup keeps static hero copy.
  function setText(selector, value) {
    const element = carousel.querySelector(selector);
    if (element && value != null) element.textContent = value;
  }

  function schedule() {
    window.clearTimeout(timer);
    const paused = manuallyPaused || hovered || document.hidden ||
      carousel.contains(document.activeElement) || (dialog && dialog.open);
    if (copy) copy.setAttribute('aria-live', paused ? 'polite' : 'off');
    if (!paused && slides.length > 1) {
      timer = window.setTimeout(function () { go(current + 1); }, interval);
    }
  }
  function go(index) {
    current = (index + slides.length) % slides.length;
    slides.forEach(function (slide, i) { slide.classList.toggle('is-active', i === current); });
    dots.forEach(function (dot, i) { dot.setAttribute('aria-current', String(i === current)); });
    const data = slides[current].dataset;
    setText('[data-slide-eyebrow]', data.eyebrow);
    setText('[data-slide-title]', data.title);
    setText('[data-slide-text]', data.text);
    schedule();
  }
  function updatePauseButton() {
    pauseButton.setAttribute('aria-pressed', String(manuallyPaused));
    pauseButton.setAttribute('aria-label', manuallyPaused ? 'Play slideshow' : 'Pause slideshow');
    pauseButton.firstElementChild.textContent = manuallyPaused ? '▶' : 'Ⅱ';
  }
  dots.forEach(function (dot) {
    dot.addEventListener('click', function () { go(Number(dot.dataset.slideTo)); });
  });
  carousel.querySelector('[data-slide-prev]').addEventListener('click', function () { go(current - 1); });
  carousel.querySelector('[data-slide-next]').addEventListener('click', function () { go(current + 1); });
  pauseButton.addEventListener('click', function () {
    manuallyPaused = !manuallyPaused;
    updatePauseButton();
    schedule();
  });
  carousel.addEventListener('mouseenter', function () { hovered = true; schedule(); });
  carousel.addEventListener('mouseleave', function () { hovered = false; schedule(); });
  carousel.addEventListener('focusin', schedule);
  carousel.addEventListener('focusout', function () { window.setTimeout(schedule, 0); });
  document.addEventListener('visibilitychange', schedule);
  document.addEventListener('most:dialogchange', schedule);
  reducedMotion.addEventListener('change', function () {
    manuallyPaused = reducedMotion.matches;
    updatePauseButton();
    schedule();
  });
  updatePauseButton();
  schedule();
};
