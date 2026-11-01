/**
 * KaamDo Equipment Rental API
 * API routes for agricultural equipment catalog and rental bookings.
 */

const EquipmentApi = {
  // GET /api/v1/equipment/
  getEquipment(filters = {}) {
    return ApiClient.get('/equipment/', filters);
  },

  // GET /api/v1/equipment/<id>/
  getEquipmentById(id) {
    return ApiClient.get(`/equipment/${id}/`);
  },

  // POST /api/v1/equipment/<id>/bookings/
  requestRental(equipmentId, rentalData) {
    return ApiClient.post(`/equipment/${equipmentId}/bookings/`, rentalData);
  },

  // PATCH /api/v1/equipment/bookings/<id>/
  respondToRental(rentalId, status) {
    return ApiClient.patch(`/equipment/bookings/${rentalId}/`, { status });
  }
};
