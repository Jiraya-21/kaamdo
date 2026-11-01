/**
 * One workspace. The page stays closed until GET /api/v1/auth/me/ confirms the role.
 */

const AreaPage = {
  text(key) {
    return typeof I18n === 'undefined' ? key : I18n.t(key);
  },

  verificationText(state) {
    const key = `verify.${state}`;
    const translated = this.text(key);
    return translated === key ? state : translated;
  },

  async init() {
    const page = document.body.dataset.accountPage;
    const result = await AccountSession.restore();
    if (result.status === 'anonymous' || result.status === 'invalid') {
      AccountSession.rememberReturnPath();
      window.location.replace('../auth/login.html');
      return;
    }
    const titleEl = document.getElementById('area-title');
    const contentEl = document.getElementById('area-content');
    const items = AccountCatalog.itemsForPage(page);
    const workspace = typeof AccountWorkspace === 'undefined'
      ? ''
      : AccountWorkspace.fromQuery(window.location.search);
    if (titleEl) titleEl.textContent = items.length ? items[0].groupTitle : this.text('area.accountArea');
    this.renderNav();
    if (result.status === 'offline') {
      this.showStatus(this.text('area.offline'));
      return;
    }
    const codes = result.user && Array.isArray(result.user.capabilities) ? result.user.capabilities : [];
    const owned = typeof AccountWorkspace === 'undefined'
      ? items.filter((item) => AccountSession.hasCapability(result.user, item.code))
      : AccountWorkspace.owned(items, codes);
    if (!owned.length) {
      this.showBlocked();
      return;
    }
    if (!workspace && owned.length > 1) {
      this.showStatus('');
      this.showChooser(owned);
      return;
    }
    const allowed = typeof AccountWorkspace === 'undefined'
      ? owned
      : AccountWorkspace.pick(owned, workspace, codes);
    if (!allowed.length) {
      this.showBlocked();
      return;
    }
    this.showStatus('');
    contentEl.replaceChildren();
    allowed.forEach((item) => {
      if (titleEl) titleEl.textContent = AccountCatalog.itemLabel(item);
      contentEl.appendChild(this.section(item, result.user));
    });
  },

  renderNav() {
    const host = document.getElementById('workspace-nav');
    if (!host) return;
    host.replaceChildren();
    const back = document.createElement('a');
    back.className = 'workspace-back';
    back.href = '../dashboard/dashboard.html';
    back.textContent = this.text('workspace.switch');
    host.appendChild(back);
  },

  showStatus(text) {
    const status = document.getElementById('area-status');
    if (status) status.textContent = text;
  },

  showBlocked() {
    const contentEl = document.getElementById('area-content');
    contentEl.replaceChildren();
    const card = document.createElement('div');
    card.className = 'account-card';
    const heading = document.createElement('h2');
    heading.textContent = this.text('area.blockedTitle');
    const copy = document.createElement('p');
    copy.className = 'text-muted';
    copy.textContent = this.text('area.blockedBody');
    const link = document.createElement('a');
    link.className = 'btn btn-primary';
    link.href = '../dashboard/dashboard.html';
    link.textContent = this.text('area.back');
    card.append(heading, copy, link);
    contentEl.appendChild(card);
  },

  showChooser(items) {
    const contentEl = document.getElementById('area-content');
    contentEl.replaceChildren();
    const lead = document.createElement('p');
    lead.className = 'text-muted';
    lead.textContent = this.text('workspace.choose');
    contentEl.appendChild(lead);
    items.forEach((item) => {
      const card = document.createElement('article');
      card.className = 'role-card';
      const title = document.createElement('h2');
      title.textContent = AccountCatalog.itemLabel(item);
      const summary = document.createElement('p');
      summary.className = 'text-muted';
      summary.textContent = AccountCatalog.itemSummary(item);
      const link = document.createElement('a');
      link.className = 'btn btn-primary';
      link.href = AccountCatalog.workspaceHref(item);
      link.textContent = this.text('workspace.open');
      card.append(title, summary, link);
      contentEl.appendChild(card);
    });
  },

  section(item, user) {
    const card = document.createElement('article');
    card.className = 'workspace-panel';
    const heading = document.createElement('h2');
    heading.className = 'visually-hidden';
    heading.textContent = AccountCatalog.itemLabel(item);
    const summary = document.createElement('p');
    summary.className = 'text-muted workspace-lead';
    summary.textContent = AccountCatalog.itemSummary(item);
    card.append(heading, summary);
    if (item.code === 'agricultural_employer' && typeof FarmHiring !== 'undefined') {
      FarmHiring.mountEmployer(card);
      if (typeof JobAccount !== 'undefined') JobAccount.mountEmployer(card, JobAccountLogic.FARM);
    } else if (item.code === 'agricultural_worker' && typeof FarmHiring !== 'undefined') {
      FarmHiring.mountWorker(card);
      if (typeof JobAccount !== 'undefined') JobAccount.mountSeeker(card, JobAccountLogic.FARM);
    } else if (item.code === 'equipment_owner' && typeof EquipmentAccount !== 'undefined') {
      EquipmentAccount.mountOwner(card);
    } else if (item.code === 'equipment_renter' && typeof EquipmentAccount !== 'undefined') {
      EquipmentAccount.mountRenter(card);
    } else if (item.code === 'employer' && typeof JobAccount !== 'undefined') {
      JobAccount.mountEmployer(card);
    } else if (item.code === 'job_seeker' && typeof JobAccount !== 'undefined') {
      JobAccount.mountSeeker(card);
    } else if (item.code === 'customer' && typeof DailyAccount !== 'undefined') {
      DailyAccount.mountCustomer(card, user);
      if (typeof ServiceRequestAccount !== 'undefined') {
        const extra = document.createElement('details');
        extra.className = 'account-details customer-direct';
        const summary = document.createElement('summary');
        summary.textContent = this.text('customer.directSummary');
        const inner = document.createElement('div');
        extra.append(summary, inner);
        card.appendChild(extra);
        ServiceRequestAccount.mountCustomer(inner);
      }
    } else if (item.code === 'service_provider') {
      if (typeof ServiceRequestAccount !== 'undefined') ServiceRequestAccount.mountProvider(card, user);
    } else {
      const gap = document.createElement('p');
      gap.textContent = this.text('area.notBuilt');
      card.appendChild(gap);
    }
    if (item.code === 'service_provider' && user.service_provider) {
      const verification = document.createElement('p');
      const state = user.service_provider.verification_status;
      verification.textContent = this.verificationText(state);
      const separate = document.createElement('p');
      separate.className = 'text-muted';
      separate.textContent = this.text('area.profileVsVerify');
      card.append(verification, separate);
    }
    if (item.page === 'agriculture/hiring.html') {
      const boundary = document.createElement('p');
      boundary.className = 'text-muted';
      boundary.textContent = this.text('area.farmBoundary');
      card.appendChild(boundary);
    }
    if (item.page === 'equipment/rental.html') {
      const boundary = document.createElement('p');
      boundary.className = 'text-muted';
      boundary.textContent = this.text('area.equipBoundary');
      card.appendChild(boundary);
    }
    return card;
  }
};

document.addEventListener('DOMContentLoaded', () => {
  AreaPage.init();
});

document.addEventListener('kaamdo:language', () => {
  if (document.body && document.body.dataset.accountPage) AreaPage.init();
});
