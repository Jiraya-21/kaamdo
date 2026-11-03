/**
 * Guest daily-service request wizard.
 * Tracking lives on a separate page. This file does not record a payment.
 */

const GuestServicePage = {
  busy: false,
  submitted: false,
  contactVerified: false,
  savedReference: '',
  savedAccessKey: '',
  lastOtpSentAt: 0,
  resendTimer: null,
  options: { email: false, phone: false, emailMode: 'unavailable', phoneMode: 'unavailable' },
  categoryRows: [],

  init() {
    sessionStorage.removeItem('kaamdo_guest_reference');
    sessionStorage.removeItem('kaamdo_guest_access_key');
    sessionStorage.removeItem('kaamdo_guest_phone');
    this.bind();
    this.showSignedInHint();
    this.loadOptions();
    this.loadCategories();
    this.loadPlaces();
    this.showStep('service');
  },

  bind() {
    document.querySelectorAll('input[name="verify-method"]').forEach((input) => {
      input.addEventListener('change', () => this.applyMethod());
    });
    document.getElementById('guest-details-form').addEventListener('submit', (event) => this.continueDetails(event));
    document.getElementById('guest-send-form').addEventListener('submit', (event) => this.sendCode(event));
    document.getElementById('guest-verify-form').addEventListener('submit', (event) => this.verifyCode(event));
    document.getElementById('guest-request-form').addEventListener('submit', (event) => this.createRequest(event));
    document.getElementById('details-back').addEventListener('click', () => this.showStep('service'));
    document.getElementById('review-back').addEventListener('click', () => this.showStep('details'));
    this.bindLocation();
    document.getElementById('copy-reference').addEventListener('click', () => {
      this.copyValue(this.savedReference, this.text('guest.copyRef'));
    });
    document.getElementById('copy-access-key').addEventListener('click', () => {
      this.copyValue(this.savedAccessKey, this.text('guest.copyAccess'));
    });
  },

  show(id, text, kind) {
    const notice = document.getElementById(id);
    if (!notice) return;
    notice.textContent = text || '';
    notice.classList.remove('is-error', 'is-success', 'is-info');
    if (text && kind) notice.classList.add(`is-${kind}`);
  },

  showStep(step) {
    const order = GuestServiceLogic.STEPS;
    const current = order.indexOf(step);
    const panels = [
      ['guest-service-section', 'service'],
      ['guest-details-section', 'details'],
      ['guest-review-section', 'review'],
    ];
    panels.forEach(([id, name]) => {
      const panel = document.getElementById(id);
      if (!panel) return;
      const on = step === name;
      panel.hidden = !on;
      panel.setAttribute('aria-hidden', on ? 'false' : 'true');
    });
    document.querySelectorAll('[data-guest-step]').forEach((item) => {
      const index = order.indexOf(item.dataset.guestStep);
      item.classList.toggle('is-done', index < current);
      item.classList.toggle('is-current', index === current);
    });
    const heading = {
      service: 'guest-catalogue-heading',
      details: 'guest-details-heading',
      review: 'guest-review-heading',
    }[step];
    const node = heading ? document.getElementById(heading) : null;
    if (node && typeof node.focus === 'function') {
      if (!node.hasAttribute('tabindex')) node.setAttribute('tabindex', '-1');
      node.focus();
    }
  },

  text(key) {
    return typeof I18n === 'undefined' ? key : I18n.t(key);
  },

  fill(key, values) {
    return typeof I18n === 'undefined' ? key : I18n.fill(key, values);
  },

  label(slug, name) {
    return typeof I18n === 'undefined' ? name : I18n.categoryLabel(slug, name);
  },

  isSignedIn() {
    if (typeof StorageUtil === 'undefined' || typeof CONFIG === 'undefined') return false;
    const token = StorageUtil.get(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    return typeof token === 'string' && token.trim() !== '' && token !== 'demo_token_authenticated';
  },

  async loadOptions() {
    try {
      const data = await ApiClient.get(GuestServiceLogic.OPTIONS_PATH);
      this.options = GuestServiceLogic.parseOptions(data);
    } catch (error) {
      this.options = GuestServiceLogic.parseOptions(null);
    }
    this.renderVerification();
  },

  async loadCategories() {
    const select = document.getElementById('request-category');
    this.show('catalogue-notice', this.text('guest.loading'), 'info');
    try {
      const page = await ApiClient.get(GuestServiceLogic.CATEGORY_PATH);
      const rows = page && page.results ? page.results : [];
      this.categoryRows = rows;
      rows.forEach((row) => {
        const option = document.createElement('option');
        option.value = String(row.id);
        option.dataset.slug = row.slug || '';
        option.dataset.fallback = row.name || '';
        option.textContent = this.label(row.slug, row.name);
        select.appendChild(option);
      });
      const params = new URLSearchParams(window.location.search);
      const chosen = GuestServiceLogic.categoryChoice(rows, {
        slug: params.get('category'),
        text: params.get('q'),
      });
      this.renderCatalogue(chosen);
      if (chosen) this.chooseCategory(chosen, { advance: false });
      if (!rows.length) this.show('catalogue-notice', this.text('guest.empty'), 'info');
      else this.show('catalogue-notice', '');
    } catch (error) {
      this.show('catalogue-notice', GuestServiceLogic.errorText(error), 'error');
    }
  },

  renderCatalogue(selectedId) {
    const grid = document.getElementById('service-catalogue');
    if (!grid) return;
    grid.replaceChildren();
    (this.categoryRows || []).forEach((row) => {
      const card = document.createElement('article');
      card.className = 'service-card';
      if (String(row.id) === String(selectedId)) card.classList.add('is-selected');
      const image = document.createElement('img');
      image.src = typeof KaamdoImages !== 'undefined'
        ? KaamdoImages.category(row.slug)
        : '../../assets/images/services/service.jpg';
      image.alt = this.label(row.slug, row.name);
      image.loading = 'lazy';
      const body = document.createElement('div');
      const title = document.createElement('h3');
      title.textContent = this.label(row.slug, row.name);
      const copy = document.createElement('p');
      copy.className = 'text-muted';
      copy.textContent = row.description || '';
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-primary';
      button.textContent = this.text('guest.chooseThis');
      button.addEventListener('click', () => this.chooseCategory(row.id));
      body.append(title, copy, button);
      card.append(image, body);
      grid.appendChild(card);
    });
  },

  chooseCategory(id, flags) {
    const select = document.getElementById('request-category');
    if (select) select.value = String(id);
    this.renderCatalogue(id);
    if (flags && flags.advance === false) return;
    this.showStep('details');
  },

  showSignedInHint() {
    const note = document.getElementById('guest-signed-in');
    if (!note) return;
    const signedIn = this.isSignedIn();
    note.hidden = !signedIn;
    if (!signedIn) {
      note.textContent = '';
      return;
    }
    note.innerHTML = '';
    const text = document.createTextNode(this.text('guest.signedIn') + ' ');
    const link = document.createElement('a');
    link.href = GuestServiceLogic.CUSTOMER_PAGE;
    link.textContent = this.text('guest.myRequests');
    note.append(text, link);
  },

  async loadPlaces() {
    if (typeof LocationFields === 'undefined') return;
    await LocationFields.enhanceByIds({
      state: 'request-state',
      district: 'request-district',
      taluk: 'request-taluk',
      locality: 'request-place',
    });
    this.bindLocation();
    if (typeof RadiusControl !== 'undefined') {
      RadiusControl.bind(
        document.getElementById('request-radius'),
        document.getElementById('request-radius-value'),
      );
    }
  },

  bindLocation() {
    if (typeof LocationDetect === 'undefined') return;
    LocationDetect.bind({
      button: document.getElementById('guest-locate'),
      status: document.getElementById('location-state'),
      mapHost: document.getElementById('guest-map-note'),
      fields: {
        state: document.getElementById('request-state'),
        district: document.getElementById('request-district'),
        taluk: document.getElementById('request-taluk'),
        locality: document.getElementById('request-place'),
        street: document.getElementById('request-street'),
        pin: document.getElementById('request-pin'),
        latitude: document.getElementById('request-latitude'),
        longitude: document.getElementById('request-longitude'),
      },
    });
  },

  requestValues() {
    return {
      guestName: document.getElementById('request-name').value,
      email: document.getElementById('request-email').value,
      phone: document.getElementById('request-phone').value,
      categoryId: document.getElementById('request-category').value,
      description: document.getElementById('request-description').value,
      state: document.getElementById('request-state') ? document.getElementById('request-state').value : '',
      district: document.getElementById('request-district') ? document.getElementById('request-district').value : '',
      taluk: document.getElementById('request-taluk') ? document.getElementById('request-taluk').value : '',
      place: document.getElementById('request-place').value,
      street: document.getElementById('request-street') ? document.getElementById('request-street').value : '',
      pin: document.getElementById('request-pin') ? document.getElementById('request-pin').value : '',
      latitude: document.getElementById('request-latitude').value,
      longitude: document.getElementById('request-longitude').value,
      radiusKm: document.getElementById('request-radius').value,
    };
  },

  continueDetails(event) {
    event.preventDefault();
    const values = this.requestValues();
    const issues = GuestServiceLogic.detailsProblems(values);
    if (issues.length) {
      this.show('details-notice', issues.join(' '), 'error');
      return;
    }
    this.show('details-notice', '');
    this.renderReview(values);
    this.showStep('review');
  },

  renderReview(values) {
    const root = document.getElementById('review-summary');
    if (!root) return;
    const select = document.getElementById('request-category');
    const option = select ? select.options[select.selectedIndex] : null;
    const categoryName = option ? option.textContent : values.categoryId;
    const rows = [
      [this.text('guest.category'), categoryName],
      [this.text('guest.name'), GuestServiceLogic.clean(values.guestName)],
      [this.text('guest.description'), GuestServiceLogic.workDescription(values.place, values.description)],
      [this.text('guest.place'), GuestServiceLogic.clean(values.place) || '—'],
      [this.text('guest.radius'), `${values.radiusKm} km`],
    ];
    root.replaceChildren();
    rows.forEach(([label, value]) => {
      const dt = document.createElement('dt');
      dt.textContent = label;
      const dd = document.createElement('dd');
      dd.textContent = value;
      root.append(dt, dd);
    });
  },

  renderVerification() {
    const usable = GuestServiceLogic.hasUsableVerification(this.options);
    const blocked = document.getElementById('guest-verify-blocked');
    const methods = document.getElementById('guest-methods');
    const sendForm = document.getElementById('guest-send-form');
    const verifyForm = document.getElementById('guest-verify-form');
    const submit = document.getElementById('request-submit');
    const modeNote = document.getElementById('verify-mode-note');
    const phoneLabel = document.getElementById('method-phone-label');
    const emailLabel = document.getElementById('method-email-label');
    const phoneRadio = phoneLabel ? phoneLabel.querySelector('input') : null;
    const emailRadio = emailLabel ? emailLabel.querySelector('input') : null;

    if (blocked) {
      blocked.hidden = usable;
      blocked.textContent = usable ? '' : this.text('guest.verifyBlocked');
    }
    if (submit) submit.disabled = !usable || this.submitted;
    if (methods) methods.hidden = !usable;
    if (sendForm) sendForm.hidden = !usable;
    if (verifyForm) verifyForm.hidden = !usable;
    if (phoneLabel) phoneLabel.hidden = !this.options.phone;
    if (emailLabel) emailLabel.hidden = !this.options.email;
    if (phoneRadio) phoneRadio.disabled = !this.options.phone;
    if (emailRadio) emailRadio.disabled = !this.options.email;

    const chosen = GuestServiceLogic.defaultMethod(this.options);
    if (chosen === 'phone' && phoneRadio) phoneRadio.checked = true;
    if (chosen === 'email' && emailRadio) emailRadio.checked = true;

    if (modeNote) {
      if (this.options.phone && !this.options.email) modeNote.textContent = this.text('guest.smsReady');
      else if (this.options.email && !this.options.phone) modeNote.textContent = this.text('guest.devOnly');
      else if (this.options.phone && this.options.email) modeNote.textContent = this.text('guest.smsOrDev');
      else modeNote.textContent = this.text('guest.noSms');
    }
    const sendButton = document.getElementById('guest-send-code');
    if (sendButton) {
      sendButton.textContent = this.options.phone && this.chosenMethod() === 'phone'
        ? this.text('guest.sendSms')
        : this.text('guest.sendCode');
    }
    this.applyMethod();
  },

  chosenMethod() {
    const chosen = document.querySelector('input[name="verify-method"]:checked');
    if (chosen && !chosen.disabled) return chosen.value;
    return GuestServiceLogic.defaultMethod(this.options);
  },

  applyMethod() {
    const method = this.chosenMethod();
    const fields = typeof OtpUi === 'undefined'
      ? { phone: method === 'phone', email: method !== 'phone' }
      : OtpUi.visibleFields(method || 'email');
    const showPhone = this.options.phone && fields.phone;
    const showEmail = this.options.email && fields.email;
    const phoneBox = document.getElementById('guest-phone-fields');
    const emailBox = document.getElementById('guest-email-fields');
    if (phoneBox) phoneBox.hidden = !showPhone;
    if (emailBox) emailBox.hidden = !showEmail;
    const sendButton = document.getElementById('guest-send-code');
    if (sendButton) {
      sendButton.textContent = showPhone ? this.text('guest.sendSms') : this.text('guest.sendCode');
    }
  },

  updateResendLabel() {
    const button = document.getElementById('guest-send-code');
    if (!button || typeof OtpUi === 'undefined') return;
    const left = OtpUi.secondsLeft(this.lastOtpSentAt, Date.now());
    if (left <= 0) {
      button.disabled = this.busy || !GuestServiceLogic.hasUsableVerification(this.options);
      this.applyMethod();
      return;
    }
    button.disabled = true;
    button.textContent = this.fill('otp.resendWait', { seconds: left });
  },

  startResendClock() {
    this.updateResendLabel();
    if (this.resendTimer) clearInterval(this.resendTimer);
    this.resendTimer = setInterval(() => {
      this.updateResendLabel();
      if (typeof OtpUi !== 'undefined' && OtpUi.canResend(this.lastOtpSentAt, Date.now())) {
        clearInterval(this.resendTimer);
        this.resendTimer = null;
      }
    }, 1000);
  },

  async sendCode(event) {
    event.preventDefault();
    if (this.busy) return;
    if (!GuestServiceLogic.hasUsableVerification(this.options)) {
      this.show('verify-notice', this.text('guest.verifyBlocked'), 'error');
      return;
    }
    if (typeof OtpUi !== 'undefined' && !OtpUi.canResend(this.lastOtpSentAt, Date.now())) {
      this.show('verify-notice', this.fill('otp.resendWait', {
        seconds: OtpUi.secondsLeft(this.lastOtpSentAt, Date.now()),
      }), 'error');
      return;
    }
    const method = this.chosenMethod();
    const email = document.getElementById('guest-email').value;
    const phone = document.getElementById('guest-phone').value;
    const problems = method === 'phone'
      ? GuestServiceLogic.phoneProblems(phone)
      : GuestServiceLogic.emailProblems(email);
    if (problems.length) {
      this.show('verify-notice', problems.join(' '), 'error');
      return;
    }
    this.busy = true;
    this.hideDevCode();
    this.show('verify-notice', this.text('guest.codeWait'), 'info');
    try {
      const sent = await ApiClient.post(
        GuestServiceLogic.SEND_PATH,
        GuestServiceLogic.sendPayload(method === 'phone' ? { phone } : { email }),
      );
      const result = GuestServiceLogic.sendResult(sent);
      this.lastOtpSentAt = Date.now();
      this.startResendClock();
      if (!result.ok) {
        this.show('verify-notice', this.text(result.key || 'guest.noCode'), 'error');
        return;
      }
      if (result.practice && result.devCode) {
        this.show('verify-notice', this.text('guest.devOnly'), 'info');
        this.showDevCode(result.devCode);
      } else {
        this.show('verify-notice', result.text, 'info');
      }
    } catch (error) {
      this.show('verify-notice', GuestServiceLogic.errorText(error), 'error');
    } finally {
      this.busy = false;
      this.updateResendLabel();
    }
  },

  showDevCode(code) {
    const note = document.getElementById('verify-dev-note');
    note.hidden = false;
    const template = typeof I18n === 'undefined'
      ? 'OTP sent to your mobile. Code: {code}'
      : I18n.t('guest.devCode');
    note.textContent = template.split('{code}').join(code);
  },

  hideDevCode() {
    const note = document.getElementById('verify-dev-note');
    note.hidden = true;
    note.textContent = '';
    const code = document.getElementById('guest-code');
    if (code) code.value = '';
  },

  async verifyCode(event) {
    event.preventDefault();
    if (this.busy) return;
    const method = this.chosenMethod();
    const email = document.getElementById('guest-email').value;
    const phone = document.getElementById('guest-phone').value;
    const code = document.getElementById('guest-code').value;
    const contactProblems = method === 'phone'
      ? GuestServiceLogic.phoneProblems(phone)
      : GuestServiceLogic.emailProblems(email);
    const problems = [
      ...contactProblems,
      ...GuestServiceLogic.codeProblems(code),
    ];
    if (problems.length) {
      this.show('verify-notice', problems.join(' '), 'error');
      return;
    }
    this.busy = true;
    this.show('verify-notice', this.text('guest.checking'), 'info');
    try {
      const verified = await ApiClient.post(
        GuestServiceLogic.VERIFY_PATH,
        GuestServiceLogic.verifyPayload(
          method === 'phone' ? { phone, code } : { email, code },
        ),
      );
      const result = GuestServiceLogic.verifyResult(verified);
      this.show('verify-notice', result.text, result.ok ? 'success' : 'error');
      if (result.ok) {
        this.contactVerified = true;
        this.fillVerifiedContact(method, phone, email);
        this.hideDevCode();
      }
    } catch (error) {
      this.show('verify-notice', GuestServiceLogic.errorText(error), 'error');
    } finally {
      this.busy = false;
    }
  },

  fillVerifiedContact(method, phone, email) {
    const emailWrap = document.getElementById('request-email-wrap');
    const phoneWrap = document.getElementById('request-phone-wrap');
    const emailInput = document.getElementById('request-email');
    const phoneInput = document.getElementById('request-phone');
    if (method === 'phone') {
      if (phoneInput) phoneInput.value = GuestServiceLogic.phone(phone);
      if (emailInput) emailInput.value = '';
      if (phoneWrap) phoneWrap.hidden = false;
      if (emailWrap) emailWrap.hidden = true;
      return;
    }
    if (emailInput) emailInput.value = GuestServiceLogic.email(email);
    if (phoneInput) phoneInput.value = '';
    if (emailWrap) emailWrap.hidden = false;
    if (phoneWrap) phoneWrap.hidden = true;
  },

  async locate() {
    const fields = {
      state: document.getElementById('request-state'),
      district: document.getElementById('request-district'),
      taluk: document.getElementById('request-taluk'),
      locality: document.getElementById('request-place'),
      street: document.getElementById('request-street'),
      pin: document.getElementById('request-pin'),
      latitude: document.getElementById('request-latitude'),
      longitude: document.getElementById('request-longitude'),
    };
    if (typeof LocationDetect !== 'undefined') {
      await LocationDetect.detect({
        status: document.getElementById('location-state'),
        mapHost: document.getElementById('guest-map-note'),
        fields,
      });
      return;
    }
    if (typeof GeolocationUtil === 'undefined') return;
    this.show('location-state', this.text('guest.locating'), 'info');
    try {
      const coords = await GeolocationUtil.getCurrentCoordinates();
      document.getElementById('request-latitude').value = GeolocationUtil.coordinateText(coords.latitude);
      document.getElementById('request-longitude').value = GeolocationUtil.coordinateText(coords.longitude);
      this.show('location-state', this.text('guest.located'), 'success');
    } catch (error) {
      this.show('location-state', this.text('guest.locationFailed'), 'error');
    }
  },

  async createRequest(event) {
    event.preventDefault();
    if (!GuestServiceLogic.canCreate(this)) {
      this.show('request-notice', this.text('guest.alreadySent'), 'info');
      return;
    }
    if (!GuestServiceLogic.hasUsableVerification(this.options) || !this.contactVerified) {
      this.show('request-notice', this.text('guest.needVerify'), 'error');
      return;
    }
    const values = this.requestValues();
    const problems = GuestServiceLogic.requestProblems(values);
    if (problems.length) {
      this.show('request-notice', problems.join(' '), 'error');
      return;
    }
    this.busy = true;
    const button = document.getElementById('request-submit');
    button.disabled = true;
    this.show('request-notice', this.text('guest.saving'), 'info');
    try {
      const saved = await ApiClient.post(
        GuestServiceLogic.CREATE_PATH,
        GuestServiceLogic.requestPayload(values),
      );
      const result = GuestServiceLogic.createResult(saved);
      if (!result.ok) {
        this.show('request-notice', this.text(result.key || 'guest.saveFailed'), 'error');
        return;
      }
      this.submitted = true;
      this.show('request-notice', '');
      this.showConfirmation(result);
    } catch (error) {
      this.show('request-notice', GuestServiceLogic.errorText(error), 'error');
    } finally {
      this.busy = false;
      button.disabled = this.submitted || !GuestServiceLogic.hasUsableVerification(this.options);
    }
  },

  showConfirmation(result) {
    this.savedReference = String(result.reference);
    this.savedAccessKey = String(result.accessKey || '');
    this.savedPayment = result.payment || null;
    document.getElementById('confirm-summary').textContent = this.text(result.key || 'guest.savedSummary');
    document.getElementById('confirm-reference').textContent = this.savedReference;
    document.getElementById('confirm-status').textContent = typeof I18n === 'undefined'
      ? GuestServiceLogic.statusSentence(result.status || 'awaiting_payment', '')
      : I18n.statusText(result.status || 'awaiting_payment', '');
    try {
      sessionStorage.setItem('kaamdo_guest_reference', this.savedReference);
      sessionStorage.setItem('kaamdo_guest_access_key', this.savedAccessKey);
      const phoneInput = document.getElementById('request-phone');
      const phone = GuestServiceLogic.phone(phoneInput ? phoneInput.value : '');
      if (phone) sessionStorage.setItem('kaamdo_guest_phone', phone);
    } catch (error) { /* ignore */ }
    const accessKeyNode = document.getElementById('confirm-access-key');
    if (accessKeyNode) {
      accessKeyNode.textContent = this.savedAccessKey;
      accessKeyNode.hidden = true;
    }
    const keyCopy = document.getElementById('confirm-key-copy');
    const copyKey = document.getElementById('copy-access-key');
    if (keyCopy) keyCopy.hidden = true;
    if (copyKey) copyKey.hidden = true;
    const track = document.getElementById('confirm-track-link');
    if (track) {
      const base = GuestServiceLogic.trackHref(this.savedReference);
      track.href = `${base}${base.includes('?') ? '&' : '?'}guest=1`;
    }
    this.mountConfirmPayment(result);
    document.getElementById('guest-request-form').hidden = true;
    document.getElementById('guest-verify-block').hidden = true;
    document.getElementById('request-confirmation').hidden = false;
    document.getElementById('confirm-notice').textContent = '';
    document.getElementById('review-back').hidden = true;
  },

  mountConfirmPayment(result) {
    const wrap = document.getElementById('confirm-pay-wrap');
    const feeLine = document.getElementById('confirm-fee-line');
    const button = document.getElementById('confirm-pay-fee');
    const payment = result.payment || {};
    const canPay = payment.can_pay_inspection === true && payment.mock_checkout === true;
    const amount = payment.inspection_fee_inr || payment.payment_amount_inr || '99.00';
    if (feeLine) {
      feeLine.hidden = false;
      feeLine.textContent = this.fill('pay.inspectionHelp', { amount });
    }
    if (wrap) wrap.hidden = !canPay;
    if (!button) return;
    button.onclick = () => {
      if (typeof MockCheckout === 'undefined') return;
      MockCheckout.open({
        title: this.text('pay.razorpayTitle'),
        amountInr: amount,
        note: this.text('guest.payNextBody'),
        onConfirm: async () => {
          const data = await ApiClient.post(GuestServiceLogic.GUEST_MOCK_PAYMENT_PATH, {
            reference: this.savedReference,
            access_key: this.savedAccessKey,
          });
          if (!data || data.money_received) throw new Error(this.text('pay.skipFailed'));
          document.getElementById('confirm-status').textContent = typeof I18n === 'undefined'
            ? GuestServiceLogic.statusSentence(data.status || 'offering', '')
            : I18n.statusText(data.status || 'offering', '');
          this.show(
            'confirm-notice',
            data.detail || this.text('pay.skipped'),
            'success',
          );
          if (wrap) wrap.hidden = true;
        },
      });
    };
  },

  async copyValue(value, label) {
    if (!value) {
      this.show('confirm-notice', this.fill('guest.noCopy', { label }), 'error');
      return;
    }
    if (!navigator.clipboard || typeof navigator.clipboard.writeText !== 'function') {
      this.show('confirm-notice', this.text('guest.copyFailed'), 'info');
      return;
    }
    try {
      await navigator.clipboard.writeText(value);
      this.show('confirm-notice', this.fill('guest.copied', { label }), 'success');
    } catch (error) {
      this.show('confirm-notice', this.text('guest.copyFailed'), 'info');
    }
  },
};

document.addEventListener('DOMContentLoaded', () => GuestServicePage.init());

document.addEventListener('kaamdo:language', () => {
  const select = document.getElementById('request-category');
  if (select && typeof I18n !== 'undefined') {
    Array.from(select.options).forEach((option) => {
      if (!option.value) return;
      option.textContent = I18n.categoryLabel(option.dataset.slug, option.dataset.fallback || option.textContent);
    });
  }
  GuestServicePage.renderCatalogue(select ? select.value : '');
  GuestServicePage.showSignedInHint();
  GuestServicePage.renderVerification();
});
