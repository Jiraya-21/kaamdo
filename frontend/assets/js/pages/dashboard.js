/**
 * Account home: one workspace card per capability from GET /api/v1/auth/me/.
 */

const DashboardController = {
  user: null,

  async init() {
    this.bindLogout();
    const retry = document.getElementById('session-retry');
    if (retry) retry.hidden = true;
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

  showOffline() {
    this.user = null;
    const nameEl = document.getElementById('dashboard-name');
    const profileEl = document.getElementById('dashboard-profile');
    if (nameEl) nameEl.textContent = this.text('account.yourAccount');
    if (profileEl) profileEl.textContent = '';
    this.showMessage(this.text('account.offline'));
    const retry = document.getElementById('session-retry');
    if (!retry) return;
    retry.hidden = false;
    if (retry.dataset.bound === 'true') return;
    retry.dataset.bound = 'true';
    retry.addEventListener('click', () => {
      this.showMessage('');
      this.init();
    });
  },

  showMessage(text) {
    const status = document.getElementById('dashboard-status');
    if (status) status.textContent = text;
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

  render() {
    const user = this.user;
    const nameEl = document.getElementById('dashboard-name');
    const profileEl = document.getElementById('dashboard-profile');
    if (nameEl) nameEl.textContent = this.displayName(user);
    if (profileEl) {
      profileEl.textContent = user.phone_number || '';
    }
    this.renderIdentity();
    this.renderTestPaymentBanner();
    this.renderProviderStatus();
    this.renderRoles();
    this.renderAdd();
    this.loadNotifications();
    this.bindLogout();
  },

  renderTestPaymentBanner() {
    const banner = document.getElementById('test-payment-banner');
    if (!banner) return;
    const payload = this.user && this.user.test_payment;
    const on = Boolean(payload && payload.enabled && payload.money_received === false);
    banner.hidden = !on;
    banner.textContent = on ? (payload.label || this.text('pay.testBanner')) : '';
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

  renderProviderStatus() {
    const host = document.getElementById('provider-status');
    if (!host) return;
    const allowed = typeof ProviderStatusLogic !== 'undefined'
      && ProviderStatusLogic.isProvider(this.user);
    host.hidden = !allowed;
    host.replaceChildren();
    if (!allowed || typeof ProviderStatus === 'undefined') return;
    ProviderStatus.mountAvailability(host, {
      onLoaded: (_value, _hasProfile, data) => {
        this.renderIdentity(data && data.photo_url);
        if (this.photoState) {
          this.photoState.hasProfile = Boolean(data);
          ProviderStatus.applyPhoto(this.photoState, data && data.photo_url, Boolean(data));
        }
      },
    });
    this.photoState = ProviderStatus.mountPhoto(host, {
      onChanged: (url) => this.renderIdentity(url),
    });
  },

  renderRoles() {
    const container = document.getElementById('role-list');
    if (!container) return;
    container.replaceChildren();
    const owned = AccountCatalog.allItems().filter((item) => (
      AccountSession.hasCapability(this.user, item.code)
    ));
    if (!owned.length) {
      const empty = document.createElement('p');
      empty.className = 'text-muted';
      empty.textContent = this.text('workspace.none');
      container.appendChild(empty);
      return;
    }
    owned.forEach((item) => container.appendChild(this.roleCard(item)));
  },

  roleCard(item) {
    const card = document.createElement('article');
    card.className = 'role-card';
    const title = document.createElement('h3');
    title.textContent = AccountCatalog.itemLabel(item);
    const summary = document.createElement('p');
    summary.className = 'text-muted';
    summary.textContent = AccountCatalog.itemSummary(item);
    const action = document.createElement('button');
    action.type = 'button';
    action.className = 'btn btn-primary';
    action.textContent = this.text('workspace.open');
    action.addEventListener('click', () => this.openWorkspace(item, action));
    card.append(title, summary, action);
    if (item.code === 'service_provider' && this.user.service_provider) {
      const status = document.createElement('p');
      status.className = 'text-muted';
      status.textContent = this.text('account.verification', {
        status: this.user.service_provider.verification_status.replaceAll('_', ' '),
      });
      card.appendChild(status);
    }
    return card;
  },

  async openWorkspace(item, button) {
    this.showMessage('');
    if (button) button.disabled = true;
    try {
      this.user = await AuthApi.setActiveMode(item.code);
      AccountSession.save(null, this.user);
    } catch (error) {
      /* The workspace page still checks the capability on the server. */
    }
    window.location.href = AccountCatalog.workspaceHref(item);
  },

  renderAdd() {
    const container = document.getElementById('capability-adder');
    if (!container) return;
    container.replaceChildren();
    const missing = AccountCatalog.allItems().filter(
      (item) => !AccountSession.hasCapability(this.user, item.code)
    );
    if (!missing.length) {
      const done = document.createElement('p');
      done.className = 'text-muted';
      done.textContent = this.text('account.allEnabled');
      container.appendChild(done);
      return;
    }
    missing.forEach((item) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-outline';
      button.textContent = this.text('account.addRole', { label: AccountCatalog.itemLabel(item) });
      button.addEventListener('click', () => this.enable(item.code, button));
      container.appendChild(button);
    });
  },

  bindLogout() {
    const button = document.getElementById('account-logout');
    if (!button || button.dataset.bound === 'true') return;
    button.dataset.bound = 'true';
    button.addEventListener('click', async () => {
      button.disabled = true;
      this.showMessage(this.text('account.signingOut'));
      const result = await AccountSession.logout();
      const notice = result.serverReached ? '' : '?notice=offline-logout';
      window.location.replace(`../auth/login.html${notice}`);
    });
  },

  async loadNotifications() {
    const status = document.getElementById('notification-status');
    const list = document.getElementById('notification-list');
    if (!status || !list) return;
    status.textContent = this.text('notify.loading');
    list.replaceChildren();
    try {
      const rows = await ApiClient.get('/notifications/');
      const items = Array.isArray(rows) ? rows : [];
      if (!items.length) {
        status.textContent = this.text('notify.empty');
        return;
      }
      status.textContent = '';
      items.forEach((row) => list.appendChild(this.notificationRow(row)));
    } catch (error) {
      status.textContent = this.text('notify.empty');
    }
  },

  notificationRow(row) {
    const article = document.createElement('article');
    article.className = 'notify-row';
    const title = document.createElement('h3');
    title.textContent = row.title || '';
    const body = document.createElement('p');
    body.className = 'text-muted';
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
    this.showMessage('');
    if (button) button.disabled = true;
    try {
      this.user = await AuthApi.enableCapability(code);
      AccountSession.save(null, this.user);
      this.render();
    } catch (error) {
      this.showMessage(AuthApi.formatError(error));
      if (button) button.disabled = false;
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  DashboardController.init();
});

document.addEventListener('kaamdo:language', () => {
  if (DashboardController.user) DashboardController.render();
});
