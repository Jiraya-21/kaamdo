/**
 * Customer daily requests and worker offer decisions.
 * These functions do not call the network and do not record a payment.
 */

const DailyAccountLogic = {
  REQUESTS_PATH: '/workers/daily-requests/mine/',
  CATEGORY_PATH: '/workers/categories/',
  OFFERS_PATH: '/workers/daily-offers/mine/',

  respondPath(id) {
    return `/workers/daily-offers/${id}/respond/`;
  },

  mockPaymentPath(reference) {
    return `/workers/daily-requests/${reference}/mock-payment/`;
  },

  extraPaymentPath(reference) {
    return `/workers/daily-requests/${reference}/mock-extra-payment/`;
  },

  extrasPath(reference) {
    return `/workers/daily-requests/${reference}/extras/`;
  },

  priceMenuPath() {
    return '/workers/price-menu/';
  },

  canSkipPayment(status) {
    return status === 'draft' || status === 'awaiting_payment';
  },

  canPayInspection(row) {
    const payment = row && row.payment;
    return Boolean(payment && payment.can_pay_inspection && payment.mock_checkout);
  },

  canPayExtras(row) {
    const payment = row && row.payment;
    return Boolean(payment && payment.can_pay_extras && payment.mock_checkout);
  },

  testPaymentEnabled(user) {
    return Boolean(
      user
      && user.test_payment
      && user.test_payment.enabled === true
      && user.test_payment.money_received === false
    );
  },

  clean(value) {
    return String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
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

  requestPayload(values) {
    const place = typeof LocationFields === 'undefined'
      ? this.clean(values.place)
      : LocationFields.placeLabel(values.street, values.place, values.taluk, values.district, values.pin);
    const payload = {
      category: Number(values.categoryId),
      description: this.workDescription(place, values.description),
      latitude: this.coordinateText(values.latitude),
      longitude: this.coordinateText(values.longitude),
    };
    if (this.clean(values.radiusKm)) payload.radius_km = Number(values.radiusKm);
    return payload;
  },

  requestProblems(values) {
    const problems = [];
    if (!Number.isInteger(Number(values.categoryId)) || Number(values.categoryId) <= 0) {
      problems.push('Choose a service category.');
    }
    const work = this.clean(values.description);
    const description = this.workDescription(values.place, values.description);
    if (!work) problems.push('Describe the work.');
    else if (description.length > 1000) problems.push('Keep the description to 1000 characters or fewer.');
    const latText = this.clean(values.latitude);
    const lngText = this.clean(values.longitude);
    const latitude = Number(latText);
    const longitude = Number(lngText);
    const locationReady = Boolean(latText) && Boolean(lngText)
      && Number.isFinite(latitude) && latitude >= -90 && latitude <= 90
      && Number.isFinite(longitude) && longitude >= -180 && longitude <= 180;
    if (!locationReady) {
      problems.push('Use this phone location before saving. A place name is kept with the request, but it does not find a worker by itself.');
    }
    if (this.clean(values.radiusKm)) {
      const radius = Number(values.radiusKm);
      if (!Number.isInteger(radius) || radius < 5 || radius > 100 || radius % 5 !== 0) {
        problems.push('Choose a radius from 5 to 100 kilometres.');
      }
    }
    return problems;
  },

  createResult(data) {
    const status = data && data.status;
    if (!data || data.reference == null || (status !== 'awaiting_payment' && status !== 'draft')) {
      return { ok: false, text: 'The request was not confirmed. No worker was assigned.' };
    }
    if (Object.hasOwn(data, 'access_key') || Object.hasOwn(data, 'assigned_profile')) {
      return { ok: false, text: 'The response included a field this save does not confirm.' };
    }
    return {
      ok: true,
      reference: data.reference,
      status,
      payment: data.payment || null,
      nextStep: data.next_step || 'pay_inspection_fee',
      text: 'Request saved. Pay the inspection fee next. Workers are offered only after that fee.',
    };
  },

  statusSentence(status, workerName) {
    const name = workerName ? String(workerName) : '';
    const sentences = {
      draft: 'Saved. Verify, then pay the inspection fee. No worker yet.',
      awaiting_payment: 'Pay the inspection fee. No worker is offered yet.',
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
    };
    return sentences[reason] || '';
  },

  expandPath(reference) {
    return `/workers/daily-requests/${reference}/expand/`;
  },

  cancelPath(reference) {
    return `/workers/daily-requests/${reference}/cancel/`;
  },

  arrivalSignalPath(reference) {
    return `/workers/daily-requests/${reference}/arrival/signal/`;
  },

  arrivalVerifyPath(reference) {
    return `/workers/daily-requests/${reference}/arrival/verify/`;
  },

  completePath(reference) {
    return `/workers/daily-requests/${reference}/complete/`;
  },

  arrivalCodePayload(code) {
    return { code: String(code == null ? '' : code).replace(/\s+/g, '') };
  },

  canSignalArrival(offer) {
    return Boolean(
      offer
      && offer.state === 'accepted'
      && offer.request
      && offer.request.status === 'assigned'
      && offer.request.reference != null
    );
  },

  canVerifyArrival(status) {
    return status === 'assigned';
  },

  canComplete(status, arrivalVerifiedAt) {
    return status === 'in_progress' && Boolean(arrivalVerifiedAt);
  },

  optionalNumber(value) {
    if (value == null || value === '') return null;
    const number = Number(value);
    if (!Number.isFinite(number) || number < 0) return null;
    return number;
  },

  identityFrom(row) {
    const primary = row && row.worker_identity && typeof row.worker_identity === 'object'
      ? row.worker_identity
      : null;
    const extra = row && row.assigned_profile && typeof row.assigned_profile === 'object'
      ? row.assigned_profile
      : null;
    const card = primary || extra;
    if (!card) return null;
    const photo = String(card.photo_url || '').trim();
    const skills = Array.isArray(card.skills) && card.skills.length
      ? card.skills
      : (extra && Array.isArray(extra.skills) ? extra.skills : []);
    return {
      id: card.profile_id != null ? card.profile_id : (card.id != null ? card.id : (extra && extra.id)),
      worker_id: card.worker_id ? String(card.worker_id) : '',
      display_name: String(card.display_name || (extra && extra.display_name) || ''),
      photo_url: /^https?:\/\//i.test(photo) ? photo : '',
      main_category: card.main_category ? String(card.main_category) : '',
      skills: skills.map(String),
      district: String(card.district || (extra && extra.district) || ''),
      locality: String(card.locality || (extra && extra.locality) || ''),
      identity_verified: card.identity_verified === true,
      identity_verification: card.identity_verification ? String(card.identity_verification) : '',
      experience_years: this.optionalNumber(card.experience_years),
      completed_jobs: this.optionalNumber(card.completed_jobs),
    };
  },

  rowsFrom(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.results)) return data.results;
    return [];
  },

  customerView(row) {
    const view = {
      reference: row && row.reference,
      category: row && row.category ? String(row.category) : '',
      description: row && row.description ? String(row.description) : '',
      status: row && row.status ? String(row.status) : '',
      radius_km: row && row.radius_km,
      search_radius_km: row && row.search_radius_km,
      match_reason: row && row.match_reason ? String(row.match_reason) : '',
      can_expand: row && row.can_expand === true,
      expand_to_km: row && row.expand_to_km == null ? null : Number(row.expand_to_km),
      created_at: row && row.created_at ? String(row.created_at) : '',
      arrival_verified_at: row && row.arrival_verified_at ? String(row.arrival_verified_at) : '',
    };
    const identity = this.identityFrom(row);
    if (identity) {
      view.worker_identity = identity;
      view.assigned_profile = identity;
    }
    return view;
  },

  offerView(row) {
    const request = row && row.request ? row.request : {};
    return {
      id: row && row.id,
      state: row && row.state ? String(row.state) : '',
      request: {
        reference: request.reference,
        category: request.category ? String(request.category) : '',
        description: request.description ? String(request.description) : '',
        status: request.status ? String(request.status) : '',
        radius_km: request.radius_km,
      },
    };
  },

  listState(error, rows, emptyText) {
    if (error) return { kind: 'error', text: this.errorText(error) };
    const safe = Array.isArray(rows) ? rows : [];
    if (!safe.length) return { kind: 'empty', text: emptyText };
    return { kind: 'ready', text: '' };
  },

  respondGate(busy, offer, decision) {
    if (busy) return { ok: false, reason: 'busy' };
    if (!offer || offer.state !== 'offered') return { ok: false, reason: 'closed' };
    if (decision !== 'accept' && decision !== 'decline') return { ok: false, reason: 'invalid' };
    return { ok: true, payload: { decision } };
  },

  applyResponse(offer, data) {
    const next = this.offerView(offer);
    if (data && data.state) next.state = String(data.state);
    if (data && data.request_status) next.request.status = String(data.request_status);
    return next;
  },

  responseText(data) {
    if (!data || !data.state) return 'The server did not confirm the offer. Nothing was shown as updated.';
    if (data.state === 'accepted') return 'Offer accepted. No money was collected.';
    if (data.state === 'declined') return 'Offer declined. The request was not paid again.';
    return 'The server did not confirm the offer. Nothing was shown as updated.';
  },

  errorText(error) {
    if (!error || typeof error.status !== 'number') {
      return 'The server could not be reached. Nothing was changed.';
    }
    if (error.status === 401) return 'Sign in again. Nothing was changed.';
    const data = error.data;
    if (data && typeof data.detail === 'string') return data.detail;
    if (data && data.code) {
      const code = Array.isArray(data.code) ? data.code.join(' ') : String(data.code);
      if (code && code !== '[object Object]') return code;
    }
    if (data && data.decision) {
      const decision = Array.isArray(data.decision) ? data.decision.join(' ') : String(data.decision);
      return decision;
    }
    if (data && Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
      return data.non_field_errors.join(' ');
    }
    if (error.status === 403) return 'This account cannot open that list.';
    if (error.status >= 500) return 'The server had a problem. Nothing was changed.';
    return 'The request was rejected. Nothing was changed.';
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = DailyAccountLogic;
}
