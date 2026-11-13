'use strict';

const passwordToggle = document.querySelector('[data-password-toggle]');
if (passwordToggle) {
  const passwordInput = document.getElementById(passwordToggle.getAttribute('aria-controls'));
  const eyeOpen = passwordToggle.querySelector('.eye-open');
  const eyeClosed = passwordToggle.querySelector('.eye-closed');
  passwordToggle.hidden = false;
  const showLabel = passwordToggle.getAttribute('aria-label') || 'စကားဝှက် ပြရန်';
  passwordToggle.dataset.showLabel = showLabel;
  passwordToggle.dataset.hideLabel = 'စကားဝှက် ဝှက်ရန်';
  
  function updateEyeIcons(showPassword) {
    if (eyeOpen) eyeOpen.style.display = showPassword ? 'none' : 'block';
    if (eyeClosed) eyeClosed.style.display = showPassword ? 'block' : 'none';
  }
  
  // Initial state
  updateEyeIcons(false);
  
  passwordToggle.addEventListener('click', function () {
    const showPassword = passwordInput.type === 'password';
    passwordInput.type = showPassword ? 'text' : 'password';
    passwordToggle.setAttribute('aria-pressed', String(showPassword));
    passwordToggle.setAttribute(
      'aria-label',
      showPassword ? passwordToggle.dataset.hideLabel : passwordToggle.dataset.showLabel
    );
    updateEyeIcons(showPassword);
  });
}