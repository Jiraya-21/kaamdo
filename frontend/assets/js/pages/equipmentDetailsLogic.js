/**
 * Payloads for one equipment advertisement.
 * These functions do not call the network and do not collect money.
 */

const EquipmentDetailsLogic = {
  INQUIRY_OTP_PURPOSE: 'equipment_inquiry',

  detailPath(id) {
    return `/equipment/${id}/`;
  },

  bookingPath(id) {
    return `/equipment/${id}/bookings/`;
  },

  inquiryPath(id) {
    return `/equipment/${id}/inquiries/`;
  },

  clean(value) {
    return String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
  },

  validDate(value) {
    const text = this.clean(value);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return false;
    const parts = text.split('-').map(Number);
    const date = new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
    return date.getUTCFullYear() === parts[0]
      && date.getUTCMonth() === parts[1] - 1
      && date.getUTCDate() === parts[2];
  },

  bookingPayload(values) {
    return {
      start_date: this.clean(values.startDate),
      end_date: this.clean(values.endDate),
      note: this.clean(values.note),
    };
  },

  inquiryPayload(values) {
    return {
      requirement: this.clean(values.requirement),
      preferred_timing: this.clean(values.preferredTiming),
    };
  },

  bookingProblems(values) {
    const problems = [];
    const start = this.clean(values.startDate);
    const end = this.clean(values.endDate);
    const note = this.clean(values.note);
    if (!this.validDate(start)) problems.push('Enter a start date.');
    if (!this.validDate(end)) problems.push('Enter an end date.');
    if (this.validDate(start) && this.validDate(end) && end < start) {
      problems.push('The end date cannot be before the start date.');
    }
    if (note.length > 1000) problems.push('Note must be 1000 characters or fewer.');
    return problems;
  },

  inquiryProblems(values) {
    const problems = [];
    const requirement = this.clean(values.requirement);
    const timing = this.clean(values.preferredTiming);
    if (!requirement) problems.push('Describe what you need.');
    else if (requirement.length > 1000) problems.push('Requirement must be 1000 characters or fewer.');
    if (timing.length > 200) problems.push('Preferred timing must be 200 characters or fewer.');
    return problems;
  },

  bookingResult(data) {
    if (!data || !data.id || data.status !== 'requested') {
      return { ok: false, text: 'The server did not confirm a requested booking. Nothing was shown as saved.' };
    }
    return {
      ok: true,
      text: 'Request saved. It is requested. It is not a confirmed rental and no money was collected.',
    };
  },

  inquiryResult(data) {
    if (!data || !data.id || data.status !== 'new') {
      return { ok: false, text: 'The server did not confirm the inquiry. Nothing was shown as saved.' };
    }
    return {
      ok: true,
      text: 'Inquiry saved. It asks the owner to make contact and does not reserve the equipment.',
    };
  },

  needsPhoneCheck(error) {
    const text = this.errorText(error).toLowerCase();
    return text.includes('verify your mobile');
  },

  otpSendResult(data) {
    if (data && data.delivery === 'sms') {
      return {
        ok: true,
        key: 'booking.smsSent',
        text: 'OTP sent to your mobile.',
      };
    }
    if (!data || data.delivery !== 'development' || !data.dev_code) {
      return {
        ok: false,
        key: 'booking.noCode',
        text: 'No code was sent. Try again.',
      };
    }
    return {
      ok: true,
      key: 'booking.smsSent',
      devCode: String(data.dev_code),
      text: 'OTP sent to your mobile.',
    };
  },

  errorText(error) {
    if (!error || typeof error.status !== 'number') {
      return 'The server could not be reached. Nothing was saved.';
    }
    if (error.status === 401) return 'Sign in again before submitting. Nothing was saved.';
    const data = error.data;
    if (typeof data === 'string' && data.trim()) return data;
    if (data && typeof data.detail === 'string') return data.detail;
    if (data && Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
      return data.non_field_errors.join(' ');
    }
    if (Array.isArray(data) && data.length) return String(data[0]);
    if (data && typeof data === 'object') {
      const parts = Object.entries(data).map(([key, value]) => {
        const text = Array.isArray(value) ? value.join(' ') : String(value);
        return `${key}: ${text}`;
      }).filter((part) => part.trim());
      if (parts.length) return parts.join(' ');
    }
    if (error.status >= 500) return 'The server had a problem. Nothing was saved.';
    return 'The request was rejected. Nothing was saved.';
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = EquipmentDetailsLogic;
}
