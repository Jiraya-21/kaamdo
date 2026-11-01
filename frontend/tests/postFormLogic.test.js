const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/postFormLogic.js');

const jobValues = {
  title: 'Shop assistant',
  description: 'Help customers and keep the counter.',
  district: 'Mandya',
  taluk: 'Mandya',
  locality: 'Town centre',
  workType: 'temporary',
  wageAmount: '500.00',
  wageNegotiable: false,
  wagePeriod: 'daily',
  headcount: '1',
};

const listingValues = {
  title: 'Small tractor',
  description: 'Available for field work near town.',
  district: 'Mandya',
  taluk: 'Mandya',
  locality: 'Town centre',
  pricingBasis: 'daily',
  rate: '850.00',
  operatorIncluded: false,
  availabilityNote: 'Weekday mornings',
};

const job = logic.jobPayload(jobValues);
assert.equal(logic.JOB_PATH, '/jobs/');
assert.equal(job.status, 'published');
assert.equal(job.taluk, 'Mandya');
assert.equal(job.work_type, 'temporary');
assert.equal(job.wage_amount, '500.00');
assert.equal(job.wage_negotiable, false);
assert.equal(job.headcount, 1);
assert.deepEqual(logic.jobProblems(jobValues), []);

const negotiable = logic.jobPayload({ ...jobValues, wageNegotiable: true, wageAmount: '' });
assert.equal(negotiable.wage_negotiable, true);
assert.equal(Object.hasOwn(negotiable, 'wage_amount'), false);
assert.deepEqual(logic.jobProblems({ ...jobValues, title: '  ' }), ['Title is required.']);
assert.ok(logic.jobProblems({ ...jobValues, wageAmount: '0', wageNegotiable: false }).length > 0);

const pending = logic.jobResult({ id: 4, status: 'draft', review_status: 'pending' });
assert.equal(pending.ok, true);
assert.equal(pending.text.includes('published'), false);
assert.equal(pending.text.includes('staff review'), true);
const published = logic.jobResult({ id: 4, status: 'published', review_status: 'approved' });
assert.equal(published.text, 'Job saved. It is published.');
assert.equal(logic.jobResult({ status: 'published' }).ok, false);

const listing = logic.equipmentPayload(listingValues);
assert.equal(logic.EQUIPMENT_PATH, '/equipment/');
assert.equal(listing.status, 'draft');
assert.equal(listing.pricing_basis, 'daily');
assert.equal(listing.rate, '850.00');
assert.equal(Object.hasOwn(listing, 'category'), false);
assert.equal(Object.hasOwn(listing, 'image'), false);
assert.deepEqual(logic.equipmentProblems(listingValues), []);
assert.ok(logic.equipmentProblems({ ...listingValues, rate: '0' }).some((item) => item.includes('rate')));

const draft = logic.equipmentResult({ id: 8, status: 'draft', fee_status: 'unpaid' });
assert.equal(draft.ok, true);
assert.equal(draft.text.includes('published'), false);
assert.equal(draft.text.includes('listing fee'), true);
assert.equal(logic.equipmentResult(null).ok, false);

assert.equal(logic.errorText(new TypeError('Failed to fetch')).includes('Nothing was saved'), true);
assert.equal(logic.errorText({ status: 401, data: { detail: 'Authentication credentials were not provided.' } }).includes('Nothing was saved'), true);
assert.equal(logic.errorText({ status: 403, data: { detail: 'Only employer accounts can manage ordinary job posts.' } }), 'Only employer accounts can manage ordinary job posts.');
assert.equal(logic.errorText({ status: 400, data: { wage_amount: ['Enter a wage, or mark the wage as negotiable.'] } }).includes('wage_amount'), true);
assert.equal(logic.errorText({ status: 500, data: null }).includes('Nothing was saved'), true);

const farmValues = {
  title: 'Paddy harvest',
  description: 'Five days of transplanting.',
  district: 'Mandya',
  taluk: 'Mandya',
  locality: 'Town centre',
  wageAmount: '500.00',
  wageNegotiable: false,
  wagePeriod: 'daily',
  headcount: '4',
  workStart: '2026-11-02',
  workEnd: '2026-11-06',
  workingHours: ' 7am to 1pm ',
};
const farm = logic.farmPayload(farmValues);
assert.equal(logic.FARM_PATH, '/jobs/agricultural/');
assert.equal(farm.status, 'published');
assert.equal(farm.work_start, '2026-11-02');
assert.equal(farm.work_end, '2026-11-06');
assert.equal(farm.working_hours, '7am to 1pm');
assert.equal(Object.hasOwn(farm, 'work_type'), false);
assert.deepEqual(logic.farmProblems(farmValues), []);
assert.equal(Object.hasOwn(logic.farmPayload({ ...farmValues, workStart: '', workEnd: '' }), 'work_start'), false);
assert.ok(logic.farmProblems({ ...farmValues, workEnd: '2026-11-01' }).some((item) => item.includes('end date')));
assert.equal(logic.farmApplyPath(12), '/jobs/agricultural/12/applications/');
assert.equal(logic.farmResult({ id: 2, status: 'draft', review_status: 'pending' }).text.includes('staff review'), true);

console.log('post form logic tests passed');
