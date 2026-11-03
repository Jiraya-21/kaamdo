/**
 * Payload and message rules for the ordinary job form and the equipment form.
 * These functions do not call the network.
 */

const PostFormLogic = {
  JOB_PATH: '/jobs/',
  FARM_PATH: '/jobs/agricultural/',
  EQUIPMENT_PATH: '/equipment/',
  WORK_TYPES: ['full_time', 'part_time', 'temporary', 'contract'],
  WAGE_PERIODS: ['hourly', 'daily', 'weekly', 'monthly'],
  PRICING_BASES: ['hourly', 'daily'],

  clean(value) {
    return String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
  },

  jobPayload(values) {
    const payload = {
      title: this.clean(values.title),
      description: this.clean(values.description),
      district: this.clean(values.district),
      taluk: this.clean(values.taluk),
      locality: this.clean(values.locality),
      work_type: values.workType,
      wage_negotiable: Boolean(values.wageNegotiable),
      wage_period: values.wagePeriod,
      headcount: Number(values.headcount),
      status: 'published',
    };
    if (!payload.wage_negotiable) {
      payload.wage_amount = this.clean(values.wageAmount);
    }
    return payload;
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

  farmPayload(values) {
    const payload = {
      title: this.clean(values.title),
      description: this.clean(values.description),
      district: this.clean(values.district),
      taluk: this.clean(values.taluk),
      locality: this.clean(values.locality),
      wage_negotiable: Boolean(values.wageNegotiable),
      wage_period: values.wagePeriod,
      headcount: Number(values.headcount),
      working_hours: this.clean(values.workingHours),
      status: 'published',
    };
    if (!payload.wage_negotiable) payload.wage_amount = this.clean(values.wageAmount);
    if (this.clean(values.workStart)) payload.work_start = this.clean(values.workStart);
    if (this.clean(values.workEnd)) payload.work_end = this.clean(values.workEnd);
    return payload;
  },

  farmApplyPath(id) {
    return `/jobs/agricultural/${id}/applications/`;
  },

  equipmentPayload(values) {
    return {
      title: this.clean(values.title),
      description: this.clean(values.description),
      district: this.clean(values.district),
      taluk: this.clean(values.taluk),
      locality: this.clean(values.locality),
      pricing_basis: values.pricingBasis,
      rate: this.clean(values.rate),
      operator_included: Boolean(values.operatorIncluded),
      availability_note: this.clean(values.availabilityNote),
      status: 'draft',
    };
  },

  jobProblems(values) {
    const problems = [];
    const title = this.clean(values.title);
    const description = this.clean(values.description);
    const district = this.clean(values.district);
    const locality = this.clean(values.locality);
    if (!title) problems.push('Title is required.');
    else if (title.length > 120) problems.push('Title must be 120 characters or fewer.');
    if (!description) problems.push('Description is required.');
    else if (description.length > 2000) problems.push('Description must be 2000 characters or fewer.');
    if (!district) problems.push('District is required.');
    else if (district.length > 100) problems.push('District must be 100 characters or fewer.');
    if (Object.hasOwn(values, 'taluk') && !this.clean(values.taluk) && this.clean(values.district) !== 'Mumbai City') {
      problems.push('Taluk is required.');
    }
    if (!locality) problems.push('Locality is required.');
    else if (locality.length > 120) problems.push('Locality must be 120 characters or fewer.');
    if (!this.WORK_TYPES.includes(values.workType)) problems.push('Choose a valid work type.');
    if (!this.WAGE_PERIODS.includes(values.wagePeriod)) problems.push('Choose a valid wage period.');
    const headcount = Number(values.headcount);
    if (!Number.isInteger(headcount) || headcount < 1 || headcount > 100) {
      problems.push('Enter a vacancy count from 1 to 100.');
    }
    if (!values.wageNegotiable) {
      const amount = Number(this.clean(values.wageAmount));
      if (!Number.isFinite(amount) || amount <= 0) {
        problems.push('Enter a wage greater than zero, or mark the wage as negotiable.');
      }
    }
    return problems;
  },

  farmProblems(values) {
    const problems = this.jobProblems({ ...values, workType: 'temporary' })
      .filter((problem) => problem !== 'Choose a valid work type.');
    const start = this.clean(values.workStart);
    const end = this.clean(values.workEnd);
    const hours = this.clean(values.workingHours);
    if (start && !this.validDate(start)) problems.push('Enter a valid start date, or leave it blank.');
    if (end && !this.validDate(end)) problems.push('Enter a valid end date, or leave it blank.');
    if (this.validDate(start) && this.validDate(end) && end < start) {
      problems.push('The end date cannot be before the start date.');
    }
    if (hours.length > 80) problems.push('Working hours must be 80 characters or fewer.');
    return problems;
  },

  equipmentProblems(values) {
    const problems = [];
    const title = this.clean(values.title);
    const description = this.clean(values.description);
    const district = this.clean(values.district);
    const locality = this.clean(values.locality);
    const note = this.clean(values.availabilityNote);
    if (!title) problems.push('Title is required.');
    else if (title.length > 120) problems.push('Title must be 120 characters or fewer.');
    if (!description) problems.push('Description is required.');
    else if (description.length > 2000) problems.push('Description must be 2000 characters or fewer.');
    if (!district) problems.push('District is required.');
    else if (district.length > 100) problems.push('District must be 100 characters or fewer.');
    if (Object.hasOwn(values, 'taluk') && !this.clean(values.taluk) && this.clean(values.district) !== 'Mumbai City') {
      problems.push('Taluk is required.');
    }
    if (!locality) problems.push('Locality is required.');
    else if (locality.length > 120) problems.push('Locality must be 120 characters or fewer.');
    if (!this.PRICING_BASES.includes(values.pricingBasis)) problems.push('Choose hourly or daily pricing.');
    const rate = Number(this.clean(values.rate));
    if (!Number.isFinite(rate) || rate <= 0) problems.push('Enter a rate greater than zero.');
    if (note.length > 200) problems.push('The availability note must be 200 characters or fewer.');
    return problems;
  },

  jobResult(data) {
    if (!data || !data.id) {
      return { ok: false, text: 'The server did not confirm the job. It was not shown as saved.' };
    }
    if (data.status === 'published' && data.review_status === 'approved') {
      return { ok: true, text: 'Job saved. It is published.' };
    }
    return {
      ok: true,
      text: 'Job saved. It is waiting for staff review and is not on the public job list.',
    };
  },

  farmResult(data) {
    return this.jobResult(data);
  },

  equipmentResult(data) {
    if (!data || !data.id) {
      return { ok: false, text: 'The server did not confirm the listing. It was not shown as saved.' };
    }
    if (data.status === 'published') {
      return { ok: true, text: 'Listing saved. It is published.' };
    }
    return {
      ok: true,
      text: 'Listing saved as a draft. It stays private until KaamDo records the listing fee.',
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
      const parts = Object.entries(data).map(([, value]) => (
        Array.isArray(value) ? value.join(' ') : String(value)
      )).filter((part) => part && part !== '[object Object]');
      if (parts.length) return parts.join(' ');
    }
    if (error.status >= 500) return 'The server had a problem. Nothing was saved.';
    return 'The request was rejected. Nothing was saved.';
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = PostFormLogic;
}
