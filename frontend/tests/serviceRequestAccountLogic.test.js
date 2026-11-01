const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/serviceRequestAccountLogic.js');

assert.equal(logic.CUSTOMER_PATH, '/workers/requests/');
assert.equal(logic.INCOMING_PATH, '/workers/requests/incoming/');
assert.equal(logic.decisionPath(4), '/workers/requests/4/');
assert.equal(Object.hasOwn(logic.customerView({
  id: 1,
  provider_name: 'Ravi',
  description: 'Tap',
  status: 'requested',
  contact_phone: '9000000102',
}), 'contact_phone'), false);
assert.equal(logic.providerView({ id: 1, contact_phone: '9000000102', status: 'requested' }).contact_phone, '9000000102');
assert.deepEqual(logic.actions('requested'), ['accepted', 'declined']);
assert.deepEqual(logic.actions('accepted'), ['closed']);
assert.deepEqual(logic.actions('declined'), []);
assert.deepEqual(logic.decisionGate(true, 'requested', 'accepted'), { ok: false, reason: 'busy' });
assert.deepEqual(logic.decisionGate(false, 'requested', 'accepted'), {
  ok: true,
  payload: { status: 'accepted' },
});
assert.equal(logic.decisionGate(false, 'declined', 'accepted').ok, false);
assert.equal(logic.canSubmitVerification('pending'), false);
assert.equal(logic.canSubmitVerification('not_submitted'), true);
const saved = logic.profilePayload({
  skills: 'Plumbing, plumbing',
  bio: 'Household work',
  serviceRate: '350.00',
  pricingBasis: 'hourly',
  district: 'Mandya',
  locality: 'Town centre',
  publicationStatus: 'published',
  latitude: '',
  longitude: '',
});
assert.deepEqual(saved.payload.skills, ['Plumbing', 'plumbing']);
assert.equal(saved.payload.publication_status, 'published');
assert.equal(Object.hasOwn(saved.payload, 'latitude'), false);
assert.equal(Object.hasOwn(saved.payload, 'service_categories'), false);
const withCategories = logic.profilePayload({
  skills: 'Wiring',
  bio: 'Household work',
  serviceRate: '100.00',
  categorySlugs: ['electrician', ''],
});
assert.deepEqual(withCategories.payload.service_categories, ['electrician']);
assert.equal(logic.profilePayload({ latitude: '12', longitude: '' }).error, 'Use this phone location, or leave the map point blank.');
assert.deepEqual(
  logic.profilePayload({
    latitude: '12.971891887766543',
    longitude: '77.59456634567891',
  }).payload.latitude,
  '12.971892',
);
assert.deepEqual(logic.availabilityPayload('unavailable'), { payload: { availability: 'unavailable' } });
assert.equal(logic.availabilityPayload('closed').error.includes('available'), true);
assert.equal(logic.availabilityResult({ availability: 'unavailable' }, 'unavailable').ok, true);
assert.equal(logic.availabilityResult({ availability: 'available' }, 'unavailable').ok, false);

console.log('service request account logic tests passed');
