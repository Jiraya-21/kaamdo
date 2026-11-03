/**
 * Guest Daily Services messages and payloads.
 * This file does not call the network and does not record a payment.
 */

const GuestServiceLogic = {
  SEND_PATH: '/auth/otp/guest/send/',
  VERIFY_PATH: '/auth/otp/guest/verify/',
  OPTIONS_PATH: '/auth/otp/guest/options/',
  CATEGORY_PATH: '/workers/categories/',
  CREATE_PATH: '/workers/daily-requests/',
  STATUS_PATH: '/workers/daily-requests/status/',
  BY_PHONE_PATH: '/workers/daily-requests/by-phone/',
  EXPAND_PATH: '/workers/daily-requests/expand/',
  CANCEL_PATH: '/workers/daily-requests/cancel/',
  ARRIVAL_VERIFY_PATH: '/workers/daily-requests/arrival/verify/',
  COMPLETE_PATH: '/workers/daily-requests/complete/',
  TRACK_PAGE: 'track-request.html',
  CUSTOMER_PAGE: 'customer.html',
  STEPS: ['service', 'details', 'review'],

  parseOptions(data) {
    const emailOk = Boolean(
      data
      && data.email
      && data.email.available === true
      && data.email.mode === 'development',
    );
    const phoneMode = data && data.phone ? String(data.phone.mode || '') : '';
    const phoneOk = Boolean(
      data
      && data.phone
      && data.phone.available === true
      && (phoneMode === 'sms' || phoneMode === 'development'),
    );
    return {
      email: emailOk,
      phone: phoneOk,
      emailMode: emailOk ? 'development' : 'unavailable',
      phoneMode: phoneOk ? phoneMode : 'unavailable',
    };
  },

  hasUsableVerification(options) {
    return Boolean(options && (options.email || options.phone));
  },

  defaultMethod(options) {
    if (options && options.phone) return 'phone';
    if (options && options.email) return 'email';
    return '';
  },

  canCreate(state) {
    return Boolean(state) && state.busy !== true && state.submitted !== true;
  },

  trackHref(reference) {
    const page = this.TRACK_PAGE;
    const number = Number(reference);
    if (!Number.isInteger(number) || number <= 0) return page;
    return `${page}?reference=${number}`;
  },

  ignoreTrackingKeyInQuery(query) {
    const source = query && typeof query.get === 'function' ? query : null;
    if (!source) return { reference: '', accessKey: '' };
    const reference = String(source.get('reference') || '').trim();
    return { reference, accessKey: '' };
  },

  clean(value) {
    return String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
  },

  email(value) {
    return String(value == null ? '' : value).trim().toLowerCase();
  },

  phone(value) {
    return String(value == null ? '' : value).replace(/\D/g, '').replace(/^91(?=\d{10}$)/, '').slice(0, 10);
  },

  sendPayload(contact) {
    if (contact && contact.phone) {
      return { phone_number: this.phone(contact.phone), purpose: 'service_request' };
    }
    const email = typeof contact === 'string' ? contact : (contact && contact.email);
    return { email: this.email(email), purpose: 'service_request' };
  },

  verifyPayload(contact, code) {
    const otp = contact && Object.prototype.hasOwnProperty.call(contact, 'code')
      ? contact.code
      : code;
    const payload = {
      purpose: 'service_request',
      code: String(otp == null ? '' : otp).trim(),
    };
    if (contact && contact.phone) {
      payload.phone_number = this.phone(contact.phone);
      return payload;
    }
    const email = typeof contact === 'string' ? contact : (contact && contact.email);
    payload.email = this.email(email);
    return payload;
  },

  workDescription(place, description) {
    const placeName = this.clean(place);
    const work = this.clean(description);
    if (!placeName) return work;
    return `Place: ${placeName}. ${work}`;
  },

  coordinateText(value) {
    const text = this.clean(value);
    if (!text) return '';
    const number = Number(text);
    if (!Number.isFinite(number)) return text;
    return number.toFixed(6);
  },

  placeLine(values) {
    const place = values && values.place;
    if (typeof LocationFields !== 'undefined') {
      return LocationFields.placeLabel(values.street, place, values.taluk, values.district, values.pin);
    }
    return this.clean(place);
  },

  requestPayload(values) {
    const payload = {
      guest_name: this.clean(values.guestName),
      category: Number(values.categoryId),
      description: this.workDescription(this.placeLine(values), values.description),
      latitude: this.coordinateText(values.latitude),
      longitude: this.coordinateText(values.longitude),
      radius_km: Number(values.radiusKm),
    };
    const phone = this.phone(values && values.phone);
    if (phone) payload.contact_phone = phone;
    else payload.contact_email = this.email(values && values.email);
    return payload;
  },

  statusPayload(reference, accessKey, phone) {
    const payload = {
      reference: Number(String(reference).trim()),
    };
    const key = String(accessKey == null ? '' : accessKey).trim();
    const mobile = this.phone(phone);
    if (key) payload.access_key = key;
    if (mobile) payload.phone_number = mobile;
    return payload;
  },

  byPhonePayload(phone) {
    return { phone_number: this.phone(phone) };
  },

  trackPhoneProblems(phone) {
    return this.phoneProblems(phone);
  },

  trackListView(data) {
    if (!data || !Array.isArray(data.requests)) {
      return { ok: false, text: 'No requests were returned for this mobile number.', rows: [] };
    }
    return {
      ok: true,
      phone: this.phone(data.phone_number),
      count: Number(data.count || data.requests.length) || 0,
      rows: data.requests,
      text: data.detail || '',
    };
  },

  emailProblems(email) {
    const value = this.email(email);
    if (!value || !value.includes('@') || value.startsWith('@') || value.endsWith('@')) {
      return ['Enter the same email address used for the code.'];
    }
    return [];
  },

  phoneProblems(phone) {
    const value = this.phone(phone);
    if (!/^[6-9]\d{9}$/.test(value)) {
      return ['Enter a 10-digit mobile number starting with 6, 7, 8, or 9.'];
    }
    return [];
  },

  codeProblems(code) {
    const value = String(code == null ? '' : code).trim();
    if (!/^\d{6}$/.test(value)) return ['Enter the 6-digit code.'];
    return [];
  },

  detailsProblems(values) {
    return this.requestProblems({
      ...values,
      email: 'pending@example.com',
      phone: '',
    }).filter((item) => item !== 'Enter the same email address used for the code.');
  },

  requestProblems(values) {
    const problems = [];
    if (!this.clean(values.guestName)) problems.push('Enter your name.');
    const phone = this.phone(values.phone);
    const email = this.email(values.email);
    if (phone && email) problems.push('Choose a mobile number or an email address, not both.');
    else if (phone) problems.push(...this.phoneProblems(phone));
    else problems.push(...this.emailProblems(values.email));
    if (!Number.isInteger(Number(values.categoryId)) || Number(values.categoryId) <= 0) {
      problems.push('Choose a service category.');
    }
    const description = this.workDescription(values.place, values.description);
    if (!this.clean(values.description)) problems.push('Describe the work.');
    else if (description.length > 1000) problems.push('Keep the description to 1000 characters or fewer.');
    const latText = this.clean(values.latitude);
    const lngText = this.clean(values.longitude);
    const latitude = Number(latText);
    const longitude = Number(lngText);
    const locationReady = Boolean(latText) && Boolean(lngText)
      && Number.isFinite(latitude) && latitude >= -90 && latitude <= 90
      && Number.isFinite(longitude) && longitude >= -180 && longitude <= 180;
    if (Object.hasOwn(values, 'district') && !this.clean(values.district)) {
      problems.push('Choose an official district.');
    }
    if (Object.hasOwn(values, 'taluk') && !this.clean(values.taluk) && this.clean(values.district) !== 'Mumbai City') {
      problems.push('Choose an official taluk.');
    }
    if (!locationReady) {
      problems.push('Use this phone location so KaamDo can find a nearby worker. A place name alone does not find a worker.');
    }
    const radius = Number(values.radiusKm);
    if (!Number.isInteger(radius) || radius < 5 || radius > 100 || radius % 5 !== 0) {
      problems.push('Choose a radius from 5 to 100 kilometres.');
    }
    return problems;
  },

  statusProblems(reference, accessKey) {
    const problems = [];
    const number = Number(String(reference == null ? '' : reference).trim());
    if (!Number.isInteger(number) || number <= 0) problems.push('Enter the request number.');
    if (!String(accessKey == null ? '' : accessKey).trim()) {
      problems.push('Enter the tracking key shown when the request was saved.');
    }
    return problems;
  },

  expandPayload(reference, accessKey, radiusKm, phone) {
    const payload = {
      reference: Number(reference),
      radius_km: Number(radiusKm),
    };
    const key = String(accessKey || '').trim();
    const mobile = this.phone(phone);
    if (key) payload.access_key = key;
    if (mobile) payload.phone_number = mobile;
    return payload;
  },

  cancelPayload(reference, accessKey, phone) {
    return this.statusPayload(reference, accessKey, phone);
  },

  sendResult(data) {
    const sentText = 'OTP sent to your mobile.';
    if (data && data.delivery === 'sms' && !data.dev_code) {
      return {
        ok: true,
        key: 'guest.codeSent',
        devCode: '',
        practice: false,
        text: data.detail || sentText,
      };
    }
    if (data && data.delivery === 'development' && data.dev_code) {
      return {
        ok: true,
        key: 'guest.codeSent',
        devCode: String(data.dev_code),
        practice: false,
        text: data.detail || sentText,
      };
    }
    return {
      ok: false,
      key: 'guest.noCode',
      text: 'No code was sent. Try again.',
    };
  },

  verifyResult(data) {
    if (!data || typeof data.detail !== 'string') {
      return { ok: false, text: 'The contact was not confirmed.' };
    }
    return { ok: true, text: data.detail };
  },

  createResult(data) {
    if (!data || !data.reference || !data.access_key) {
      return {
        ok: false,
        key: 'guest.saveFailed',
        text: 'The request was not confirmed. It was not shown as saved.',
      };
    }
    return {
      ok: true,
      key: 'guest.savedSummary',
      reference: data.reference,
      accessKey: String(data.access_key),
      status: data.status || 'awaiting_payment',
      payment: data.payment || null,
      nextStep: data.next_step || 'pay_inspection_fee',
      text: 'Mobile checked. Pay the inspection fee next. Workers are offered only after that fee.',
    };
  },

  GUEST_MOCK_PAYMENT_PATH: '/workers/daily-requests/mock-payment/',

  categoryChoice(categories, query) {
    const rows = Array.isArray(categories) ? categories : [];
    const slug = String(query && query.slug ? query.slug : '').trim().toLowerCase();
    const text = String(query && query.text ? query.text : '').trim().toLowerCase();
    if (slug) {
      const bySlug = rows.find((row) => String(row && row.slug ? row.slug : '').toLowerCase() === slug);
      if (bySlug) return String(bySlug.id);
    }
    if (text) {
      const byText = rows.find((row) => {
        const name = String(row && row.name ? row.name : '').toLowerCase();
        const rowSlug = String(row && row.slug ? row.slug : '').toLowerCase();
        return name === text || rowSlug === text || name.includes(text) || rowSlug.includes(text);
      });
      if (byText) return String(byText.id);
    }
    return '';
  },

  statusSentence(status, workerName) {
    const name = workerName ? String(workerName) : '';
    const sentences = {
      draft: 'Saved. Verify mobile, then pay the inspection fee. No worker yet.',
      awaiting_payment: 'Mobile checked. Pay the inspection fee. No worker is offered yet.',
      dispatch_pending: 'Inspection fee recorded. Ready to offer to workers. No worker has accepted yet.',
      no_workers: 'No eligible worker is in range. No worker is assigned.',
      offering: 'Offered to eligible workers. No worker has accepted yet.',
      assigned: name ? `A worker accepted: ${name}.` : 'A worker accepted.',
      worker_cancelled: 'The assigned worker cancelled before the visit. This is not a new assignment.',
      no_acceptance: 'No worker accepted.',
      in_progress: name ? `Service in progress with ${name}.` : 'Service in progress.',
      completed: name ? `Completed with ${name}.` : 'Completed.',
      cancelled: 'Cancelled. No worker is assigned.',
      refund_requested: 'A refund was requested. This is not a new assignment.',
    };
    return sentences[status] || 'The status was returned. No assignment was added by this page.';
  },

  reasonSentence(reason) {
    const sentences = {
      needs_radius_consent: 'No eligible worker is inside your chosen radius. You can allow a wider search. A farther worker may take longer. This page does not add a travel fee or promise an arrival time.',
      no_eligible: 'No eligible worker is in range. No worker is assigned.',
      no_response: 'Workers were offered this request. None accepted in time.',
      all_declined: 'Workers were offered this request. All declined.',
      pool_exhausted: 'No more eligible workers remain. No worker is assigned.',
      rounds_exhausted: 'Matching stopped after the allowed number of attempts. No worker is assigned.',
      unusable_location: 'This request cannot be matched because the location is not usable.',
    };
    return sentences[reason] || '';
  },

  arrivalVerifyPayload(reference, accessKey, code, phone) {
    const payload = this.statusPayload(reference, accessKey, phone);
    payload.code = String(code == null ? '' : code).replace(/\s+/g, '');
    return payload;
  },

  completePayload(reference, accessKey, phone) {
    return this.statusPayload(reference, accessKey, phone);
  },

  publicWorker(data) {
    const primary = data && data.worker_identity && typeof data.worker_identity === 'object'
      ? data.worker_identity
      : null;
    const extra = data && data.assigned_profile && typeof data.assigned_profile === 'object'
      ? data.assigned_profile
      : null;
    const card = primary || extra;
    if (!card) return null;
    const photo = String(card.photo_url || '').trim();
    const skills = Array.isArray(card.skills) && card.skills.length
      ? card.skills
      : (extra && Array.isArray(extra.skills) ? extra.skills : []);
    return {
      id: card.profile_id != null ? card.profile_id : card.id,
      worker_id: card.worker_id ? String(card.worker_id) : '',
      display_name: card.display_name || (extra && extra.display_name) || '',
      photo_url: /^https?:\/\//i.test(photo) ? photo : '',
      main_category: card.main_category ? String(card.main_category) : '',
      skills: skills.map(String),
      district: card.district || (extra && extra.district) || '',
      locality: card.locality || (extra && extra.locality) || '',
      identity_verified: card.identity_verified === true,
      identity_verification: card.identity_verification ? String(card.identity_verification) : '',
    };
  },

  statusView(data) {
    if (!data || data.reference == null || !data.status) {
      return { ok: false, text: 'The request status was not confirmed.' };
    }
    const card = this.publicWorker(data);
    const reasonText = this.reasonSentence(data.match_reason);
    const statusText = reasonText || this.statusSentence(data.status, card && card.display_name);
    return {
      ok: true,
      reference: data.reference,
      category: data.category ? String(data.category) : '',
      description: data.description ? String(data.description) : '',
      status: data.status,
      radiusKm: data.radius_km,
      searchRadiusKm: data.search_radius_km,
      matchReason: data.match_reason ? String(data.match_reason) : '',
      canExpand: data.can_expand === true,
      expandToKm: data.expand_to_km == null ? null : Number(data.expand_to_km),
      canCancel: data.status === 'draft'
        || data.status === 'awaiting_payment'
        || data.status === 'dispatch_pending'
        || data.status === 'offering'
        || data.status === 'no_workers'
        || data.status === 'no_acceptance'
        || data.status === 'assigned',
      assignedProfile: card,
      workerIdentity: card,
      arrivalVerifiedAt: data.arrival_verified_at ? String(data.arrival_verified_at) : '',
      canVerifyArrival: data.status === 'assigned',
      canComplete: data.status === 'in_progress' && Boolean(data.arrival_verified_at),
      payment: data.payment || null,
      canPayInspection: Boolean(data.payment && data.payment.can_pay_inspection && data.payment.mock_checkout),
      canPayExtras: Boolean(data.payment && data.payment.can_pay_extras && data.payment.mock_checkout),
      text: `Reference ${data.reference}. ${statusText}`,
    };
  },

  GUEST_MOCK_EXTRA_PATH: '/workers/daily-requests/mock-extra-payment/',

  errorText(error) {
    if (!error || typeof error.status !== 'number') {
      return 'The server could not be reached. Nothing was saved.';
    }
    const data = error.data;
    if (data && typeof data.detail === 'string') return data.detail;
    if (data && Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
      return data.non_field_errors.join(' ');
    }
    if (data && typeof data === 'object') {
      const parts = Object.entries(data).map(([, value]) => (
        Array.isArray(value) ? value.join(' ') : String(value)
      )).filter((part) => part && part !== '[object Object]');
      if (parts.length) return parts.join(' ');
    }
    if (error.status === 404) return 'That request was not found. Check the number and secret code.';
    if (error.status === 401) return 'Please sign in and try again.';
    if (error.status >= 500) return 'The server had a problem. Try again in a moment.';
    return 'Something went wrong. Check the details and try again.';
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = GuestServiceLogic;
}
