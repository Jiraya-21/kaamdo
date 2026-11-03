const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/dailyAccountLogic.js');

assert.equal(logic.REQUESTS_PATH, '/workers/daily-requests/mine/');
assert.equal(logic.OFFERS_PATH, '/workers/daily-offers/mine/');
assert.equal(logic.respondPath(4), '/workers/daily-offers/4/respond/');
assert.equal(logic.REQUESTS_PATH.includes('mock-payment'), false);
const draft = logic.requestPayload({
  categoryId: '4',
  description: ' Fan repair ',
  latitude: '12.1',
  longitude: '77.2',
  radiusKm: '15',
});
assert.deepEqual(draft, {
  category: 4,
  description: 'Fan repair',
  latitude: '12.100000',
  longitude: '77.200000',
  radius_km: 15,
});
assert.equal(Object.hasOwn(draft, 'customer'), false);
assert.equal(logic.requestProblems({ categoryId: '', description: '', latitude: '', longitude: '' }).length > 0, true);
assert.equal(logic.requestProblems({
  categoryId: '4',
  description: 'Fan repair',
  latitude: '12.1',
  longitude: '77.2',
  radiusKm: '15',
}).length, 0);
assert.equal(logic.requestProblems({
  categoryId: '4',
  description: 'Fan repair',
  latitude: '12.1',
  longitude: '77.2',
  radiusKm: '60',
}).length, 0);
assert.ok(logic.requestProblems({
  categoryId: '4',
  description: 'Fan repair',
  latitude: '12.1',
  longitude: '77.2',
  radiusKm: '101',
}).some((item) => item.includes('5 to 100')));
const placed = logic.requestPayload({
  categoryId: '4',
  description: 'Fan repair',
  place: 'Mandya town',
  latitude: '12.1',
  longitude: '77.2',
  radiusKm: '15',
});
assert.equal(placed.description, 'Place: Mandya town. Fan repair');
assert.equal(Object.hasOwn(placed, 'place'), false);
assert.match(
  logic.requestProblems({
    categoryId: '4',
    description: 'Fan repair',
    latitude: '',
    longitude: '',
    radiusKm: '15',
  }).join(' '),
  /phone location/,
);
assert.equal(logic.createResult({ reference: 8, status: 'awaiting_payment' }).ok, true);
assert.equal(
  logic.createResult({ reference: 8, status: 'awaiting_payment' }).text.includes('inspection fee'),
  true,
);
assert.equal(logic.createResult({ reference: 8, status: 'assigned' }).ok, false);
assert.equal(logic.createResult({ reference: 8, status: 'awaiting_payment', assigned_profile: { id: 1 } }).ok, false);
assert.equal(logic.statusSentence('awaiting_payment').includes('inspection fee'), true);
assert.equal(logic.statusSentence('offering').includes('No worker has accepted'), true);
assert.equal(logic.statusSentence('assigned', 'Asha').includes('Asha'), true);
assert.equal(logic.statusSentence('worker_cancelled', 'Asha').includes('not a new assignment'), true);
assert.equal(logic.OFFERS_PATH.includes('mock-payment'), false);
assert.equal(logic.respondPath(4).includes('mock-payment'), false);
assert.equal(logic.mockPaymentPath(8), '/workers/daily-requests/8/mock-payment/');
assert.equal(logic.extraPaymentPath(8), '/workers/daily-requests/8/mock-extra-payment/');
assert.equal(logic.extrasPath(8), '/workers/daily-requests/8/extras/');
assert.equal(logic.canPayInspection({
  payment: { can_pay_inspection: true, mock_checkout: true },
}), true);
assert.equal(logic.canPayInspection({
  payment: { can_pay_inspection: true, mock_checkout: false },
}), false);
assert.equal(logic.canPayExtras({
  payment: { can_pay_extras: true, mock_checkout: true },
}), true);
assert.equal(logic.canSkipPayment('draft'), true);
assert.equal(logic.canSkipPayment('offering'), false);
assert.equal(logic.testPaymentEnabled({ test_payment: { enabled: true, money_received: false } }), true);
assert.equal(logic.testPaymentEnabled({ test_payment: { enabled: true, money_received: true } }), false);
assert.equal(logic.testPaymentEnabled({ test_payment: null }), false);
assert.equal(logic.testPaymentEnabled({}), false);

const page = logic.rowsFrom({ results: [{ reference: 2 }] });
assert.deepEqual(page, [{ reference: 2 }]);
assert.deepEqual(logic.rowsFrom([]), []);

