const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/equipmentListLogic.js');

assert.equal(logic.LIST_PATH, '/equipment/');
assert.deepEqual(logic.params({
  query: '  tractor  ',
  district: 'All',
  pricingBasis: '',
  operatorIncluded: '',
}), { q: 'tractor' });
assert.deepEqual(logic.params({
  query: '',
  district: 'Mysuru',
  pricingBasis: 'daily',
  operatorIncluded: 'false',
}), { district: 'Mysuru', pricing_basis: 'daily', operator_included: 'false' });
assert.deepEqual(logic.params({
  query: '',
  district: '',
  pricingBasis: 'weekly',
  operatorIncluded: 'maybe',
}), {});
assert.equal(logic.rateText({ rate: '500.00', pricing_basis: 'hourly' }), '500.00 hourly');

console.log('equipment list logic tests passed');
