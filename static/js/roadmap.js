'use strict';

// Smooth scroll for pillar nav links with header offset.
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('a[href^="#pillar-"]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      var targetId = this.getAttribute('href').slice(1);
      var target = document.getElementById(targetId);
      if (!target) return;

      event.preventDefault();
      var header = document.querySelector('.site-header');
      var headerHeight = header ? header.offsetHeight : 0;
      var targetPosition =
        target.getBoundingClientRect().top + window.pageYOffset - headerHeight - 20;

      window.scrollTo({ top: targetPosition, behavior: 'smooth' });
      history.pushState(null, '', '#' + targetId);
    });
  });
});
