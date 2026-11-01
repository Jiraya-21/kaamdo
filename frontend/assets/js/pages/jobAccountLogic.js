/**
 * Employer and job-seeker account payloads.
 * These functions do not call the network.
 */

const JobAccountLogic = {
  ORDINARY: {
    mine: '/jobs/mine/',
    applications: '/jobs/applications/',
    jobApplications(id) {
      return `/jobs/${id}/applications/`;
    },
    application(id) {
      return `/jobs/applications/${id}/`;
    },
    decision(jobId, applicationId) {
      return `/jobs/${jobId}/applications/${applicationId}/`;
    },
    detail(id) {
      return `/jobs/${id}/`;
    },
  },
  FARM: {
    mine: '/jobs/agricultural/mine/',
    applications: '/jobs/agricultural/applications/',
    jobApplications(id) {
      return `/jobs/agricultural/${id}/applications/`;
    },
    application(id) {
      return `/jobs/agricultural/applications/${id}/`;
    },
    decision(jobId, applicationId) {
      return `/jobs/agricultural/${jobId}/applications/${applicationId}/`;
    },
    detail(id) {
      return `/jobs/agricultural/${id}/`;
    },
  },

  rowsFrom(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.results)) return data.results;
    return [];
  },

  jobView(row) {
    return {
      id: row && row.id,
      title: row && row.title ? String(row.title) : '',
      status: row && row.status ? String(row.status) : '',
      review_status: row && row.review_status ? String(row.review_status) : '',
      district: row && row.district ? String(row.district) : '',
      taluk: row && row.taluk ? String(row.taluk) : '',
      locality: row && row.locality ? String(row.locality) : '',
    };
  },

  applicationView(row) {
    return {
      id: row && row.id,
      job: row && row.job,
      job_title: row && row.job_title ? String(row.job_title) : '',
      job_status: row && row.job_status ? String(row.job_status) : '',
      job_district: row && row.job_district ? String(row.job_district) : '',
      job_taluk: row && row.job_taluk ? String(row.job_taluk) : '',
      job_locality: row && row.job_locality ? String(row.job_locality) : '',
      applicant_name: row && row.applicant_name ? String(row.applicant_name) : '',
      message: row && row.message ? String(row.message) : '',
      status: row && row.status ? String(row.status) : '',
      created_at: row && row.created_at ? String(row.created_at) : '',
    };
  },

  listState(error, rows, emptyText) {
    if (error) return { kind: 'error', text: this.errorText(error) };
    const safe = Array.isArray(rows) ? rows : [];
    if (!safe.length) return { kind: 'empty', text: emptyText };
    return { kind: 'ready', text: '' };
  },

  withdrawGate(busy, application) {
    if (busy) return { ok: false, reason: 'busy' };
    if (!application || application.status !== 'submitted') return { ok: false, reason: 'closed' };
    return { ok: true, payload: { status: 'withdrawn' } };
  },

  closeGate(busy, job) {
    if (busy) return { ok: false, reason: 'busy' };
    if (!job || (job.status !== 'draft' && job.status !== 'published')) {
      return { ok: false, reason: 'closed' };
    }
    return { ok: true, payload: { status: 'closed' } };
  },

  employerActions(application) {
    if (application && application.status === 'submitted') return ['accepted', 'rejected'];
    return [];
  },

  decisionGate(busy, application, status) {
    if (busy) return { ok: false, reason: 'busy' };
    if (!application || application.status !== 'submitted') return { ok: false, reason: 'closed' };
    if (status !== 'accepted' && status !== 'rejected') return { ok: false, reason: 'invalid' };
    return { ok: true, payload: { status } };
  },

  applyWithdraw(application, data) {
    const next = this.applicationView(application);
    if (data && data.status) next.status = String(data.status);
    return next;
  },

  errorText(error) {
    if (!error || typeof error.status !== 'number') {
      return 'The server could not be reached. Nothing was changed.';
    }
    if (error.status === 401) return 'Sign in again. Nothing was changed.';
    const data = error.data;
    if (data && typeof data.detail === 'string') return data.detail;
    if (data && Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
      return data.non_field_errors.join(' ');
    }
    if (data && data.status) {
      return Array.isArray(data.status) ? data.status.join(' ') : String(data.status);
    }
    if (error.status === 403) return 'This account cannot open that list.';
    if (error.status >= 500) return 'The server had a problem. Nothing was changed.';
    return 'The request was rejected. Nothing was changed.';
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = JobAccountLogic;
}
