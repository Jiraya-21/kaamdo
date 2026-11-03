/**
 * Compact account hub: name, Available tap, marketplace taps, roles, add work.
 */

const DashboardController = {
  user: null,
  availabilityState: null,

  async init() {
    this.bindLogout();
    this.hideAlert();
    const result = await AccountSession.restore();
    if (result.status === 'anonymous' || result.status === 'invalid') {
      window.location.replace('../auth/login.html');
      return;
    }
    if (result.status === 'offline') {
      this.showOffline();
      return;
    }
    this.user = result.user;
    this.render();
  },

  hideAlert() {
    const alert = document.getElementById('account-alert');
    const status = document.getElementById('dashboard-status');
    const retry = document.getElementById('session-retry');
    if (alert) alert.hidden = true;
    if (status) status.textContent = '';
    if (retry) retry.hidden = true;
  },

  showAlert(message, { retry = false } = {}) {
    const alert = document.getElementById('account-alert');
    const status = document.getElementById('dashboard-status');
    const retryBtn = document.getElementById('session-retry');
    if (status) status.textContent = message || '';
    if (alert) alert.hidden = !message;
    if (retryBtn) {
      retryBtn.hidden = !retry;
      if (retry && retryBtn.dataset.bound !== 'true') {
        retryBtn.dataset.bound = 'true';
        retryBtn.addEventListener('click', () => {
          this.hideAlert();
          this.init();
        });
      }
    }
  },

  showOffline() {
    this.user = null;
    const nameEl = document.getElementById('dashboard-name');
    const profileEl = document.getElementById('dashboard-profile');
    if (nameEl) nameEl.textContent = this.text('account.yourAccount');
    if (profileEl) profileEl.textContent = '';
    this.showAlert(this.text('account.offline'), { retry: true });
    const roles = document.getElementById('roles-block');
    const add = document.getElementById('add-role-block');
    const notify = document.getElementById('notify-block');
    if (roles) roles.hidden = true;
    if (add) add.hidden = true;
    if (notify) notify.hidden = true;
    const avail = document.getElementById('hub-availability');
    if (avail) {
      avail.hidden = true;
      avail.replaceChildren();
    }
    this.availabilityState = null;
    const market = document.getElementById('marketplace-list');
    if (market) market.replaceChildren();
  },

  showMessage(text) {
    if (!text) {
      this.hideAlert();
      return;
    }
    this.showAlert(text, { retry: false });
  },

  displayName(user) {
    if (typeof user.full_name === 'string' && user.full_name.trim()) {
      return user.full_name.trim();
    }
    const combined = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
    return combined || this.text('account.yourAccount');
  },

  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  verificationLabel(code) {
    if (code !== 'service_provider' || !this.user || !this.user.service_provider) return '';
    const raw = String(this.user.service_provider.verification_status || '').trim();
    if (!raw || raw === 'approved') return '';
    const shortKey = {
      not_submitted: 'hub.verifyNeed',
      pending: 'hub.verifyWait',
      rejected: 'hub.verifyNo',
      needs_info: 'hub.verifyMore',
    }[raw];
    return shortKey ? this.text(shortKey) : '';
  },

  render() {
    this.hideAlert();
    const user = this.user;
    const nameEl = document.getElementById('dashboard-name');
    const profileEl = document.getElementById('dashboard-profile');
    if (nameEl) nameEl.textContent = this.displayName(user);
    if (profileEl) profileEl.textContent = user.phone_number || '';
    this.renderIdentity('');
    this.loadIdentityPhoto();
    this.renderTestPaymentBanner();
    this.renderAvailability();
    this.renderMarketplaces();
    this.renderRoles();
    this.renderAdd();
    this.loadNotifications();
    this.bindLogout();
    if (typeof I18n !== 'undefined') I18n.apply(document);
  },

  renderAvailability() {
    const host = document.getElementById('hub-availability');
    if (!host) return;
    const isProvider = typeof ProviderStatusLogic !== 'undefined'
      && ProviderStatusLogic.isProvider(this.user);
    if (!isProvider || typeof ProviderStatus === 'undefined') {
      host.hidden = true;
      host.replaceChildren();
      this.availabilityState = null;
      return;
    }
    if (this.availabilityState && host.contains(this.availabilityState.wrap)) {
      host.hidden = false;
      return;
    }
    host.replaceChildren();
    host.hidden = false;
    this.availabilityState = ProviderStatus.mountAvailability(host, { compact: true });
  },

  async loadIdentityPhoto() {
    if (typeof ProviderStatusLogic === 'undefined' || !ProviderStatusLogic.isProvider(this.user)) {
      return;
    }
    try {
      const data = await ApiClient.get(ProviderStatusLogic.PROFILE_PATH);
      if (this.user) this.renderIdentity(data && data.photo_url);
    } catch (error) {
      if (this.user) this.renderIdentity('');
    }
  },

  renderTestPaymentBanner() {
    const banner = document.getElementById('test-payment-banner');
    if (!banner) return;
    // First-phase UI: do not show staff/test payment banners to ordinary users.
    banner.hidden = true;
    banner.textContent = '';
  },

  renderIdentity(photoUrl) {
    const photo = document.getElementById('account-photo');
    const initials = document.getElementById('account-initials');
    const name = this.displayName(this.user);
    const uploaded = typeof ProviderStatusLogic !== 'undefined'
      && ProviderStatusLogic.hasUploadedPhoto(photoUrl);
    if (photo) {
      if (uploaded) {
        photo.hidden = false;
        photo.src = ProviderStatusLogic.photoSrc(photoUrl);
        photo.alt = this.text('profile.photoAlt', { name });
      } else {
        photo.hidden = true;
        photo.removeAttribute('src');
        photo.alt = '';
      }
    }
    if (initials) {
      initials.hidden = uploaded;
      initials.textContent = typeof ProviderStatusLogic === 'undefined'
        ? name.slice(0, 2).toUpperCase()
        : ProviderStatusLogic.initials(name);
    }
  },

  renderMarketplaces() {
    const container = document.getElementById('marketplace-list');
    if (!container) return;
    container.replaceChildren();
    const items = AccountCatalog.marketplaces || [];
    items.forEach((item) => {
      const link = document.createElement('a');
      link.className = 'marketplace-link';
      link.href = AccountCatalog.marketplaceHref(item);
      if (typeof KaamdoImages !== 'undefined') {
        const image = document.createElement('img');
        image.className = 'marketplace-link-image';
        image.src = KaamdoImages.marketplace(item.id);
        image.alt = '';
        image.setAttribute('aria-hidden', 'true');
        link.appendChild(image);
      }
      const title = document.createElement('span');
      title.className = 'marketplace-link-title';
      title.textContent = AccountCatalog.itemLabel(item);
      link.append(title);
      container.appendChild(link);
    });
  },

  renderRoles() {
    const block = document.getElementById('roles-block');
    const container = document.getElementById('role-list');
    if (!block || !container) return;
    container.replaceChildren();
    const owned = AccountCatalog.allItems().filter((item) => (
      AccountSession.hasCapability(this.user, item.code)
    ));
    block.hidden = owned.length === 0;
    if (!owned.length) return;
    owned.forEach((item) => container.appendChild(this.roleRow(item)));
  },

  roleTagLine(item) {
    const section = item.groupTitle || this.text('nav.daily');
    if (item.code === 'service_provider') {
      const categories = (
        this.user
        && this.user.service_provider
        && Array.isArray(this.user.service_provider.categories)
      ) ? this.user.service_provider.categories : [];
      const names = categories
        .map((row) => (row && row.name ? String(row.name).trim() : ''))
        .filter(Boolean);
      if (names.length) {
        return names.map((name) => `${section} · ${name}`).join(' · ');
      }
      return `${section} · ${this.text('role.providerShort')}`;
    }
    return `${section} · ${AccountCatalog.itemLabel(item)}`;
  },

  roleRow(item) {
    const row = document.createElement('li');
    row.className = 'hub-row';

    const copy = document.createElement('div');
    copy.className = 'hub-row-copy';
    const title = document.createElement('p');
    title.className = 'hub-row-title';
    title.textContent = this.roleTagLine(item);
    copy.append(title);
    const verification = this.verificationLabel(item.code);
    if (verification) {
      const meta = document.createElement('p');
      meta.className = 'hub-row-meta';
      meta.textContent = verification;
      copy.appendChild(meta);
    }

    const action = document.createElement('a');
    action.className = 'btn btn-primary btn-sm';
    action.href = AccountCatalog.workspaceHref(item);
    action.textContent = this.text('hub.openWork');
    action.addEventListener('click', (event) => {
      event.preventDefault();
      this.openWorkspace(item, action);
    });

    row.append(copy, action);
    return row;
  },

  async openWorkspace(item, control) {
    this.hideAlert();
    if (control) {
      control.setAttribute('aria-disabled', 'true');
      if (control.tagName === 'BUTTON' || control.tagName === 'A') {
        control.style.pointerEvents = 'none';
      }
    }
    try {
      this.user = await AuthApi.setActiveMode(item.code);
      AccountSession.save(null, this.user);
    } catch (error) {
      /* Workspace page still checks capability on the server. */
    }
    window.location.href = AccountCatalog.workspaceHref(item);
  },

  renderAdd() {
    const block = document.getElementById('add-role-block');
    const container = document.getElementById('capability-adder');
    if (!block || !container) return;
    container.replaceChildren();
    const missing = AccountCatalog.allItems().filter(
      (item) => !AccountSession.hasCapability(this.user, item.code)
    );
    if (!missing.length) {
      block.hidden = true;
      return;
    }
    block.hidden = false;
    missing.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'hub-add-row';
      const title = document.createElement('p');
      title.className = 'hub-row-title';
      title.textContent = AccountCatalog.itemLabel(item);
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-outline btn-sm';
      button.textContent = this.text('hub.addWork');
      button.addEventListener('click', () => this.enable(item.code, button));
      row.append(title, button);
      container.appendChild(row);
    });
  },

  bindLogout() {
    const button = document.getElementById('account-logout');
    if (!button || button.dataset.bound === 'true') return;
    button.dataset.bound = 'true';
    button.addEventListener('click', async () => {
      button.disabled = true;
      this.showAlert(this.text('account.signingOut'), { retry: false });
      const result = await AccountSession.logout();
      const notice = result.serverReached ? '' : '?notice=offline-logout';
      window.location.replace(`../auth/login.html${notice}`);
    });
  },

  async loadNotifications() {
    const block = document.getElementById('notify-block');
    const status = document.getElementById('notification-status');
    const list = document.getElementById('notification-list');
    if (!block || !status || !list) return;
    list.replaceChildren();
    status.hidden = true;
    status.textContent = '';
    try {
      const rows = await ApiClient.get('/notifications/');
      const items = Array.isArray(rows) ? rows : [];
      if (!items.length) {
        block.hidden = true;
        return;
      }
      block.hidden = false;
      items.forEach((row) => list.appendChild(this.notificationRow(row)));
    } catch (error) {
      block.hidden = true;
    }
  },

  notificationRow(row) {
    const article = document.createElement('article');
    article.className = 'hub-notify-row';
    const title = document.createElement('p');
    title.className = 'hub-row-title';
    title.textContent = row.title || '';
    const body = document.createElement('p');
    body.className = 'hub-row-summary';
    body.textContent = row.body || '';
    article.append(title, body);
    if (!row.read_at) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-outline btn-sm';
      button.textContent = this.text('notify.markRead');
      button.addEventListener('click', () => this.markNotificationRead(row, article, button));
      article.appendChild(button);
    }
    return article;
  },

  async markNotificationRead(row, article, button) {
    button.disabled = true;
    try {
      await ApiClient.post(`/notifications/${row.id}/read/`, {});
      button.remove();
    } catch (error) {
      button.disabled = false;
    }
  },

  async enable(code, button) {
    this.hideAlert();
    if (button) button.disabled = true;
    try {
      this.user = await AuthApi.enableCapability(code);
      AccountSession.save(null, this.user);
      this.render();
    } catch (error) {
      this.showAlert(AuthApi.formatError(error), { retry: false });
      if (button) button.disabled = false;
    }
  },
};

document.addEventListener('DOMContentLoaded', () => {
  DashboardController.init();
});

document.addEventListener('kaamdo:language', () => {
  if (DashboardController.user) DashboardController.render();
});
