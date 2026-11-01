const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/bookingFlowLogic.js');

assert.equal(logic.REQUEST_PATH, '/workers/requests/');
assert.equal(logic.REQUEST_PATH.includes('mock-payment'), false);

const missing = logic.sendResult({ detail: 'SMS delivery is not configured. No code was sent.' });
assert.equal(missing.ok, false);
assert.equal(missing.key, 'booking.noCode');
assert.equal(missing.text.includes('No code was issued'), true);

const issued = logic.sendResult({
  detail: 'Local development code only. This was not sent by SMS.',
  delivery: 'development',
  dev_code: '654321',
});
assert.equal(issued.ok, true);
assert.equal(issued.devCode, '654321');
assert.equal(issued.text.includes('not sent by SMS'), true);

assert.equal(logic.sendResult({ delivery: 'development' }).ok, false);
assert.equal(logic.sendResult(null).ok, false);

const sms = logic.sendResult({
  detail: 'The SMS provider accepted the request. Enter the code when it arrives.',
  delivery: 'sms',
  dev_code: '654321',
});
assert.equal(sms.ok, true);
assert.equal(sms.key, 'booking.smsSent');
assert.equal(sms.devCode, undefined);
assert.equal(sms.text.includes('accepted the request'), true);
assert.equal(sms.text.toLowerCase().includes('sent to your mobile'), false);

console.log('booking flow logic tests passed');
