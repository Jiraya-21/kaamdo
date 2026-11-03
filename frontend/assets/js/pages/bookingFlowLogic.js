/**
 * Direct-request OTP checks.
 * These functions do not call the network and do not record a payment.
 */

const BookingFlowLogic = {
  REQUEST_PATH: '/workers/requests/',

  sendResult(data) {
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
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = BookingFlowLogic;
}
