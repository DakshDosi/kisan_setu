(() => {
  const form = document.getElementById('register-form');
  const status = document.getElementById('form-status');
  if (!form) return;

  form.addEventListener('submit', (e) => {
    const username = form.username.value.trim();
    const password = form.password.value.trim();
    if (!username || !password) {
      e.preventDefault();
      status.textContent = 'Username and password are required.';
      status.style.color = '#b45309';
      return;
    }
    status.textContent = 'Submitting…';
    status.style.color = '#5b6b60';
  });
})();


