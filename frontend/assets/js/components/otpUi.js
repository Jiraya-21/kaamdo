/**
 * OTP field helpers. These functions do not send messages.
 */

const OtpUi = {
  RESEND_SECONDS: 30,

  canResend(lastSentAt, now, waitSeconds) {
    if (!lastSentAt) return true;
    const wait = (waitSeconds == null ? this.RESEND_SECONDS : waitSeconds) * 1000;
    return (now - lastSentAt) >= wait;
  },

  secondsLeft(lastSentAt, now, waitSeconds) {
    if (!lastSentAt) return 0;
    const wait = (waitSeconds == null ? this.RESEND_SECONDS : waitSeconds) * 1000;
    const remain = Math.ceil((wait - (now - lastSentAt)) / 1000);
    return remain > 0 ? remain : 0;
  },

  visibleFields(method) {
    if (method === 'email') return { phone: false, email: true };
    return { phone: true, email: false };
  },

  digits(value) {
    return String(value == null ? '' : value).replace(/\D/g, '').slice(0, 6);
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = OtpUi;
}