const view = logic.customerView({
  reference: 8,
  category: 'Electrician',
  description: 'Fan repair',
  status: 'assigned',
  radius_km: 15,
  contact_email: 'secret@example.com',
  access_key: 'raw-key',
  access_key_hash: 'hash',
  payment_state: 'mock_recorded',
  assigned_profile: {
    id: 3,
    display_name: 'Asha Rao',
    skills: ['Wiring'],
    district: 'Mandya',
    locality: 'Town centre',
    phone_number: '9000000000',
    latitude: '12.000000',
  },
});
assert.equal(view.reference, 8);
assert.equal(view.category, 'Electrician');
assert.equal(view.assigned_profile.locality, 'Town centre');
assert.equal(Object.hasOwn(view, 'contact_email'), false);
assert.equal(Object.hasOwn(view, 'access_key'), false);
assert.equal(Object.hasOwn(view, 'payment_state'), false);
assert.equal(Object.hasOwn(view.assigned_profile, 'phone_number'), false);
assert.equal(Object.hasOwn(view.assigned_profile, 'latitude'), false);

const offer = logic.offerView({
  id: 5,
  state: 'offered',
  request: {
    reference: 8,
    category: 'Electrician',
    description: 'Fan repair',
    status: 'offering',
    radius_km: 15,
    contact_email: 'secret@example.com',
  },
});
assert.equal(Object.hasOwn(offer.request, 'contact_email'), false);
assert.equal(logic.listState(null, [], 'You have no daily service requests.').kind, 'empty');
assert.equal(logic.listState(null, [offer], 'You have no offers.').kind, 'ready');
assert.equal(logic.listState({ status: 500, data: null }, [], 'unused').kind, 'error');
assert.match(logic.errorText(new TypeError('Failed to fetch')), /could not be reached/);
assert.match(logic.errorText({ status: 401, data: {} }), /Sign in again/);
assert.equal(logic.errorText({ status: 403, data: { detail: 'Only customer accounts can view their daily service requests.' } }), 'Only customer accounts can view their daily service requests.');
assert.match(logic.errorText({ status: 400, data: { decision: ['This offer has already been answered.'] } }), /already been answered/);

assert.equal(logic.respondGate(true, offer, 'accept').ok, false);
assert.equal(logic.respondGate(false, { state: 'declined' }, 'accept').reason, 'closed');
assert.deepEqual(logic.respondGate(false, offer, 'decline').payload, { decision: 'decline' });

const updated = logic.applyResponse(offer, { state: 'accepted', request_status: 'assigned' });
assert.equal(updated.state, 'accepted');
assert.equal(updated.request.status, 'assigned');
assert.match(logic.responseText({ state: 'accepted' }), /No money was collected/);
assert.match(logic.responseText({ state: 'declined' }), /not paid again/);
assert.equal(logic.responseText({}).includes('Nothing was shown as updated'), true);
assert.equal(logic.arrivalSignalPath(8), '/workers/daily-requests/8/arrival/signal/');
assert.equal(logic.arrivalVerifyPath(8), '/workers/daily-requests/8/arrival/verify/');
assert.equal(logic.completePath(8), '/workers/daily-requests/8/complete/');
assert.deepEqual(logic.arrivalCodePayload(' 123456 '), { code: '123456' });
assert.equal(logic.canSignalArrival({
  state: 'accepted',
  request: { status: 'assigned', reference: 8 },
}), true);
assert.equal(logic.canSignalArrival({
  state: 'offered',
  request: { status: 'assigned', reference: 8 },
}), false);
assert.equal(logic.canVerifyArrival('assigned'), true);
assert.equal(logic.canComplete('in_progress', '2026-01-01T00:00:00Z'), true);
assert.equal(logic.canComplete('assigned', ''), false);
const identified = logic.customerView({
  reference: 9,
  category: 'Electrician',
  description: 'Fan repair',
  status: 'assigned',
  radius_km: 15,
  worker_identity: {
    worker_id: 'KDABC',
    profile_id: 3,
    display_name: 'Asha Rao',
    photo_url: 'https://cdn.example/a.jpg',
    identity_verified: true,
    skills: ['Wiring'],
    phone_number: '9000000000',
    rating_average: 4.9,
    latitude: '12.1',
    completed_jobs: 2,
    locality: 'Town centre',
    district: 'Mandya',
  },
});
assert.equal(identified.worker_identity.worker_id, 'KDABC');
assert.equal(identified.worker_identity.identity_verified, true);
assert.equal(identified.worker_identity.photo_url, 'https://cdn.example/a.jpg');
assert.equal(identified.worker_identity.completed_jobs, 2);
assert.equal(Object.hasOwn(identified.worker_identity, 'phone_number'), false);
assert.equal(Object.hasOwn(identified.worker_identity, 'rating_average'), false);
assert.equal(Object.hasOwn(identified.worker_identity, 'latitude'), false);

console.log('daily account logic tests passed');
