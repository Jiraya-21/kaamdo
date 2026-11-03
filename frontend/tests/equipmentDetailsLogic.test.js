const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/equipmentDetailsLogic.js');

assert.equal(logic.detailPath(4), '/equipment/4/');
assert.equal(logic.bookingPath(4), '/equipment/4/bookings/');
assert.equal(logic.inquiryPath(4), '/equipment/4/inquiries/');

const booking = logic.bookingPayload({
  startDate: '2026-11-02',
  endDate: '2026-11-04',
  note: '  Morning  delivery  ',
});
assert.deepEqual(booking, {
  start_date: '2026-11-02',
  end_date: '2026-11-04',
  note: 'Morning delivery',
});
assert.equal(Object.hasOwn(booking, 'status'), false);
assert.deepEqual(logic.bookingProblems({
  startDate: '2026-11-02',
  endDate: '2026-11-04',
  note: '',
}), []);
assert.ok(logic.bookingProblems({
  startDate: '2026-11-04',
  endDate: '2026-11-02',
  note: '',
}).includes('The end date cannot be before the start date.'));
assert.ok(logic.bookingProblems({
  startDate: '2026-02-31',
  endDate: '2026-03-01',
  note: '',
}).includes('Enter a start date.'));

const inquiry = logic.inquiryPayload({
  requirement: ' Need a tractor ',
  preferredTiming: ' Next week ',
});
assert.deepEqual(inquiry, {
  requirement: 'Need a tractor',
  preferred_timing: 'Next week',
});
assert.equal(Object.hasOwn(inquiry, 'contact_phone'), false);
assert.deepEqual(logic.inquiryProblems({ requirement: 'Need a tractor', preferredTiming: '' }), []);
assert.ok(logic.inquiryProblems({ requirement: '   ', preferredTiming: '' }).includes('Describe what you need.'));

assert.equal(logic.bookingResult({ id: 3, status: 'requested' }).ok, true);
assert.match(logic.bookingResult({ id: 3, status: 'requested' }).text, /no money was collected/i);
assert.equal(logic.bookingResult({ id: 3, status: 'accepted' }).ok, false);
assert.equal(logic.inquiryResult({ id: 8, status: 'new' }).ok, true);
assert.match(logic.inquiryResult({ id: 8, status: 'new' }).text, /does not reserve/i);
assert.equal(logic.inquiryResult({ id: 8, status: 'closed' }).ok, false);
assert.match(logic.errorText({ status: 400, data: { detail: 'Verify your mobile number before sending an inquiry.' } }), /Verify your mobile/);
assert.equal(
  logic.needsPhoneCheck({ status: 400, data: { detail: 'Verify your mobile number before sending an inquiry.' } }),
  true,
);
assert.equal(logic.needsPhoneCheck({ status: 400, data: { detail: 'Choose dates.' } }), false);
assert.equal(logic.INQUIRY_OTP_PURPOSE, 'equipment_inquiry');
assert.equal(logic.otpSendResult({ delivery: 'development', dev_code: '123456' }).ok, true);
assert.equal(logic.otpSendResult({ delivery: 'development', dev_code: '123456' }).devCode, '123456');
assert.equal(logic.otpSendResult({ delivery: 'sms' }).ok, true);
assert.equal(
  logic.otpSendResult({ delivery: 'sms' }).text.includes('OTP sent to your mobile'),
  true,
);
assert.equal(logic.otpSendResult({ detail: 'SMS delivery is not configured. No code was sent.' }).ok, false);
assert.match(logic.errorText(new TypeError('Failed to fetch')), /could not be reached/);

console.log('equipment details logic tests passed');
