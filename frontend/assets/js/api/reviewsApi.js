/**
 * KaamDo Reviews API
 * API routes for verified ratings and reviews.
 */

const ReviewsApi = {
  // GET /api/v1/reviews/worker/<worker_id>/
  getWorkerReviews(workerId) {
    return ApiClient.get(`/reviews/worker/${workerId}/`);
  },

  // POST /api/v1/reviews/
  submitReview(reviewData) {
    return ApiClient.post('/reviews/', reviewData);
  }
};
