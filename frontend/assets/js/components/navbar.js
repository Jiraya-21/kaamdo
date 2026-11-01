/**
 * KaamDo Dynamic Navbar Component
 * Renders consistent header and mobile bottom navigation across all pages.
 */

const NavbarComponent = {
  render() {
    const isRoot = window.location.pathname.endsWith('index.html') || window.location.pathname.endsWith('/') || !window.location.pathname.includes('/pages/');
    const basePath = isRoot ? '' : '../../';

    const headerContainer = document.getElementById('navbar-container');
    if (headerContainer) {
      headerContainer.innerHTML = `
        <a href="#app-content" class="skip-link" data-i18n="nav.skip">Skip to content</a>
        <header class="navbar-header">
          <div class="container navbar">
            <a href="${basePath}index.html" class="navbar-brand">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" width="36" height="36">
                <rect width="40" height="40" rx="8" fill="#237E43"/>
                <path d="M12 28 L20 12 L28 28 Z" fill="#ffffff"/>
                <circle cx="28" cy="14" r="4" fill="#F59E0B" />
              </svg>
              <span>KaamDo</span>
            </a>

            <nav class="navbar-links">
              <a href="${basePath}pages/services/guest-request.html" class="nav-link" id="nav-daily">${this.label('nav.daily')}</a>
              <a href="${basePath}pages/jobs/jobs-list.html" class="nav-link" id="nav-jobs">${this.label('nav.jobs')}</a>
              <a href="${basePath}pages/equipment/equipment-list.html" class="nav-link" id="nav-equipment">${this.label('nav.equipment')}</a>
              <a href="${basePath}pages/jobs/farm-jobs.html" class="nav-link" id="nav-farm">${this.label('nav.farm')}</a>
            </nav>

            <div class="navbar-auth">
              <label class="lang-switch">
                <span class="visually-hidden">${this.label('nav.language')}</span>
                <select id="lang-select" aria-label="${this.label('nav.language')}">
                  <option value="en">English</option>
                  <option value="kn">ಕನ್ನಡ</option>
                  <option value="hi">हिन्दी</option>
                </select>
              </label>
              ${this.hasSavedSession() ? `
                <a href="${basePath}pages/dashboard/dashboard.html" class="btn btn-outline btn-sm" id="nav-account">${this.label('nav.account')}</a>
                <button type="button" class="btn btn-primary btn-sm" id="nav-logout">${this.label('nav.logout')}</button>
              ` : `
                <a href="${basePath}pages/auth/login.html" class="btn btn-outline btn-sm" id="nav-login">${this.label('nav.login')}</a>
                <a href="${basePath}pages/auth/register.html" class="btn btn-primary btn-sm" id="nav-signup">${this.label('nav.signup')}</a>
              `}
            </div>
          </div>
        </header>
      `;
    }

    // Render Mobile Bottom Navigation
    if (!document.getElementById('mobile-bottom-nav')) {
      const mobileNavHTML = `
        <nav id="mobile-bottom-nav" class="mobile-bottom-nav">
          <a href="${basePath}pages/services/guest-request.html" class="mobile-nav-item" id="mob-daily">
            <svg fill="currentColor" viewBox="0 0 20 20"><path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z"></path></svg>
            <span id="mob-daily-label">${this.label('nav.daily')}</span>
          </a>
          <a href="${basePath}pages/jobs/jobs-list.html" class="mobile-nav-item" id="mob-jobs">
            <svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M6 6V5a3 3 0 013-3h2a3 3 0 013 3v1h2a2 2 0 012 2v3.57A22.952 22.952 0 0110 13a22.95 22.95 0 01-8-1.43V8a2 2 0 012-2h2zm2-1a1 1 0 011-1h2a1 1 0 011 1v1H8V5zm1 5a1 1 0 011-1h.01a1 1 0 110 2H10a1 1 0 01-1-1z" clip-rule="evenodd"></path></svg>
            <span id="mob-jobs-label">${this.label('nav.jobs')}</span>
          </a>
          <a href="${basePath}pages/equipment/equipment-list.html" class="mobile-nav-item" id="mob-equipment">
            <svg fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd"></path></svg>
            <span id="mob-equipment-label">${this.label('nav.equipment')}</span>
          </a>
          <a href="${basePath}pages/jobs/farm-jobs.html" class="mobile-nav-item" id="mob-farm">
            <svg fill="currentColor" viewBox="0 0 20 20"><path d="M10 2a1 1 0 01.894.553l2 4A1 1 0 0112 8H8a1 1 0 01-.894-1.447l2-4A1 1 0 0110 2zM4 10a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zm1 4a1 1 0 100 2h10a1 1 0 100-2H5z"></path></svg>
            <span id="mob-farm-label">${this.label('nav.farm')}</span>
          </a>
        </nav>
      `;
      document.body.insertAdjacentHTML('beforeend', mobileNavHTML);
    }

    const logoutButton = document.getElementById('nav-logout');
    if (logoutButton) {
      logoutButton.addEventListener('click', () => {
        this.logout(basePath);
      });
    }
    this.bindLanguage();
    this.updateMobileLabels();
    this.highlightActive(isRoot);
    if (typeof I18n !== 'undefined') I18n.apply(document);
  },

  label(key) {
    return typeof I18n === 'undefined' ? key : I18n.t(key);
  },

  bindLanguage() {
    const select = document.getElementById('lang-select');
    if (!select || typeof I18n === 'undefined') return;
    select.value = I18n.currentLanguage();
    select.addEventListener('change', () => {
      I18n.current = I18n.write(localStorage, select.value);
      document.documentElement.lang = I18n.current;
      this.render();
      document.dispatchEvent(new CustomEvent('kaamdo:language', { detail: I18n.current }));
    });
  },

  updateMobileLabels() {
    const pairs = [
      ['mob-daily-label', 'nav.daily'],
      ['mob-jobs-label', 'nav.jobs'],
      ['mob-equipment-label', 'nav.equipment'],
      ['mob-farm-label', 'nav.farm'],
    ];
    pairs.forEach(([id, key]) => {
      const element = document.getElementById(id);
      if (element) element.textContent = this.label(key);
    });
  },

  hasSavedSession() {
    if (typeof StorageUtil === 'undefined' || typeof CONFIG === 'undefined') return false;
    const token = StorageUtil.get(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    return typeof token === 'string' && token.trim() !== '' && token !== 'demo_token_authenticated';
  },

  async logout(basePath) {
    const loginUrl = `${basePath}pages/auth/login.html`;
    let serverReached = false;
    if (typeof AccountSession !== 'undefined') {
      const result = await AccountSession.logout();
      serverReached = result.serverReached;
    } else {
      const token = StorageUtil.get(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
      try {
        await fetch(`${CONFIG.API_BASE_URL}/auth/logout/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...(token ? { Authorization: `Token ${token}` } : {})
          },
          body: '{}'
        });
        serverReached = true;
      } catch (error) {
        serverReached = false;
      }
      StorageUtil.remove(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
      StorageUtil.remove(CONFIG.STORAGE_KEYS.USER_DATA);
      StorageUtil.remove(CONFIG.STORAGE_KEYS.USER_ROLE);
    }
    const notice = serverReached ? '' : '?notice=offline-logout';
    window.location.href = `${loginUrl}${notice}`;
  },

  highlightActive(isRoot) {
    const path = window.location.pathname;
    let activeId = '';
    if (path.includes('farm-jobs') || path.includes('/agriculture/')) activeId = 'farm';
    else if (path.includes('/jobs/')) activeId = 'jobs';
    else if (path.includes('/services/')) activeId = 'daily';
    else if (path.includes('/equipment/')) activeId = 'equipment';

    const desktopEl = document.getElementById(`nav-${activeId}`);
    const mobileEl = document.getElementById(`mob-${activeId}`);
    if (desktopEl) desktopEl.classList.add('active');
    if (mobileEl) mobileEl.classList.add('active');
  }
};

document.addEventListener('DOMContentLoaded', () => {
  NavbarComponent.render();
});
