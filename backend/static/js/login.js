(() => {
  const tabPhone = document.getElementById('tab-phone');
  const tabEmail = document.getElementById('tab-email');
  const fieldPhone = document.getElementById('field-phone');
  const fieldEmail = document.getElementById('field-email');
  const peek = document.getElementById('peek');
  const pwd = document.getElementById('password');
  const form = document.getElementById('login-form');

  function setTab(mode){
    const isPhone = mode === 'phone';
    tabPhone.classList.toggle('active', isPhone);
    tabEmail.classList.toggle('active', !isPhone);
    fieldPhone.classList.toggle('hidden', !isPhone);
    fieldEmail.classList.toggle('hidden', isPhone);
  }

  tabPhone?.addEventListener('click', () => setTab('phone'));
  tabEmail?.addEventListener('click', () => setTab('email'));

  peek?.addEventListener('click', () => {
    const is = pwd.getAttribute('type') === 'password';
    pwd.setAttribute('type', is ? 'text' : 'password');
  });

  // On submit, navigate to chat page after basic check.
  form?.addEventListener('submit', (e) => {
    const phone = (document.getElementById('phone')?.value || '').trim();
    const email = (document.getElementById('email')?.value || '').trim();
    if (!phone && !email) {
      // use browser validation instead
    }
  });
})();


