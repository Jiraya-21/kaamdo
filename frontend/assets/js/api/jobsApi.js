/**
 * Ordinary job routes that exist on the API.
 * Hire requests and price revisions are not implemented.
 */

const JobsApi = {
  getJobs(filters = {}) {
    return ApiClient.get('/jobs/', filters);
  },

  getJobById(id) {
    return ApiClient.get(`/jobs/${id}/`);
  },

  createJob(jobData) {
    return ApiClient.post('/jobs/', jobData);
  },
};
