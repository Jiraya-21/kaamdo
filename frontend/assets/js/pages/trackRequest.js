/**
 * Simple request tracking:
 * - Account users → My requests
 * - Guests → verified mobile number → list every request for that number
 */

const TrackRequestPage = {
  busy: false,
  path: '',
  phone: '',
  verified: false,
  rows: [],

  init() {
    this.bind();
    this.applyUserMode();
    this.openInitialPath();
    this.prefillPhone();
  },

  bind() {
    const phoneForm = document.getElementById('track-phone-form');
    const verifyForm = document.getElementById('track-verify-form');
    if (phoneForm) phoneForm.addEventListener('submit', (event) => this.sendCode(event));
    if (verifyForm) verifyForm.addEventListener('submit', (event) => this.verifyCode(event));
    const chooseAccount = document.getElementById('track-choose-account');
    const chooseGuest = document.getElementById('track-choose-guest');
    const backAccount = document.getElementById('track-back-account');
    const backGuest = document.getElementById('track-back-guest');
    if (chooseAccount) chooseAccount.addEventListener('click', () => this.showPath('account'));
    if (chooseGuest) chooseGuest.addEventListener('click', () => this.showPath('guest'));
    if (backAccount) backAccount.addEventListener('click', () => this.showPath(''));
    if (backGuest) backGuest.addEventListener('click', () => this.showPath(''));
  },

  text(key) {
    return typeof I18n === 'undefined' ? key : I18n.t(key);
  },

  isSignedIn() {
    if (typeof StorageUtil === 'undefined' || typeof CONFIG === 'undefined') return false;
    const token = StorageUtil.get(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    return typeof token === 'string' && token.trim() !== '' && token !== 'demo_token_authenticated';
  },

  show(id, text, kind) {
    const notice = document.getElementById(id);
    if (!notice) return;
    notice.textContent = text || '';
    notice.classList.remove('is-error', 'is-success', 'is-info');
    if (text && kind) notice.classList.add(`is-${kind}`);
  },

  applyUserMode() {
    const signedIn = this.isSignedIn();
    const loginLink = document.getElementById('track-login-link');
    const myRequests = document.getElementById('track-my-requests');
    if (loginLink) {
      loginLink.hidden = signedIn;
      loginLink.href = '../auth/login.html?next=customer';
    }
    if (myRequests) {
      myRequests.href = signedIn
        ? '../services/customer.html?view=track'
        : '../auth/login.html?next=customer';
      myRequests.textContent = signedIn
        ? this.text('guest.myRequests')
        : this.text('home.trackLogin');
    }
  },

  openInitialPath() {
    const query = new URLSearchParams(window.location.search);
    const forceGuest = query.get('guest') === '1';
    const storedPhone = sessionStorage.getItem('kaamdo_guest_phone') || '';
    // Signed-in accounts track in My requests — no OTP, no guest form.
    if (this.isSignedIn() && !forceGuest) {
      window.location.replace('../services/customer.html?view=track');
      return;
    }
    if (forceGuest || storedPhone) {
      this.showPath('guest');
      return;
    }
    this.showPath('');
  },

  showPath(path) {
    this.path = path || '';
    const chooser = document.getElementById('track-chooser');
    const accountPath = document.getElementById('track-account-path');
    const guestPath = document.getElementById('track-guest-path');
    if (chooser) chooser.hidden = Boolean(path);
    if (accountPath) accountPath.hidden = path !== 'account';
    if (guestPath) guestPath.hidden = path !== 'guest';
    if (path !== 'guest') {
      this.clearResult();
      this.clearList();
    }
  },

  prefillPhone() {
    const input = document.getElementById('track-phone');
    if (!input) return;
    const stored = sessionStorage.getItem('kaamdo_guest_phone') || '';
    if (stored) {
      input.value = GuestServiceLogic.phone(stored);
      this.show('status-notice', this.text('track.savedOnThisPhone'), 'info');
    }
  },

  setBusy(busy) {
    this.busy = busy;
    ['track-send-code', 'track-verify-code'].forEach((id) => {
      const button = document.getElementById(id);
      if (button) button.disabled = busy;
    });
  },

  async sendCode(event) {
    event.preventDefault();
    if (this.busy) return;
    const phone = GuestServiceLogic.phone(document.getElementById('track-phone').value);
    const problems = GuestServiceLogic.trackPhoneProblems(phone);
    if (problems.length) {
      this.show('status-notice', problems.join(' '), 'error');
      return;
    }
    this.setBusy(true);
    this.show('status-notice', this.text('guest.checking'), 'info');
    try {
      const data = await ApiClient.post(
        GuestServiceLogic.SEND_PATH,
        GuestServiceLogic.sendPayload({ phone }),
      );
      const result = GuestServiceLogic.sendResult(data);
      if (!result.ok) {
        this.show('status-notice', result.text || this.text('guest.noCode'), 'error');
        return;
      }
      this.phone = phone;
      this.verified = false;
      document.getElementById('track-verify-form').hidden = false;
      this.show('status-notice', result.text, result.practice ? 'info' : 'success');
      if (result.devCode) {
        document.getElementById('track-code').value = result.devCode;
      }
    } catch (error) {
      this.show('status-notice', GuestServiceLogic.errorText(error), 'error');
    } finally {
      this.setBusy(false);
    }
  },

  async verifyCode(event) {
    event.preventDefault();
    if (this.busy) return;
    const phone = this.phone || GuestServiceLogic.phone(document.getElementById('track-phone').value);
    const code = document.getElementById('track-code').value;
    const problems = [
      ...GuestServiceLogic.trackPhoneProblems(phone),
      ...GuestServiceLogic.codeProblems(code),
    ];
    if (problems.length) {
      this.show('status-notice', problems.join(' '), 'error');
      return;
    }
    this.setBusy(true);
    this.show('status-notice', this.text('guest.checking'), 'info');
    try {
      const verified = await ApiClient.post(
        GuestServiceLogic.VERIFY_PATH,
        GuestServiceLogic.verifyPayload({ phone, code }),
      );
      const check = GuestServiceLogic.verifyResult(verified);
      if (!check.ok) {
        this.show('status-notice', check.text, 'error');
        return;
      }
      this.phone = phone;
      this.verified = true;
      try {
        sessionStorage.setItem('kaamdo_guest_phone', phone);
      } catch (error) { /* ignore */ }
      await this.loadByPhone();
    } catch (error) {
      this.show('status-notice', GuestServiceLogic.errorText(error), 'error');
    } finally {
      this.setBusy(false);
    }
  },

  async loadByPhone() {
    const data = await ApiClient.post(
      GuestServiceLogic.BY_PHONE_PATH,
      GuestServiceLogic.byPhonePayload(this.phone),
    );
    const list = GuestServiceLogic.trackListView(data);
    if (!list.ok) {
      this.clearList();
      this.clearResult();
      this.show('status-notice', list.text, 'error');
      return;
    }
    this.rows = list.rows;
    if (!list.rows.length) {
      this.clearList();
      this.clearResult();
      this.show('status-notice', this.text('track.noneForPhone'), 'info');
      return;
    }
    this.show('status-notice', this.text('track.foundCount').split('{count}').join(String(list.count)), 'success');
    this.renderList(list.rows);
    if (list.rows.length === 1) {
      this.openRequest(list.rows[0]);
    } else {
      this.clearResult();
    }
  },

  clearList() {
    const root = document.getElementById('track-request-list');
    if (!root) return;
    root.replaceChildren();
    root.hidden = true;
  },

  renderList(rows) {
    const root = document.getElementById('track-request-list');
    if (!root) return;
    root.replaceChildren();
    const heading = document.createElement('h3');
    heading.textContent = this.text('track.listHeading');
    root.appendChild(heading);
    rows.forEach((row) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'track-request-item';
      const statusText = typeof I18n === 'undefined'
        ? GuestServiceLogic.statusSentence(row.status, '')
        : I18n.statusText(row.status, '');
      button.innerHTML = '';
      const title = document.createElement('strong');
      title.textContent = row.category || this.text('track.resultHeading');
      const meta = document.createElement('span');
      meta.textContent = statusText;
      const desc = document.createElement('span');
      desc.className = 'track-request-desc';
      desc.textContent = row.description || '';
      button.append(title, meta, desc);
      button.addEventListener('click', () => this.openRequest(row));
      root.appendChild(button);
    });
    root.hidden = false;
  },

  openRequest(row) {
    const view = GuestServiceLogic.statusView(row);
    this.renderStatus(view);
  },

  clearResult() {
    const root = document.getElementById('status-result');
    if (!root) return;
    root.replaceChildren();
    root.hidden = true;
  },

  renderStatus(view) {
    const root = document.getElementById('status-result');
    if (!root) return;
    root.replaceChildren();
    if (!view.ok) {
      root.hidden = true;
      return;
    }

    const workerName = view.assignedProfile && view.assignedProfile.display_name;
    const statusText = typeof I18n === 'undefined'
      ? view.text
      : I18n.statusText(view.status, workerName);

    const badge = document.createElement('p');
    badge.className = 'track-status-badge';
    badge.textContent = statusText;

    const meta = document.createElement('p');
    meta.className = 'track-status-meta';
    meta.textContent = `${view.category ? `${view.category} · ` : ''}${this.text('track.needNumberTitle')}: ${view.reference}`;

    root.append(badge, meta);

    const accepted = view.status === 'assigned' || view.status === 'in_progress' || view.status === 'completed';
    const identity = view.workerIdentity || view.assignedProfile;
    if (accepted && identity && typeof WorkerIdentityCard !== 'undefined') {
      root.appendChild(WorkerIdentityCard.render(identity));
    } else if (accepted && view.assignedProfile && view.assignedProfile.display_name) {
      const worker = document.createElement('p');
      worker.className = 'track-status-meta';
      worker.textContent = `${this.text('track.providerLabel')}: ${view.assignedProfile.display_name}`;
      root.appendChild(worker);
    }

    if (view.canPayInspection) root.appendChild(this.inspectionPayForm(view));
    if (view.canPayExtras) root.appendChild(this.extrasPayForm(view));
    if (view.canExpand && view.expandToKm) {
      const expand = document.createElement('button');
      expand.type = 'button';
      expand.className = 'btn btn-outline btn-block action-gap';
      expand.textContent = typeof I18n === 'undefined'
        ? `Allow a ${view.expandToKm} km search`
        : I18n.fill('track.expand', { km: view.expandToKm });
      expand.addEventListener('click', () => this.expand(view, expand));
      root.appendChild(expand);
    }
    if (view.canVerifyArrival) root.appendChild(this.arrivalVerifyForm(view));
    if (view.canComplete) root.appendChild(this.completeForm(view));
    if (view.canCancel) {
      const cancel = document.createElement('button');
      cancel.type = 'button';
      cancel.className = 'btn btn-outline btn-block action-gap';
      cancel.textContent = this.text('track.cancel');
      cancel.addEventListener('click', () => this.cancel(view, cancel));
      root.appendChild(cancel);
    }

    root.hidden = false;
    this.lastView = view;
  },

  trackingKeys(reference) {
    return {
      reference: reference == null ? (this.lastView && this.lastView.reference) : reference,
      phone: this.phone,
    };
  },

  actionPayload(reference) {
    const keys = this.trackingKeys(reference);
    return GuestServiceLogic.statusPayload(keys.reference, '', keys.phone);
  },

  inspectionPayForm(view) {
    const panel = document.createElement('div');
    panel.className = 'arrival-panel';
    const amount = (view.payment && (view.payment.inspection_fee_inr || view.payment.payment_amount_inr)) || '99.00';
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('pay.inspectionHelp').split('{amount}').join(amount);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-primary btn-block';
    button.textContent = this.text('pay.inspection');
    button.addEventListener('click', () => {
      if (typeof MockCheckout === 'undefined') return;
      MockCheckout.open({
        title: this.text('pay.razorpayTitle'),
        amountInr: amount,
        note: this.text('guest.payNextBody'),
        onConfirm: async () => {
          const data = await ApiClient.post(
            GuestServiceLogic.GUEST_MOCK_PAYMENT_PATH,
            this.actionPayload(view.reference),
          );
          if (!data || data.money_received) throw new Error(this.text('pay.skipFailed'));
          this.show('status-notice', data.detail || this.text('pay.skipped'), 'success');
          await this.refreshSelected(view.reference);
        },
      });
    });
    panel.append(note, button);
    return panel;
  },

  extrasPayForm(view) {
    const panel = document.createElement('div');
    panel.className = 'arrival-panel';
    const amount = (view.payment && view.payment.extras_due_inr) || '0.00';
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('pay.extrasHelp').split('{amount}').join(amount);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-primary btn-block';
    button.textContent = this.text('pay.extras');
    button.addEventListener('click', () => {
      if (typeof MockCheckout === 'undefined') return;
      MockCheckout.open({
        title: this.text('pay.razorpayExtrasTitle'),
        amountInr: amount,
        note: this.text('pay.extrasNote'),
        onConfirm: async () => {
          const data = await ApiClient.post(
            GuestServiceLogic.GUEST_MOCK_EXTRA_PATH,
            this.actionPayload(view.reference),
          );
          if (!data || data.money_received) throw new Error(this.text('pay.skipFailed'));
          this.show('status-notice', data.detail || this.text('pay.extrasPaid'), 'success');
          await this.refreshSelected(view.reference);
        },
      });
    });
    panel.append(note, button);
    return panel;
  },

  async refreshSelected(reference) {
    const status = await ApiClient.post(
      GuestServiceLogic.STATUS_PATH,
      this.actionPayload(reference),
    );
    this.renderStatus(GuestServiceLogic.statusView(status));
    await this.loadByPhoneQuiet();
  },

  async loadByPhoneQuiet() {
    try {
      const data = await ApiClient.post(
        GuestServiceLogic.BY_PHONE_PATH,
        GuestServiceLogic.byPhonePayload(this.phone),
      );
      const list = GuestServiceLogic.trackListView(data);
      if (list.ok) {
        this.rows = list.rows;
        this.renderList(list.rows);
      }
    } catch (error) { /* keep current detail view */ }
  },

  arrivalVerifyForm(view) {
    const panel = document.createElement('form');
    panel.className = 'arrival-panel';
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('arrival.ownerNote');
    const input = document.createElement('input');
    input.className = 'form-input';
    input.inputMode = 'numeric';
    input.maxLength = 6;
    input.autocomplete = 'one-time-code';
    input.setAttribute('aria-label', this.text('arrival.codeInput'));
    const button = document.createElement('button');
    button.type = 'submit';
    button.className = 'btn btn-primary btn-block';
    button.textContent = this.text('arrival.verify');
    const notice = document.createElement('p');
    notice.setAttribute('role', 'status');
    panel.append(note, input, button, notice);
    panel.addEventListener('submit', (event) => this.verifyArrival(event, view, input, button, notice));
    return panel;
  },

  completeForm(view) {
    const panel = document.createElement('div');
    panel.className = 'arrival-panel';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-primary btn-block';
    button.textContent = this.text('arrival.complete');
    const notice = document.createElement('p');
    notice.setAttribute('role', 'status');
    button.addEventListener('click', () => this.completeVisit(view, button, notice));
    panel.append(button, notice);
    return panel;
  },

  async verifyArrival(event, view, input, button, notice) {
    event.preventDefault();
    const payload = GuestServiceLogic.arrivalVerifyPayload(view.reference, '', input.value, this.phone);
    if (!/^\d{6}$/.test(payload.code)) {
      notice.textContent = this.text('arrival.codeInvalid');
      return;
    }
    if (this.busy) return;
    this.setBusy(true);
    button.disabled = true;
    notice.textContent = this.text('arrival.verifying');
    try {
      const data = await ApiClient.post(GuestServiceLogic.ARRIVAL_VERIFY_PATH, payload);
      this.show('status-notice', data.detail || this.text('arrival.verified'), 'success');
      this.renderStatus(GuestServiceLogic.statusView(data));
    } catch (error) {
      notice.textContent = GuestServiceLogic.errorText(error);
      button.disabled = false;
    } finally {
      this.setBusy(false);
    }
  },

  async completeVisit(view, button, notice) {
    if (this.busy) return;
    this.setBusy(true);
    button.disabled = true;
    notice.textContent = this.text('arrival.completing');
    try {
      const data = await ApiClient.post(
        GuestServiceLogic.COMPLETE_PATH,
        GuestServiceLogic.completePayload(view.reference, '', this.phone),
      );
      this.show('status-notice', data.detail || this.text('arrival.completed'), 'success');
      this.renderStatus(GuestServiceLogic.statusView(data));
    } catch (error) {
      notice.textContent = GuestServiceLogic.errorText(error);
      button.disabled = false;
    } finally {
      this.setBusy(false);
    }
  },

  async expand(view, button) {
    if (this.busy) return;
    this.setBusy(true);
    button.disabled = true;
    try {
      const data = await ApiClient.post(
        GuestServiceLogic.EXPAND_PATH,
        GuestServiceLogic.expandPayload(view.reference, '', view.expandToKm, this.phone),
      );
      this.show('status-notice', data.detail || this.text('track.expanded'), 'success');
      await this.refreshSelected(view.reference);
    } catch (error) {
      this.show('status-notice', GuestServiceLogic.errorText(error), 'error');
      button.disabled = false;
    } finally {
      this.setBusy(false);
    }
  },

  async cancel(view, button) {
    if (this.busy) return;
    this.setBusy(true);
    button.disabled = true;
    try {
      const data = await ApiClient.post(
        GuestServiceLogic.CANCEL_PATH,
        GuestServiceLogic.cancelPayload(view.reference, '', this.phone),
      );
      this.show('status-notice', data.detail || this.text('track.cancelled'), 'success');
      this.renderStatus(GuestServiceLogic.statusView(Object.assign({}, view, data, {
        status: data.status || 'cancelled',
        can_expand: false,
        canCancel: false,
      })));
      await this.loadByPhoneQuiet();
    } catch (error) {
      this.show('status-notice', GuestServiceLogic.errorText(error), 'error');
      button.disabled = false;
    } finally {
      this.setBusy(false);
    }
  },
};

document.addEventListener('DOMContentLoaded', () => TrackRequestPage.init());
document.addEventListener('kaamdo:language', () => {
  TrackRequestPage.applyUserMode();
  if (TrackRequestPage.lastView) TrackRequestPage.renderStatus(TrackRequestPage.lastView);
});
