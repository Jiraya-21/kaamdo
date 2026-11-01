const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/guestServiceLogic.js');

assert.equal(logic.SEND_PATH, '/auth/otp/guest/send/');
assert.equal(logic.VERIFY_PATH, '/auth/otp/guest/verify/');
assert.equal(logic.OPTIONS_PATH, '/auth/otp/guest/options/');
assert.equal(logic.CREATE_PATH, '/workers/daily-requests/');
assert.equal(logic.STATUS_PATH, '/workers/daily-requests/status/');
assert.equal(logic.CREATE_PATH.includes('mock-payment'), false);

const send = logic.sendPayload('  Guest@Example.com ');
assert.deepEqual(send, { email: 'guest@example.com', purpose: 'service_request' });
assert.deepEqual(logic.sendPayload({ phone: '98765 43210' }), {
  phone_number: '9876543210',
  purpose: 'service_request',
});
const verify = logic.verifyPayload('guest@example.com', ' 123456 ');
assert.equal(verify.code, '123456');
assert.equal(typeof verify.code, 'string');
assert.equal(logic.verifyPayload('guest@example.com', 123456).code, '123456');
assert.equal(logic.verifyPayload({ phone: '9876543210', code: '654321' }).phone_number, '9876543210');
assert.deepEqual(logic.codeProblems('12345'), ['Enter the 6-digit code.']);
assert.deepEqual(logic.phoneProblems('12345'), ['Enter a 10-digit mobile number starting with 6, 7, 8, or 9.']);
assert.deepEqual(logic.phoneProblems('9876543210'), []);

const request = logic.requestPayload({
  guestName: 'Asha Rao',
  email: 'guest@example.com',
  categoryId: '3',
  description: 'The fan does not start.',
  latitude: '12.520000',
  longitude: '76.890000',
  radiusKm: '15',
});
assert.equal(request.category, 3);
assert.equal(request.radius_km, 15);
assert.equal(logic.requestPayload({
  guestName: 'Asha Rao',
  email: 'guest@example.com',
  categoryId: '3',
  description: 'The fan does not start.',
  place: 'Town centre',
  latitude: '12.520000',
  longitude: '76.890000',
  radiusKm: '15',
}).description, 'Place: Town centre. The fan does not start.');
assert.equal(request.latitude, '12.520000');
assert.equal(logic.requestPayload({
  guestName: 'Asha Rao',
  email: 'guest@example.com',
  categoryId: '3',
  description: 'The fan does not start.',
  latitude: '12.971891887766543',
  longitude: '77.59456634567891',
  radiusKm: '15',
}).latitude, '12.971892');
assert.equal(request.contact_email, 'guest@example.com');
assert.equal(Object.hasOwn(request, 'contact_phone'), false);
assert.equal(logic.requestPayload({
  guestName: 'Asha Rao',
  phone: '9876543210',
  categoryId: '3',
  description: 'The fan does not start.',
  latitude: '12.520000',
  longitude: '76.890000',
  radiusKm: '15',
}).contact_phone, '9876543210');
assert.equal(Object.hasOwn(request, 'access_key'), false);
assert.deepEqual(logic.requestProblems({
  guestName: '',
  email: 'guest@example.com',
  categoryId: '3',
  description: 'The fan does not start.',
  latitude: '12.5',
  longitude: '76.8',
  radiusKm: '7',
}).includes('Enter your name.'), true);

const missingCode = logic.sendResult({ detail: 'No code was sent.' });
assert.equal(missingCode.ok, false);
assert.equal(missingCode.key, 'guest.noCode');
const issued = logic.sendResult({
  detail: 'Local development code only. This was not sent by SMS.',
  delivery: 'development',
  dev_code: '123456',
});
assert.equal(issued.ok, true);
assert.equal(issued.text.includes('not sent by SMS'), true);
const smsSent = logic.sendResult({
  detail: 'The SMS provider accepted the request. Enter the code when it arrives.',
  delivery: 'sms',
  expires_in: 600,
});
assert.equal(smsSent.ok, true);
assert.equal(smsSent.devCode, '');
assert.equal(smsSent.text.includes('accepted the request'), true);
assert.equal(smsSent.text.toLowerCase().includes('sent to your mobile'), false);

const created = logic.createResult({
  reference: 9,
  status: 'draft',
  radius_km: 15,
  access_key: 'shown-once-to-the-guest',
});
assert.equal(created.ok, true);
assert.equal(created.key, 'guest.savedSummary');
assert.equal(created.text.includes('not a payment'), true);
assert.equal(created.text.includes('no worker is assigned'), true);
assert.equal(logic.createResult({ reference: 9 }).ok, false);

const waiting = logic.statusView({ reference: 9, status: 'offering', radius_km: 15 });
assert.equal(waiting.assignedProfile, null);
assert.equal(waiting.text.includes('No worker has accepted yet'), true);
assert.equal(waiting.canExpand, false);
const consent = logic.statusView({
  reference: 9,
  status: 'no_workers',
  radius_km: 8,
  match_reason: 'needs_radius_consent',
  can_expand: true,
  expand_to_km: 15,
});
assert.equal(consent.canExpand, true);
assert.equal(consent.expandToKm, 15);
assert.equal(consent.text.includes('wider search'), true);
assert.equal(consent.text.toLowerCase().includes('travel fee'), true);
assert.equal(logic.categoryChoice([
  { id: 2, name: 'Electrician', slug: 'electrician' },
  { id: 3, name: 'Plumber', slug: 'plumber' },
], { slug: 'plumber' }), '3');
assert.equal(logic.categoryChoice([
  { id: 2, name: 'Electrician', slug: 'electrician' },
], { text: 'electric' }), '2');
assert.equal(logic.categoryChoice([{ id: 2, name: 'Electrician', slug: 'electrician' }], { text: 'tractor' }), '');
const assigned = logic.statusView({
  reference: 9,
  status: 'assigned',
  radius_km: 15,
  assigned_profile: {
    id: 4,
    display_name: 'Ravi Kumar',
    skills: ['Wiring'],
    district: 'Mandya',
    locality: 'Town centre',
    phone: '9000000000',
    latitude: '12.1',
  },
});
assert.equal(Object.hasOwn(assigned.assignedProfile, 'phone'), false);
assert.equal(Object.hasOwn(assigned.assignedProfile, 'latitude'), false);
assert.equal(assigned.text.includes('Ravi Kumar'), true);

assert.equal(logic.errorText(new TypeError('Failed to fetch')).includes('Nothing was saved'), true);
assert.equal(logic.errorText({ status: 400, data: { contact_email: ['Verify this email address before creating a request.'] } }).includes('Verify this email'), true);
assert.equal(logic.errorText({ status: 404, data: { detail: 'Daily service request not found.' } }), 'Daily service request not found.');

console.log('guest service logic tests passed');
