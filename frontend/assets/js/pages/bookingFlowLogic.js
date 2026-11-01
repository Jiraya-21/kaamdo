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
        text: 'The SMS provider accepted the request. Enter the code when it arrives.',
      };
    }
    if (!data || data.delivery !== 'development' || !data.dev_code) {
      return {
        ok: false,
        key: 'booking.noCode',
        text: 'No code was issued. Nothing was verified.',
      };
    }
    return {
      ok: true,
      key: 'booking.devCode',
      devCode: String(data.dev_code),
      text: 'Local development code only. This was not sent by SMS.',
    };
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = BookingFlowLogic;
}
