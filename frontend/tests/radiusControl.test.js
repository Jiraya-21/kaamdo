const assert = require('node:assert/strict');
const RadiusControl = require('../assets/js/pages/radiusControl.js');

assert.equal(RadiusControl.MIN, 5);
assert.equal(RadiusControl.MAX, 100);
assert.equal(RadiusControl.STEP, 5);
assert.equal(RadiusControl.DEFAULT, 60);
assert.equal(RadiusControl.snap(''), 60);
assert.equal(RadiusControl.snap(7), 5);
assert.equal(RadiusControl.snap(8), 10);
assert.equal(RadiusControl.snap(60), 60);
assert.equal(RadiusControl.snap(97), 95);
assert.equal(RadiusControl.snap(101), 100);
assert.equal(RadiusControl.label(60), '60 km');
assert.deepEqual(RadiusControl.problems(60), []);
assert.deepEqual(RadiusControl.problems(5), []);
assert.deepEqual(RadiusControl.problems(100), []);
assert.ok(RadiusControl.problems(8).length > 0);
assert.ok(RadiusControl.problems(4).length > 0);
assert.ok(RadiusControl.problems(101).length > 0);

console.log('radius control tests passed');
