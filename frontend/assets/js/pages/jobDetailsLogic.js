/**
 * Paths for one ordinary job or one agricultural job.
 * These functions do not call the network.
 */

const JobDetailsLogic = {
  paths(kind, id) {
    const key = encodeURIComponent(String(id == null ? '' : id));
    if (kind === 'agricultural') {
      return {
        job: `/jobs/agricultural/${key}/`,
        apply: `/jobs/agricultural/${key}/applications/`,
        listHref: 'farm-jobs.html',
        listLabel: 'Back to farm jobs',
      };
    }
    return {
      job: `/jobs/${key}/`,
      apply: `/jobs/${key}/applications/`,
      listHref: 'jobs-list.html',
      listLabel: 'Back to jobs',
    };
  },

  scheduleText(job) {
    if (!job) return '';
    const parts = [];
    if (job.work_start) parts.push(`Starts ${job.work_start}`);
    if (job.work_end) parts.push(`Ends ${job.work_end}`);
    if (job.working_hours) parts.push(String(job.working_hours));
    return parts.join('. ');
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = JobDetailsLogic;
}
