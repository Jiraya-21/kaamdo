/**
 * One equipment advertisement from the API.
 * A booking request and an inquiry use the existing endpoints.
 * Neither action collects money.
 */

const EquipmentDetails = {
  listingId: null,
  busy: false,

  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  init() {
    const params = new URLSearchParams(window.location.search);
    this.listingId = params.get('id');
    this.load();
  },

  root() {
    return document.getElementById('equipment-detail');
  },

  signedIn() {
    const token = StorageUtil.get(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    return typeof token === 'string' && token.trim() && token !== 'demo_token_authenticated';
  },

  async load() {
    const root = this.root();
    if (!root) return;
    if (!this.listingId) {
      root.textContent = this.text('equipDetail.missing');
      return;
    }
    root.textContent = this.text('equipDetail.loading');
    try {
      const listing = await ApiClient.get(EquipmentDetailsLogic.detailPath(this.listingId));
      this.render(listing);
    } catch (error) {
      root.textContent = error && error.status === 404
        ? this.text('equipDetail.unavailable')
        : this.text('equipDetail.failed');
    }
  },

  render(listing) {
    const root = this.root();
    root.replaceChildren();

    const photo = document.createElement('img');
    photo.className = 'listing-detail-photo';
    photo.src = typeof KaamdoImages !== 'undefined'
      ? KaamdoImages.equipmentPhoto(listing.photo_url)
      : '../../assets/images/placeholders/tractor-default.jpg';
    photo.alt = listing.title || '';
    photo.onerror = () => {
      photo.onerror = null;
      photo.src = '../../assets/images/placeholders/tractor-default.jpg';
    };

    const title = document.createElement('h1');
    title.style.fontSize = '1.85rem';
    title.textContent = listing.title;

    const place = document.createElement('p');
    place.className = 'text-muted';
    place.textContent = [listing.locality, listing.district].filter(Boolean).join(', ');

    const rate = document.createElement('p');
    const basisKeys = { hourly: 'list.hourly', daily: 'list.daily' };
    const basis = basisKeys[listing.pricing_basis]
      ? this.text(basisKeys[listing.pricing_basis])
      : (listing.pricing_basis || '');
    rate.textContent = this.text('list.rate', { amount: listing.rate, basis });

    const operator = document.createElement('p');
    operator.textContent = listing.operator_included
      ? this.text('list.operatorYes')
      : this.text('list.operatorNo');

    const availability = document.createElement('p');
    availability.textContent = listing.availability_note
      ? this.text('equipDetail.availability', { note: listing.availability_note })
      : '';

    const owner = document.createElement('p');
    owner.className = 'text-muted';
    owner.textContent = listing.owner_name ? this.text('equipDetail.listedBy', { name: listing.owner_name }) : '';

    const description = document.createElement('p');
    description.textContent = listing.description;

    root.append(photo, title, place, rate, operator, availability, owner, description);

    if (listing.status !== 'published') {
      const privateNote = document.createElement('p');
      privateNote.textContent = this.text('equipDetail.private');
      root.appendChild(privateNote);
    }
    if (listing.is_owner) {
      const own = document.createElement('p');
      own.textContent = this.text('equipDetail.own');
      root.appendChild(own);
      return;
    }

    root.appendChild(this.bookingForm());
    root.appendChild(this.inquiryForm());
  },

  field(labelText, control) {
    const group = document.createElement('div');
    group.className = 'form-group';
    const label = document.createElement('label');
    label.className = 'form-label';
    label.htmlFor = control.id;
    label.textContent = labelText;
    group.append(label, control);
    return group;
  },

  bookingForm() {
    const form = document.createElement('form');
    form.style.marginTop = '24px';
    const heading = document.createElement('h2');
    heading.textContent = this.text('equipDetail.bookTitle');
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('equipDetail.bookNote');
    const start = document.createElement('input');
    start.type = 'date';
    start.id = 'booking-start';
    start.className = 'form-input';
    start.required = true;
    const end = document.createElement('input');
    end.type = 'date';
    end.id = 'booking-end';
    end.className = 'form-input';
    end.required = true;
    const message = document.createElement('textarea');
    message.id = 'booking-note';
    message.className = 'form-textarea';
    message.maxLength = 1000;
    message.rows = 3;
    const button = document.createElement('button');
    button.type = 'submit';
    button.className = 'btn btn-primary';
    button.id = 'booking-submit';
    button.textContent = this.text('equipDetail.sendRequest');
    const status = document.createElement('p');
    status.id = 'booking-notice';
    status.setAttribute('role', 'status');
    form.append(
      heading,
      note,
      this.field(this.text('equipDetail.start'), start),
      this.field(this.text('equipDetail.end'), end),
      this.field(this.text('equipDetail.note'), message),
      status,
      button,
    );
    form.addEventListener('submit', (event) => this.submitBooking(event, button, status, start, end, message));
    return form;
  },

  inquiryForm() {
    const form = document.createElement('form');
    form.style.marginTop = '24px';
    const heading = document.createElement('h2');
    heading.textContent = this.text('equipDetail.askTitle');
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('equipDetail.askNote');
    const requirement = document.createElement('textarea');
    requirement.id = 'inquiry-requirement';
    requirement.className = 'form-textarea';
    requirement.maxLength = 1000;
    requirement.rows = 3;
    requirement.required = true;
    const timing = document.createElement('input');
    timing.type = 'text';
    timing.id = 'inquiry-timing';
    timing.className = 'form-input';
    timing.maxLength = 200;
    const button = document.createElement('button');
    button.type = 'submit';
    button.className = 'btn btn-outline';
    button.id = 'inquiry-submit';
    button.textContent = this.text('equipDetail.sendInquiry');
    const status = document.createElement('p');
    status.id = 'inquiry-notice';
    status.setAttribute('role', 'status');
    const otpWrap = document.createElement('div');
    otpWrap.id = 'inquiry-otp';
    otpWrap.hidden = true;
    const otpLead = document.createElement('p');
    otpLead.className = 'text-muted';
    otpLead.textContent = this.text('booking.otpLead');
    const code = document.createElement('input');
    code.type = 'text';
    code.id = 'inquiry-otp-code';
    code.className = 'form-input';
    code.inputMode = 'numeric';
    code.maxLength = 6;
    code.autocomplete = 'one-time-code';
    const dev = document.createElement('p');
    dev.id = 'inquiry-dev-code';
    dev.hidden = true;
    const verify = document.createElement('button');
    verify.type = 'button';
    verify.id = 'inquiry-otp-verify';
    verify.className = 'btn btn-primary';
    verify.textContent = this.text('booking.verify');
    const resend = document.createElement('button');
    resend.type = 'button';
    resend.id = 'inquiry-otp-resend';
    resend.className = 'btn btn-outline';
    resend.style.marginLeft = '8px';
    resend.textContent = this.text('booking.resend');
    otpWrap.append(
      otpLead,
      this.field(this.text('booking.needSix'), code),
      dev,
      verify,
      resend,
    );
    form.append(
      heading,
      note,
      this.field(this.text('equipDetail.need'), requirement),
      this.field(this.text('equipDetail.timing'), timing),
      status,
      otpWrap,
      button,
    );
    form.addEventListener('submit', (event) => {
      this.submitInquiry(event, button, status, requirement, timing, otpWrap, code, dev);
    });
    verify.addEventListener('click', () => {
      this.verifyInquiry(button, status, requirement, timing, otpWrap, code, dev);
    });
    resend.addEventListener('click', () => this.sendInquiryCode(status, otpWrap, dev));
    return form;
  },

  rememberLogin() {
    if (typeof AccountSession !== 'undefined') AccountSession.rememberReturnPath();
    window.location.href = '../auth/login.html';
  },

  accountPhone() {
    const user = StorageUtil.get(CONFIG.STORAGE_KEYS.USER_DATA);
    return user && typeof user.phone_number === 'string' ? user.phone_number.trim() : '';
  },

  async submitBooking(event, button, status, start, end, message) {
    event.preventDefault();
    if (this.busy) return;
    const values = { startDate: start.value, endDate: end.value, note: message.value };
    const problems = EquipmentDetailsLogic.bookingProblems(values);
    if (problems.length) {
      status.textContent = problems.join(' ');
      return;
    }
    if (!this.signedIn()) {
      this.rememberLogin();
      return;
    }
    await this.send(
      EquipmentDetailsLogic.bookingPath(this.listingId),
      EquipmentDetailsLogic.bookingPayload(values),
      EquipmentDetailsLogic.bookingResult,
      button,
      status,
    );
  },

  async submitInquiry(event, button, status, requirement, timing, otpWrap, code, dev) {
    event.preventDefault();
    if (this.busy) return;
    const values = { requirement: requirement.value, preferredTiming: timing.value };
    const problems = EquipmentDetailsLogic.inquiryProblems(values);
    if (problems.length) {
      status.textContent = problems.join(' ');
      return;
    }
    if (!this.signedIn()) {
      this.rememberLogin();
      return;
    }
    await this.send(
      EquipmentDetailsLogic.inquiryPath(this.listingId),
      EquipmentDetailsLogic.inquiryPayload(values),
      EquipmentDetailsLogic.inquiryResult,
      button,
      status,
      () => this.sendInquiryCode(status, otpWrap, dev),
    );
  },

  async sendInquiryCode(status, otpWrap, dev) {
    otpWrap.hidden = false;
    const phone = this.accountPhone();
    if (!phone) {
      status.textContent = this.text('booking.noPhone');
      return;
    }
    if (typeof AuthApi === 'undefined') {
      status.textContent = this.text('booking.noCode');
      return;
    }
    try {
      const sent = await AuthApi.sendOtp(phone, EquipmentDetailsLogic.INQUIRY_OTP_PURPOSE);
      const result = EquipmentDetailsLogic.otpSendResult(sent);
      if (!result.ok) {
        status.textContent = this.text(result.key || 'booking.noCode');
        return;
      }
      if (result.devCode) {
        dev.hidden = false;
        dev.textContent = this.text('booking.devCode', { code: result.devCode });
        status.textContent = this.text('booking.enterCode');
        return;
      }
      status.textContent = this.text(result.key || 'booking.smsSent');
    } catch (error) {
      status.textContent = AuthApi.formatError(error);
    }
  },

  async verifyInquiry(button, status, requirement, timing, otpWrap, code, dev) {
    if (this.busy) return;
    const digits = String(code.value || '').replace(/\D/g, '');
    if (!/^\d{6}$/.test(digits)) {
      status.textContent = this.text('booking.needSix');
      return;
    }
    const phone = this.accountPhone();
    if (!phone) {
      status.textContent = this.text('booking.noPhone');
      return;
    }
    this.busy = true;
    try {
      await AuthApi.verifyOtp(phone, EquipmentDetailsLogic.INQUIRY_OTP_PURPOSE, digits);
      otpWrap.hidden = true;
      dev.hidden = true;
      this.busy = false;
      await this.submitInquiry(
        { preventDefault() {} },
        button,
        status,
        requirement,
        timing,
        otpWrap,
        code,
        dev,
      );
    } catch (error) {
      status.textContent = AuthApi.formatError(error);
    } finally {
      this.busy = false;
    }
  },

  async send(path, payload, resultFor, button, status, onPhoneCheck) {
    this.busy = true;
    button.disabled = true;
    try {
      const data = await ApiClient.post(path, payload);
      status.textContent = resultFor(data).text;
    } catch (error) {
      if (error && error.status === 401) {
        this.rememberLogin();
        return;
      }
      if (typeof onPhoneCheck === 'function' && EquipmentDetailsLogic.needsPhoneCheck(error)) {
        await onPhoneCheck();
        return;
      }
      status.textContent = EquipmentDetailsLogic.errorText(error);
    } finally {
      this.busy = false;
      button.disabled = false;
    }
  },
};

document.addEventListener('DOMContentLoaded', () => EquipmentDetails.init());

document.addEventListener('kaamdo:language', () => EquipmentDetails.init());
