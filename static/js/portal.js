'use strict';

const passwordToggle = document.querySelector('[data-password-toggle]');
if (passwordToggle) {
  const passwordInput = document.getElementById(passwordToggle.getAttribute('aria-controls'));
  passwordToggle.hidden = false;
  passwordToggle.addEventListener('click', function () {
    const showPassword = passwordInput.type === 'password';
    passwordInput.type = showPassword ? 'text' : 'password';
    passwordToggle.textContent = showPassword ? 'ဝှက်ရန်' : 'ပြရန်';
    passwordToggle.setAttribute('aria-pressed', String(showPassword));
  });
}
