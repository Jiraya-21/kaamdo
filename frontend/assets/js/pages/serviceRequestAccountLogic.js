/**
 * Direct service requests and the provider profile form.
 * These functions do not call the network and do not collect a payment.
 */

const ServiceRequestAccountLogic = {
  CUSTOMER_PATH: '/workers/requests/',
  INCOMING_PATH: '/workers/requests/incoming/',
  PROFILE_PATH: '/workers/profile/',
  VERIFICATION_PATH: '/workers/verification/',
  CATEGORY_PATH: '/workers/categories/',

  clean(value) {
    return String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
  },

  decisionPath(id) {
    return `/workers/requests/${id}/`;
  },

  rowsFrom(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.results)) return data.results;
    return [];
  },

  customerView(row) {
    return {
      id: row && row.id,
      profile: row && row.profile,
      provider_name: row && row.provider_name ? String(row.provider_name) : 'Worker',
      description: row && row.description ? String(row.description) : '',
      status: row && row.status ? String(row.status) : '',
      created_at: row && row.created_at ? String(row.created_at) : '',
    };
  },

  providerView(row) {
    const view = this.customerView(row);
    view.contact_phone = row && row.contact_phone ? String(row.contact_phone) : '';
    return view;
  },

  actions(status) {
    if (status === 'requested') return ['accepted', 'declined'];
    if (status === 'accepted') return ['closed'];
    return [];
  },

  decisionGate(busy, currentStatus, nextStatus) {
    if (busy) return { ok: false, reason: 'busy' };
    if (this.actions(currentStatus).indexOf(nextStatus) === -1) {
      return { ok: false, reason: 'closed' };
    }
    return { ok: true, payload: { status: nextStatus } };
  },

  canSubmitVerification(status) {
    return status === 'not_submitted' || status === 'rejected' || status === 'needs_info' || !status;
  },

  coordinateText(value) {
    const text = this.clean(value);
    if (!text) return '';
    const number = Number(text);
    if (!Number.isFinite(number)) return text;
    return number.toFixed(6);
  },

  profilePayload(values) {
    const source = values || {};
    const latitude = this.coordinateText(source.latitude);
    const longitude = this.coordinateText(source.longitude);
    if ((latitude && !longitude) || (!latitude && longitude)) {
      return { error: 'Use this phone location, or leave the map point blank.' };
    }
    const skills = String(source.skills == null ? '' : source.skills)
      .split(',')
      .map((item) => this.clean(item))
      .filter(Boolean);
    const payload = {
      skills,
      bio: this.clean(source.bio),
      service_rate: this.clean(source.serviceRate),
      pricing_basis: source.pricingBasis === 'daily' ? 'daily' : 'hourly',
      district: this.clean(source.district),
      taluk: this.clean(source.taluk),
      locality: this.clean(source.locality),
      availability: source.availability === 'unavailable' ? 'unavailable' : 'available',
      publication_status: source.publicationStatus === 'published' ? 'published' : 'draft',
    };
    const years = this.clean(source.experienceYears);
    const radius = this.clean(source.serviceRadiusKm);
    if (years) payload.experience_years = Number(years);
    if (radius) payload.service_radius_km = Number(radius);
    if (latitude && longitude) {
      payload.latitude = latitude;
      payload.longitude = longitude;
    }
    if (Array.isArray(source.categorySlugs)) {
      payload.service_categories = source.categorySlugs
        .map((slug) => this.clean(slug))
        .filter(Boolean);
    }
    return { payload };
  },

  availabilityPayload(next) {
    if (next !== 'available' && next !== 'unavailable') {
      return { error: 'Choose available or not available.' };
    }
    return { payload: { availability: next } };
  },

  availabilityResult(data, expected) {
    if (!data || data.availability !== expected) {
      return { ok: false, text: 'The server did not confirm the new availability.' };
    }
    return { ok: true, value: data.availability };
  },

  errorText(error) {
    if (!error || typeof error.status !== 'number') return 'The server could not be reached.';
    if (error.status === 401) return 'Sign in again.';
    const data = error.data;
    if (data && typeof data.detail === 'string') return data.detail;
    if (data && Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
      return data.non_field_errors.join(' ');
    }
    if (data && typeof data === 'object') {
      const first = Object.values(data)[0];
      if (Array.isArray(first) && first.length) return String(first[0]);
      if (typeof first === 'string') return first;
    }
    if (error.status === 403) return 'This account cannot do that.';
    return 'The server rejected the request.';
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = ServiceRequestAccountLogic;
}
