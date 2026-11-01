const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/jobDetailsLogic.js');

assert.deepEqual(logic.paths('ordinary', 4), {
  job: '/jobs/4/',
  apply: '/jobs/4/applications/',
  listHref: 'jobs-list.html',
  listLabel: 'Back to jobs',
});
assert.equal(logic.paths('agricultural', 9).job, '/jobs/agricultural/9/');
assert.equal(logic.paths('agricultural', 9).apply, '/jobs/agricultural/9/applications/');
assert.equal(logic.scheduleText({
  work_start: '2026-11-01',
  work_end: '2026-11-10',
  working_hours: '6am to 11am',
}), 'Starts 2026-11-01. Ends 2026-11-10. 6am to 11am');
assert.equal(logic.scheduleText({}), '');

console.log('job details logic tests passed');
