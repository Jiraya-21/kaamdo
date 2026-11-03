/**
 * KaamDo Login Controller
 * Signs in with the registered mobile number and stores the API token.
 */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('login-form');
  const errorEl = document.getElementById('login-error');
  if (!form || !errorEl) return;

  const next = new URLSearchParams(window.location.search).get('next');
  if (next === 'customer') {
    try {
      sessionStorage.setItem('kaamdo_after_login', '/pages/services/customer.html?view=track');
    } catch (storageError) { /* ignore */ }
  }

  if (new URLSearchParams(window.location.search).get('notice') === 'offline-logout') {
    errorEl.textContent = typeof I18n === 'undefined'
      ? 'You are signed out in this browser. The server could not be reached, so sign in and log out again when the connection works if this is a shared computer.'
      : I18n.t('login.offlineLogout');
    errorEl.style.display = 'block';
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const phone = typeof AuthFormLogic === 'undefined'
      ? document.getElementById('login-phone').value.trim()
      : AuthFormLogic.phoneDigits(document.getElementById('login-phone').value);
    const password = document.getElementById('login-password').value;
    const button = form.querySelector('button[type="submit"]');

    errorEl.style.display = 'none';
    if (typeof AuthFormLogic !== 'undefined') {
      const problems = AuthFormLogic.loginProblems(phone, password);
      if (problems.length) {
        errorEl.textContent = problems.map((key) => (
          typeof I18n === 'undefined' ? key : I18n.t(key)
        )).join(' ');
        errorEl.style.display = 'block';
        return;
      }
    }
    button.disabled = true;

    try {
      const result = await AuthApi.login({
        phone_number: phone,
        password
      });
      StorageUtil.set(CONFIG.STORAGE_KEYS.AUTH_TOKEN, result.token);
      StorageUtil.set(CONFIG.STORAGE_KEYS.USER_DATA, result.user);
      StorageUtil.set(CONFIG.STORAGE_KEYS.USER_ROLE, result.user.active_mode);
      let stored = '';
      try {
        stored = sessionStorage.getItem('kaamdo_after_login') || '';
        sessionStorage.removeItem('kaamdo_after_login');
      } catch (storageError) {
        stored = '';
      }
      const nextPath = typeof AccountSession === 'undefined'
        ? '../dashboard/dashboard.html'
        : AccountSession.safeNextPath(stored);
      window.location.href = nextPath;
    } catch (error) {
      errorEl.textContent = AuthApi.formatError(error);
      errorEl.style.display = 'block';
      button.disabled = false;
    }
  });
});
