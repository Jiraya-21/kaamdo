const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const OtpUi = require('../assets/js/components/otpUi.js');

assert.equal(OtpUi.canResend(0, 1000), true);
assert.equal(OtpUi.canResend(1000, 1000 + 29000, 30), false);
assert.equal(OtpUi.canResend(1000, 1000 + 30000, 30), true);
assert.equal(OtpUi.secondsLeft(1000, 1000 + 5000, 30), 25);
assert.equal(OtpUi.secondsLeft(null, 5000, 30), 0);
assert.deepEqual(OtpUi.visibleFields('phone'), { phone: true, email: false });
assert.deepEqual(OtpUi.visibleFields('email'), { phone: false, email: true });
assert.equal(OtpUi.digits('12-34 ab 56'), '123456');
assert.equal(OtpUi.digits('123456789'), '123456');

const guestHtml = fs.readFileSync(path.join(__dirname, '../pages/services/guest-request.html'), 'utf8');
assert.match(guestHtml, /otpUi\.js/);
assert.match(guestHtml, /name="verify-method"/);
assert.match(guestHtml, /value="phone"/);
assert.equal(guestHtml.includes('value="phone" disabled'), false);
assert.match(guestHtml, /id="request-phone"/);
assert.match(guestHtml, /id="guest-verify-blocked"/);

console.log('otp ui tests passed');
