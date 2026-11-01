const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/jobAccountLogic.js');

assert.equal(logic.ORDINARY.mine, '/jobs/mine/');
assert.equal(logic.ORDINARY.jobApplications(4), '/jobs/4/applications/');
assert.equal(logic.ORDINARY.application(9), '/jobs/applications/9/');
assert.equal(logic.ORDINARY.decision(4, 9), '/jobs/4/applications/9/');
assert.equal(logic.FARM.mine, '/jobs/agricultural/mine/');
assert.equal(logic.FARM.application(3), '/jobs/agricultural/applications/3/');
assert.equal(logic.FARM.decision(2, 3), '/jobs/agricultural/2/applications/3/');

const job = logic.jobView({
  id: 2,
  title: 'Shop assistant',
  status: 'draft',
  review_status: 'pending',
  district: 'Mandya',
  locality: 'Town centre',
  phone_number: '9000000000',
});
assert.equal(job.title, 'Shop assistant');
assert.equal(Object.hasOwn(job, 'phone_number'), false);

const application = logic.applicationView({
  id: 8,
  job: 2,
  job_title: 'Shop assistant',
  job_status: 'published',
  job_district: 'Mandya',
  job_locality: 'Town centre',
  applicant_name: 'Meera Naik',
  message: 'I can start Monday.',
  status: 'submitted',
  created_at: '2026-10-21T10:00:00Z',
  phone_number: '9000000822',
});
assert.equal(application.applicant_name, 'Meera Naik');
assert.equal(Object.hasOwn(application, 'phone_number'), false);
assert.equal(logic.listState(null, [], 'You have no posts yet.').kind, 'empty');
assert.equal(logic.listState({ status: 500, data: null }, [], 'unused').kind, 'error');
assert.equal(logic.withdrawGate(true, application).ok, false);
assert.equal(logic.withdrawGate(false, { status: 'withdrawn' }).reason, 'closed');
assert.deepEqual(logic.withdrawGate(false, application).payload, { status: 'withdrawn' });
assert.equal(logic.applyWithdraw(application, { status: 'withdrawn' }).status, 'withdrawn');
assert.equal(logic.ORDINARY.detail(4), '/jobs/4/');
assert.equal(logic.FARM.detail(2), '/jobs/agricultural/2/');
assert.deepEqual(logic.closeGate(false, { status: 'published' }).payload, { status: 'closed' });
assert.equal(logic.closeGate(false, { status: 'closed' }).ok, false);
assert.deepEqual(logic.employerActions(application), ['accepted', 'rejected']);
assert.deepEqual(logic.employerActions({ status: 'accepted' }), []);
assert.equal(logic.decisionGate(true, application, 'accepted').ok, false);
assert.equal(logic.decisionGate(false, { status: 'withdrawn' }, 'accepted').reason, 'closed');
assert.deepEqual(logic.decisionGate(false, application, 'accepted').payload, { status: 'accepted' });
assert.equal(logic.decisionGate(false, application, 'published').reason, 'invalid');
assert.match(logic.errorText(new TypeError('Failed to fetch')), /could not be reached/);
assert.equal(
  logic.errorText({ status: 403, data: { detail: 'Only employer accounts can manage ordinary job posts.' } }),
  'Only employer accounts can manage ordinary job posts.',
);

console.log('job account logic tests passed');
