const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const logic = require('../assets/js/pages/guestServiceLogic.js');

const guestHtml = fs.readFileSync(
  path.join(__dirname, '../pages/services/guest-request.html'),
  'utf8',
);
const guestJs = fs.readFileSync(
  path.join(__dirname, '../assets/js/pages/guestService.js'),
  'utf8',
);
const trackHtml = fs.readFileSync(
  path.join(__dirname, '../pages/services/track-request.html'),
  'utf8',
);

assert.match(guestHtml, /data-i18n="guest.title"/);
assert.match(guestHtml, /data-guest-step="service"/);
assert.match(guestHtml, /data-guest-step="details"/);
assert.match(guestHtml, /data-guest-step="review"/);
assert.equal(guestHtml.includes('data-guest-step="status"'), false);
assert.equal(guestHtml.includes('id="guest-status-form"'), false);
assert.equal(guestHtml.includes('id="status-access-key"'), false);
assert.match(guestHtml, /href="track-request.html"/);
assert.equal(guestHtml.includes('id="use-manual-location"'), false);
assert.equal(guestHtml.includes('id="manual-location-fields"'), false);
assert.match(guestHtml, /id="request-district"/);
assert.match(guestHtml, /id="request-taluk"/);
assert.match(guestHtml, /id="request-latitude"/);
assert.match(guestHtml, /id="request-longitude"/);
assert.match(guestHtml, /type="hidden"/);
assert.match(guestHtml, /for="guest-phone"/);
assert.match(guestHtml, /for="guest-email"/);
assert.equal(guestHtml.includes('Mobile code is not available'), false);
assert.match(trackHtml, /id="guest-status-form"/);
assert.match(trackHtml, /id="status-access-key"/);
assert.match(trackHtml, /data-i18n="track.lead"/);
assert.match(trackHtml, /class="track-need"/);
assert.match(trackHtml, /data-i18n="track.formLead"/);
assert.match(trackHtml, /data-i18n="track.submit"/);
assert.match(trackHtml, /for="status-reference"/);
assert.match(trackHtml, /for="status-access-key"/);
assert.match(trackHtml, /aria-describedby="status-reference-help"/);
assert.match(trackHtml, /trackRequest\.js/);
assert.equal(trackHtml.includes('Look up one request'), false);
assert.equal(trackHtml.includes('location.search'), false);
assert.deepEqual(logic.statusProblems('', ''), [
  'Enter the request number.',
  'Enter the tracking key shown when the request was saved.',
]);
assert.equal(logic.statusProblems('12', 'saved-key').length, 0);

assert.equal(logic.OPTIONS_PATH, '/auth/otp/guest/options/');
assert.deepEqual(logic.parseOptions(null), {
  email: false,
  phone: false,
  emailMode: 'unavailable',
  phoneMode: 'unavailable',
});
assert.deepEqual(logic.parseOptions({
  email: { available: true, mode: 'development' },
  phone: { available: false, mode: 'unavailable' },
}), {
  email: true,
  phone: false,
  emailMode: 'development',
  phoneMode: 'unavailable',
});
assert.equal(logic.parseOptions({
  email: { available: false, mode: 'unavailable' },
  phone: { available: true, mode: 'sms' },
}).phone, true);
assert.equal(logic.parseOptions({
  email: { available: true, mode: 'development' },
  phone: { available: true, mode: 'development' },
}).phone, false);
assert.equal(logic.hasUsableVerification(logic.parseOptions(null)), false);
assert.equal(logic.hasUsableVerification(logic.parseOptions({
  email: { available: true, mode: 'development' },
  phone: { available: false, mode: 'unavailable' },
})), true);
assert.equal(logic.defaultMethod({ phone: true, email: true }), 'phone');
assert.equal(logic.defaultMethod({ phone: false, email: true }), 'email');
assert.equal(logic.canCreate({ busy: false, submitted: false }), true);
assert.equal(logic.canCreate({ busy: true, submitted: false }), false);
assert.equal(logic.canCreate({ busy: false, submitted: true }), false);
assert.equal(logic.trackHref(12), 'track-request.html?reference=12');
assert.equal(logic.trackHref('nope'), 'track-request.html');
assert.deepEqual(logic.ignoreTrackingKeyInQuery(new URLSearchParams('reference=9&access_key=secret')), {
  reference: '9',
  accessKey: '',
});
assert.equal(logic.detailsProblems({
  guestName: 'Asha',
  categoryId: '3',
  description: 'Fan repair',
  latitude: '12.5',
  longitude: '76.8',
  radiusKm: '15',
}).length, 0);
const issued = logic.sendResult({
  delivery: 'development',
  dev_code: '123456',
  detail: 'Development practice code only. This was not sent by SMS or email.',
});
assert.equal(issued.ok, true);
assert.equal(issued.practice, true);
const sms = logic.sendResult({
  delivery: 'sms',
  detail: 'The SMS provider accepted the request. Enter the code when it arrives.',
});
assert.equal(sms.ok, true);
assert.equal(sms.practice, false);
assert.equal(logic.sendResult({ delivery: 'sms', dev_code: '111111' }).ok, false);
assert.equal(logic.sendResult({ detail: 'Email delivery is not configured. No code was sent.' }).ok, false);

const guestCss = fs.readFileSync(
  path.join(__dirname, '../assets/css/pages/guest-request.css'),
  'utf8',
);
assert.match(guestCss, /\[hidden\]\s*\{\s*display:\s*none\s*!important;/);
assert.match(guestJs, /setAttribute\('aria-hidden'/);

const messages = fs.readFileSync(
  path.join(__dirname, '../assets/js/i18n/messages.js'),
  'utf8',
);
assert.equal(messages.includes("'guest.requestHeading': '3. Describe the work'"), false);
assert.equal(messages.includes("'guest.emailHeading': '2. Check your contact'"), false);
assert.match(messages, /'guest.requestHeading': 'Describe the work'/);
assert.match(messages, /'guest.emailHeading': 'Check your contact'/);
assert.match(messages, /'track.formHeading': 'See how the work is going'/);
assert.equal(messages.includes("'track.formHeading': 'Look up one request'"), false);

console.log('guest request flow tests passed');
