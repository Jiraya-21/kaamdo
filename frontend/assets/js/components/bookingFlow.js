/**
 * Direct request to one published provider.
 * This is not a Daily Services category match and does not assign the provider.
 * The server stores the request. This screen does not collect a fee or a payment.
 */

const BookingFlow = {
  worker: null,
  user: null,
  submitting: false,

  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  init() {
    if (typeof StorageUtil !== 'undefined') {
      StorageUtil.remove('kaamdo_guest_booking');
    }
    this.createModalDOM();
    this.bindEvents();
    this.applyLanguage();
  },

  createModalDOM() {
    if (document.getElementById('booking-modal-overlay')) return;

    const modalHTML = `
      <div id="booking-modal-overlay" class="modal-overlay">
        <div class="modal-card">
          <button id="modal-close-btn" class="modal-close-btn" data-i18n-aria="booking.close" aria-label="Close">&times;</button>
          <h3 id="booking-title" style="font-size:1.25rem; font-weight:700; margin-bottom:8px;"></h3>
          <p id="booking-intro" class="text-muted" style="font-size:0.875rem; margin-bottom:12px;" data-i18n="booking.intro">
            This asks one published provider. It is not a category offer, and the provider is not assigned by sending it. This screen does not collect a payment.
          </p>
          <div id="booking-message" style="display:none; border-radius:8px; padding:12px; font-size:0.9rem; margin-bottom:12px;"></div>

          <form id="service-request-form" style="display:none;">
            <div class="form-group">
              <label class="form-label" for="request-description" data-i18n="booking.work">What needs to be done?</label>
              <textarea id="request-description" class="form-textarea" rows="4" maxlength="1000" required data-i18n-placeholder="booking.workPlaceholder" placeholder="Describe the problem. Do not include a price."></textarea>
            </div>
            <button id="request-submit-btn" type="submit" class="btn btn-primary btn-block" data-i18n="booking.send">Send request</button>
          </form>

          <div id="request-otp-pane" style="display:none;">
            <p class="text-muted" style="font-size:0.875rem;" data-i18n="booking.otpLead">Enter the 6-digit code for the mobile number on your account. A code appears here only for local practice delivery.</p>
            <p id="request-dev-code" style="display:none; background:#FEF3C7; border:1px dashed #D97706; border-radius:8px; padding:10px; margin:12px 0; font-size:0.85rem; color:#92400E;"></p>
            <input id="request-otp-code" class="form-input" inputmode="numeric" maxlength="6" autocomplete="one-time-code" data-i18n-placeholder="guest.code" placeholder="6-digit code">
            <button id="request-otp-verify" type="button" class="btn btn-primary btn-block" style="margin-top:12px;" data-i18n="booking.verify">Check code and send request</button>
            <button id="request-otp-resend" type="button" class="btn btn-outline btn-block" style="margin-top:8px;" data-i18n="booking.resend">Ask for another practice code</button>
          </div>

          <div id="request-success-pane" style="display:none;">
            <p style="font-weight:700; margin-bottom:8px;" data-i18n="booking.success">The server saved your request to this provider. That is not an assignment.</p>
            <p><span data-i18n="booking.status">Status</span>: <strong id="request-status-label"></strong></p>
            <button id="request-success-close" type="button" class="btn btn-primary btn-block" style="margin-top:16px;" data-i18n="booking.close">Close</button>
          </div>

          <a id="request-login-link" class="btn btn-primary btn-block" style="display:none;" href="pages/auth/login.html" data-i18n="booking.signIn">Sign in to send a request</a>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
  },

  applyLanguage() {
    const overlay = document.getElementById('booking-modal-overlay');
    if (overlay && typeof I18n !== 'undefined') I18n.apply(overlay);
    this.setTitle();
  },

  setTitle() {
    const nameEl = document.getElementById('booking-title');
    if (!nameEl) return;
    const name = this.worker && (this.worker.name || this.worker.display_name)
      ? (this.worker.name || this.worker.display_name)
      : this.text('booking.thisProvider');
    nameEl.textContent = this.text('booking.title', { name });
  },

  openBooking(worker) {
    this.worker = worker || null;
    this.user = null;
    this.submitting = false;
    if (typeof StorageUtil !== 'undefined') {
      StorageUtil.remove('kaamdo_guest_booking');
    }
    this.applyLanguage();
    this.showPane('checking');
    const overlay = document.getElementById('booking-modal-overlay');
    if (overlay) overlay.classList.add('active');
    this.prepare();
  },

  async prepare() {
    const workerId = this.worker && this.worker.id;
    if (!/^\d+$/.test(String(workerId || ''))) {
      this.showMessage(this.text('booking.invalidListing'), 'warn');
      this.showPane('message');
      return;
    }
    const token = typeof StorageUtil !== 'undefined'
      ? StorageUtil.get(CONFIG.STORAGE_KEYS.AUTH_TOKEN)
      : null;
    if (typeof token !== 'string' || !token.trim()) {
      this.showSignedOut();
      return;
    }
    try {
      this.user = await AuthApi.getCurrentUser();
    } catch (error) {
      if (error && (error.status === 401 || error.status === 403)) {
        this.showSignedOut();
        return;
      }
      this.showMessage(this.text('booking.offline'), 'error');
      this.showPane('message');
      return;
    }
    const capabilities = this.user && Array.isArray(this.user.capabilities) ? this.user.capabilities : [];
    if (!capabilities.includes('customer')) {
      this.showMessage(this.text('booking.needCustomer'), 'warn');
      this.showPane('message');
      return;
    }
    this.showPane('form');
  },

  showSignedOut() {
    this.showMessage(this.text('booking.signedOut'), 'warn');
    const link = document.getElementById('request-login-link');
    if (link) {
      link.style.display = 'block';
      link.href = this.loginHref();
    }
    this.showPane('signedout');
  },

  loginHref() {
    const path = window.location.pathname || '';
    if (path.includes('/pages/')) {
      const after = path.split('/pages/')[1] || '';
      const depth = Math.max(after.split('/').length - 1, 0);
      return `${'../'.repeat(depth)}auth/login.html`;
    }
    return 'pages/auth/login.html';
  },

  showPane(mode) {
    const form = document.getElementById('service-request-form');
    const otp = document.getElementById('request-otp-pane');
    const success = document.getElementById('request-success-pane');
    const link = document.getElementById('request-login-link');
    if (form) form.style.display = mode === 'form' ? 'block' : 'none';
    if (otp) otp.style.display = mode === 'otp' ? 'block' : 'none';
    if (success) success.style.display = mode === 'success' ? 'block' : 'none';
    if (link && mode !== 'signedout') link.style.display = 'none';
  },

  showMessage(text, kind) {
    const box = document.getElementById('booking-message');
    if (!box) return;
    box.style.display = 'block';
    box.textContent = text;
    if (kind === 'error') {
      box.style.background = '#FEF2F2';
      box.style.color = '#991B1B';
      box.style.border = '1px solid #FECACA';
    } else if (kind === 'ok') {
      box.style.background = '#F0FDF4';
      box.style.color = '#166534';
      box.style.border = '1px solid #BBF7D0';
    } else {
      box.style.background = '#FFFBEB';
      box.style.color = '#92400E';
      box.style.border = '1px solid #FDE68A';
    }
  },

  clearMessage() {
    const box = document.getElementById('booking-message');
    if (box) {
      box.style.display = 'none';
      box.textContent = '';
    }
  },

  closeModal() {
    const overlay = document.getElementById('booking-modal-overlay');
    if (overlay) overlay.classList.remove('active');
    const description = document.getElementById('request-description');
    const code = document.getElementById('request-otp-code');
    const dev = document.getElementById('request-dev-code');
    if (description) description.value = '';
    if (code) code.value = '';
    if (dev) {
      dev.style.display = 'none';
      dev.textContent = '';
    }
    this.submitting = false;
    this.clearMessage();
  },

  needsPhoneCheck(error) {
    const text = AuthApi.formatError(error).toLowerCase();
    return text.includes('verify your mobile');
  },

  async sendCode() {
    this.clearMessage();
    const phone = this.user && this.user.phone_number;
    if (!phone) {
      this.showMessage(this.text('booking.noPhone'), 'error');
      return;
    }
    const button = document.getElementById('request-otp-resend');
    if (button) button.disabled = true;
    const dev = document.getElementById('request-dev-code');
    if (dev) {
      dev.style.display = 'none';
      dev.textContent = '';
    }
    try {
      const sent = await AuthApi.sendOtp(phone, 'service_request');
      const result = BookingFlowLogic.sendResult(sent);
      if (!result.ok) {
        this.showMessage(this.text(result.key || 'booking.noCode'), 'error');
        return;
      }
      if (result.devCode && dev) {
        dev.style.display = 'block';
        dev.textContent = this.text('booking.devCode', { code: result.devCode });
        this.showMessage(this.text('booking.enterCode'), 'warn');
        return;
      }
      this.showMessage(this.text(result.key || 'booking.smsSent'), 'warn');
    } catch (error) {
      this.showMessage(AuthApi.formatError(error), 'error');
    } finally {
      if (button) button.disabled = false;
    }
  },

  async submitRequest() {
    if (this.submitting) return;
    const descriptionEl = document.getElementById('request-description');
    const description = descriptionEl ? descriptionEl.value.trim() : '';
    if (!description) {
      this.showMessage(this.text('booking.describe'), 'error');
      return;
    }
    this.submitting = true;
    const button = document.getElementById('request-submit-btn');
    if (button) {
      button.disabled = true;
      button.textContent = this.text('booking.sending');
    }
    this.clearMessage();
    try {
      const saved = await ApiClient.post(BookingFlowLogic.REQUEST_PATH, {
        profile: Number(this.worker.id),
        description,
      });
      const statusEl = document.getElementById('request-status-label');
      if (statusEl) statusEl.textContent = saved && saved.status ? saved.status : 'requested';
      this.clearMessage();
      this.showPane('success');
    } catch (error) {
      if (this.needsPhoneCheck(error)) {
        this.showPane('otp');
        await this.sendCode();
      } else {
        this.showMessage(AuthApi.formatError(error), 'error');
      }
    } finally {
      this.submitting = false;
      if (button) {
        button.disabled = false;
        button.textContent = this.text('booking.send');
      }
    }
  },

  async verifyAndSend() {
    if (this.submitting) return;
    const codeEl = document.getElementById('request-otp-code');
    const code = codeEl ? codeEl.value.trim() : '';
    const phone = this.user && this.user.phone_number;
    if (!/^\d{6}$/.test(code)) {
      this.showMessage(this.text('booking.needSix'), 'error');
      return;
    }
    this.submitting = true;
    const button = document.getElementById('request-otp-verify');
    if (button) button.disabled = true;
    try {
      await AuthApi.verifyOtp(phone, 'service_request', code);
      const dev = document.getElementById('request-dev-code');
      if (dev) {
        dev.style.display = 'none';
        dev.textContent = '';
      }
      this.showPane('form');
      this.submitting = false;
      await this.submitRequest();
    } catch (error) {
      this.showMessage(AuthApi.formatError(error), 'error');
      this.submitting = false;
    } finally {
      if (button) button.disabled = false;
    }
  },

  bindEvents() {
    const closeBtn = document.getElementById('modal-close-btn');
    const successClose = document.getElementById('request-success-close');
    const form = document.getElementById('service-request-form');
    const verifyBtn = document.getElementById('request-otp-verify');
    const resendBtn = document.getElementById('request-otp-resend');
    const loginLink = document.getElementById('request-login-link');
    if (closeBtn) closeBtn.addEventListener('click', () => this.closeModal());
    if (successClose) successClose.addEventListener('click', () => this.closeModal());
    if (form) {
      form.addEventListener('submit', (event) => {
        event.preventDefault();
        this.submitRequest();
      });
    }
    if (verifyBtn) verifyBtn.addEventListener('click', () => this.verifyAndSend());
    if (resendBtn) resendBtn.addEventListener('click', () => this.sendCode());
    if (loginLink) {
      loginLink.addEventListener('click', () => {
        try {
          sessionStorage.setItem('kaamdo_after_login', `${window.location.pathname}${window.location.search}`);
        } catch (error) {
          /* The login page can still open without a return path. */
        }
      });
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  BookingFlow.init();
});

document.addEventListener('kaamdo:language', () => {
  if (typeof BookingFlow !== 'undefined') BookingFlow.applyLanguage();
});
