/**
 * Query string for the public ordinary job list.
 * Filters are sent to the API so they apply before pagination.
 */

const JobListLogic = {
  LIST_PATH: '/jobs/',
  WORK_TYPES: ['full_time', 'part_time', 'temporary', 'contract'],

  clean(value) {
    return String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
  },

  params(values) {
    const params = {};
    const query = this.clean(values && values.query);
    const district = this.clean(values && values.district);
    const workType = this.clean(values && values.workType);
    if (query) params.q = query;
    if (district && district.toLowerCase() !== 'all') params.district = district;
    if (workType && this.WORK_TYPES.indexOf(workType) !== -1) params.work_type = workType;
    return params;
  },

  wageText(job) {
    if (!job) return '';
    if (job.wage_negotiable) return 'Wage: negotiable';
    return `Wage: ${job.wage_amount} ${job.wage_period}`;
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = JobListLogic;
}
