/**
 * KaamDo Registration Controller
 * Creates a customer or worker account and stores the API token.
 * District is collected later on listings and provider profiles, not here.
 */

document.addEventListener('DOMContentLoaded', () => {
  const role = new URLSearchParams(window.location.search).get('role');
  const capability = document.getElementById('reg-capability');
  if (capability && (role === 'worker' || role === 'service_provider')) {
    capability.value = 'service_provider';
  }

  const form = document.getElementById('register-form');
  const errorEl = document.getElementById('register-error');
  if (!form) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    errorEl.style.display = 'none';
    const fullName = document.getElementById('reg-name').value.trim();
    const phone = typeof AuthFormLogic === 'undefined'
      ? document.getElementById('reg-phone').value.trim()
      : AuthFormLogic.phoneDigits(document.getElementById('reg-phone').value);
    const password = document.getElementById('reg-password').value;
    if (typeof AuthFormLogic !== 'undefined') {
      const problems = AuthFormLogic.registerProblems(fullName, phone, password);
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
      const result = await AuthApi.register({
        capabilities: [document.getElementById('reg-capability').value],
        full_name: fullName,
        phone_number: phone,
        password
      });
      StorageUtil.set(CONFIG.STORAGE_KEYS.AUTH_TOKEN, result.token);
      StorageUtil.set(CONFIG.STORAGE_KEYS.USER_DATA, result.user);
      StorageUtil.set(CONFIG.STORAGE_KEYS.USER_ROLE, result.user.active_mode);
      window.location.href = '../dashboard/dashboard.html';
    } catch (error) {
      errorEl.textContent = AuthApi.formatError(error);
      errorEl.style.display = 'block';
      button.disabled = false;
    }
  });
});
