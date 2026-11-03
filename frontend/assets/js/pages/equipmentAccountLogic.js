/**
 * Decision payloads for equipment bookings and inquiries.
 * These functions do not call the network and do not collect money.
 */

const EquipmentAccountLogic = {
  LISTING_FORM_PATH: '../jobs/post-job.html#equipment',

  LISTINGS_PATH: '/equipment/mine/',
  MY_BOOKINGS_PATH: '/equipment/bookings/',

  listingBookingsPath(id) {
    return `/equipment/${id}/bookings/`;
  },

  listingInquiriesPath(id) {
    return `/equipment/${id}/inquiries/`;
  },

  bookingDecisionPath(id) {
    return `/equipment/bookings/${id}/`;
  },

  inquiryDecisionPath(id) {
    return `/equipment/inquiries/${id}/`;
  },

  decisionPayload(status) {
    return { status };
  },

  bookingActions(booking) {
    if (!booking || booking.status !== 'requested') return [];
    return ['accepted', 'declined'];
  },

  inquiryActions(inquiry) {
    if (!inquiry || inquiry.status === 'closed') return [];
    // One clear action for low-tech owners: close the inquiry.
    return ['closed'];
  },

  decisionResult(data, kind) {
    if (!data || !data.id || !data.status) {
      return { ok: false, text: 'The server did not confirm the update. Nothing was shown as saved.' };
    }
    if (kind === 'booking') {
      return {
        ok: true,
        text: `Request updated to ${data.status}. This does not collect money.`,
      };
    }
    return {
      ok: true,
      text: `Inquiry updated to ${data.status}. An inquiry does not reserve the equipment.`,
    };
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = EquipmentAccountLogic;
}
