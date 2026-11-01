const assert = require('node:assert/strict');
const distance = require('../assets/js/utils/distance.js');

assert.equal(distance.between(12, 77, 12, 77), 0);
assert.equal(distance.between(null, 77, 12, 77), null);
const north = distance.between(12, 77, 12.09, 77);
assert.ok(north > 9 && north < 11);

console.log('distance tests passed');
