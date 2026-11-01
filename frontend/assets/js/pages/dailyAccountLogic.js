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

  canSkipPayment(status) {
    return status === 'draft' || status === 'awaiting_payment';
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
    const payload = {
      category: Number(values.categoryId),
      description: this.workDescription(values.place, values.description),
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
      if (!Number.isInteger(radius) || radius < 8 || radius > 50) {
        problems.push('Choose a radius from 8 to 50 kilometres.');
      }
    }
    return problems;
  },

  createResult(data) {
    if (!data || data.reference == null || data.status !== 'draft') {
      return { ok: false, text: 'The request was not confirmed. No worker was assigned.' };
    }
    if (Object.hasOwn(data, 'access_key') || Object.hasOwn(data, 'assigned_profile')) {
      return { ok: false, text: 'The response included a field this save does not confirm.' };
    }
    return {
      ok: true,
      reference: data.reference,
      text: 'Request saved. No worker is assigned yet. This did not collect money.',
    };
  },

  statusSentence(status, workerName) {
    const name = workerName ? String(workerName) : '';
    const sentences = {
      draft: 'Saved. No worker is assigned yet.',
      awaiting_payment: 'Waiting for a recorded payment. No worker is assigned yet.',
      dispatch_pending: 'Ready to offer after a recorded payment. No worker is assigned yet.',
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
    };
    const card = row && row.assigned_profile;
    if (card && typeof card === 'object') {
      view.assigned_profile = {
        id: card.id,
        display_name: card.display_name ? String(card.display_name) : '',
        skills: Array.isArray(card.skills) ? card.skills.map(String) : [],
        district: card.district ? String(card.district) : '',
        locality: card.locality ? String(card.locality) : '',
      };
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
