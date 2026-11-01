/**
 * KaamDo Workers API
 * API routes for worker discovery, profiles, and radius searches.
 */

const WorkersApi = {
  // GET /api/v1/workers/?radius=20&lat=...&lng=...&skill=...
  getWorkers(filters = {}) {
    return ApiClient.get('/workers/', filters);
  },

  // GET /api/v1/workers/<id>/
  getWorkerById(id) {
    return ApiClient.get(`/workers/${id}/`);
  },

  // PUT /api/v1/workers/profile/
  updateProfile(profileData) {
    return ApiClient.put('/workers/profile/', profileData);
  }
};
