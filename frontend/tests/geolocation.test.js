const assert = require('node:assert/strict');
const geo = require('../assets/js/utils/geolocation.js');

assert.equal(geo.coordinateText('12.971891887766543'), '12.971892');
assert.equal(geo.coordinateText('77.59456634567891'), '77.594566');
assert.equal(geo.coordinateText('12.5'), '12.500000');
assert.equal(geo.coordinateText('not-a-number'), '');
assert.equal(geo.coordinateText(''), '');
assert.equal(geo.coordinateText(null), '');

console.log('geolocation tests passed');
