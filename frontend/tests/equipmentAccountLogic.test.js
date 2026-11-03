const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const logic = require('../assets/js/pages/equipmentAccountLogic.js');

assert.equal(logic.LISTING_FORM_PATH, '../jobs/post-job.html#equipment');
assert.equal(logic.LISTINGS_PATH, '/equipment/mine/');
assert.equal(logic.listingBookingsPath(4), '/equipment/4/bookings/');
assert.equal(logic.listingInquiriesPath(4), '/equipment/4/inquiries/');
assert.equal(logic.bookingDecisionPath(9), '/equipment/bookings/9/');
assert.equal(logic.inquiryDecisionPath(3), '/equipment/inquiries/3/');
assert.deepEqual(logic.decisionPayload('accepted'), { status: 'accepted' });
assert.deepEqual(logic.decisionPayload('seen'), { status: 'seen' });
assert.deepEqual(logic.bookingActions({ status: 'requested' }), ['accepted', 'declined']);
assert.deepEqual(logic.bookingActions({ status: 'accepted' }), []);
assert.deepEqual(logic.inquiryActions({ status: 'new' }), ['closed']);
assert.deepEqual(logic.inquiryActions({ status: 'seen' }), ['closed']);
assert.deepEqual(logic.inquiryActions({ status: 'closed' }), []);
assert.match(logic.decisionResult({ id: 9, status: 'declined' }, 'booking').text, /does not collect money/i);
assert.match(logic.decisionResult({ id: 3, status: 'seen' }, 'inquiry').text, /does not reserve/i);
assert.equal(logic.decisionResult({ status: 'accepted' }, 'booking').ok, false);

const accountJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/equipmentAccount.js'), 'utf8');
assert.match(accountJs, /LISTING_FORM_PATH/);
assert.match(accountJs, /equip\.addListing/);

console.log('equipment account logic tests passed');
