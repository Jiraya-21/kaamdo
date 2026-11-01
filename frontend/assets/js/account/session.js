/**
 * Signed-in account session.
 * localStorage keeps the token between pages. Permission always comes from /auth/me/.
 */

const AccountSession = {
  save(token, user) {
    if (typeof token === 'string' && token.trim()) {
      StorageUtil.set(CONFIG.STORAGE_KEYS.AUTH_TOKEN, token);
    }
    StorageUtil.set(CONFIG.STORAGE_KEYS.USER_DATA, user);
    StorageUtil.set(CONFIG.STORAGE_KEYS.USER_ROLE, user && user.active_mode ? user.active_mode : '');
  },

  clear() {
    StorageUtil.remove(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    StorageUtil.remove(CONFIG.STORAGE_KEYS.USER_DATA);
    StorageUtil.remove(CONFIG.STORAGE_KEYS.USER_ROLE);
  },

  hasCapability(user, code) {
    return Boolean(user && Array.isArray(user.capabilities) && user.capabilities.includes(code));
  },

  async restore() {
    const token = StorageUtil.get(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    if (typeof token !== 'string' || !token.trim() || token === 'demo_token_authenticated') {
      this.clear();
      return { status: 'anonymous' };
    }
    try {
      const user = await AuthApi.getCurrentUser();
      this.save(null, user);
      return { status: 'ok', user };
    } catch (error) {
      if (error && (error.status === 401 || error.status === 403)) {
        this.clear();
        return { status: 'invalid' };
      }
      return { status: 'offline' };
    }
  },

  async logout() {
    let serverReached = false;
    try {
      await AuthApi.logout();
      serverReached = true;
    } catch (error) {
      serverReached = Boolean(error && error.status);
    }
    this.clear();
    return { ok: true, serverReached };
  },

  rememberReturnPath() {
    try {
      sessionStorage.setItem(
        'kaamdo_after_login',
        `${window.location.pathname}${window.location.search}${window.location.hash}`,
      );
      return true;
    } catch (error) {
      return false;
    }
  },

  safeNextPath(stored, fallback) {
    const home = fallback || '../dashboard/dashboard.html';
    if (typeof stored !== 'string') return home;
    if (!stored.startsWith('/') || stored.startsWith('//') || stored.includes('\\')) return home;
    return stored;
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = AccountSession;
}
