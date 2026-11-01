const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/jobListLogic.js');

assert.equal(logic.LIST_PATH, '/jobs/');
assert.deepEqual(logic.params({ query: '  shop  ', district: 'All', workType: '' }), { q: 'shop' });
assert.deepEqual(logic.params({
  query: '',
  district: 'Mysuru',
  workType: 'full_time',
}), { district: 'Mysuru', work_type: 'full_time' });
assert.deepEqual(logic.params({ query: '', district: '', workType: 'seasonal' }), {});
assert.equal(logic.wageText({ wage_negotiable: true }), 'Wage: negotiable');
assert.equal(logic.wageText({ wage_amount: '500.00', wage_period: 'daily' }), 'Wage: 500.00 daily');

console.log('job list logic tests passed');
