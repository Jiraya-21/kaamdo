const assert = require('node:assert/strict');
const LocationFields = require('../assets/js/pages/locationFields.js');

assert.equal(LocationFields.CATALOG_PATH, '/locations/catalog/');
assert.equal(LocationFields.placeLabel('Town centre', 'Mandya', 'Mandya'), 'Town centre, Mandya');
assert.equal(LocationFields.placeLabel('Town centre', 'Maddur', 'Mandya'), 'Town centre, Maddur, Mandya');
assert.equal(LocationFields.placeLabel('', '', ''), '');
assert.deepEqual(
  LocationFields.taluksFor({
    districts: [{ name: 'Bengaluru South', taluks: ['Harohalli', 'Magadi'] }],
  }, 'Bengaluru South'),
  ['Harohalli', 'Magadi'],
);
assert.deepEqual(LocationFields.taluksFor({ districts: [] }, 'Invented'), []);

console.log('location field tests passed');
