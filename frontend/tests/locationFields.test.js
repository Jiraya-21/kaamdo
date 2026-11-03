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

const catalog = {
  state: { name: 'Karnataka' },
  districts: [{ name: 'Mandya', taluks: ['Maddur'] }],
  states: [
    {
      name: 'Karnataka',
      districts: [{ name: 'Mandya', taluks: ['Maddur', 'Mandya'] }],
    },
    {
      name: 'Maharashtra',
      districts: [
        { name: 'Pune', taluks: ['Haveli', 'Mulshi'] },
        { name: 'Mumbai City', taluks: [] },
      ],
    },
  ],
};
assert.deepEqual(LocationFields.stateNames(catalog), ['Karnataka', 'Maharashtra']);
assert.deepEqual(LocationFields.districtsFor(catalog, 'Maharashtra'), ['Pune', 'Mumbai City']);
assert.equal(LocationFields.districtsFor(catalog, '').includes('Pune'), true);
assert.equal(LocationFields.districtsFor(catalog, '').includes('Mandya'), true);
assert.deepEqual(LocationFields.taluksFor(catalog, 'Pune'), ['Haveli', 'Mulshi']);
assert.deepEqual(LocationFields.taluksFor(catalog, 'Mumbai City'), []);
assert.equal(LocationFields.stateForDistrict(catalog, 'Pune'), 'Maharashtra');
assert.equal(
  LocationFields.placeLabel('Karve Road', 'Kothrud', 'Haveli', 'Pune', '411038'),
  'Karve Road, Kothrud, Haveli, Pune, 411038',
);

console.log('location field tests passed');
