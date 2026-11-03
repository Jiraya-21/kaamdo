const assert = require('node:assert/strict');
const LocationDetect = require('../assets/js/pages/locationDetect.js');

assert.equal(LocationDetect.REVERSE_PATH, '/locations/reverse/');
assert.equal(LocationDetect.gpsErrorKey({ code: 1 }), 'location.permissionDenied');
assert.equal(LocationDetect.gpsErrorKey({ code: 2 }), 'location.unavailable');
assert.equal(LocationDetect.gpsErrorKey({ code: 3 }), 'location.timeout');
assert.equal(
  LocationDetect.displayName({ locality: 'Town centre', taluk: 'Maddur', district: 'Mandya' }),
  'Town centre, Maddur, Mandya',
);
assert.equal(
  LocationDetect.displayName({
    street: 'Karve Road',
    locality: 'Kothrud',
    taluk: 'Haveli',
    district: 'Pune',
    postcode: '411038',
  }),
  'Karve Road, Kothrud, Haveli, Pune, 411038',
);
assert.equal(LocationDetect.displayName({ latitude: '12.52', longitude: '76.89' }), '');
assert.equal(
  LocationDetect.hasTypedPlace({
    district: { value: '' },
    taluk: { value: '' },
    locality: { value: 'Town', dataset: {} },
  }),
  true,
);
assert.equal(
  LocationDetect.hasTypedPlace({
    district: { value: '' },
    taluk: { value: '' },
    locality: { value: 'Town', dataset: { autoFilled: '1' } },
  }),
  false,
);

assert.equal(
  LocationDetect.fieldSnapshot({
    district: { value: 'Mandya' },
    taluk: { value: 'Maddur' },
    locality: { value: 'Town' },
  }),
  LocationDetect.fieldSnapshot({
    district: { value: ' Mandya ' },
    taluk: { value: 'Maddur' },
    locality: { value: 'Town' },
  }),
);
assert.notEqual(
  LocationDetect.fieldSnapshot({ locality: { value: 'A' } }),
  LocationDetect.fieldSnapshot({ locality: { value: 'B' } }),
);

const source = require('node:fs').readFileSync(
  require('node:path').join(__dirname, '../assets/js/pages/locationDetect.js'),
  'utf8',
);
assert.equal(source.includes('renderConfirm'), false);
assert.equal(source.includes('location.confirmUse'), false);
assert.equal(source.includes('location.keepManual'), false);
assert.equal(source.includes('location-confirm-title'), false);
assert.match(source, /detectToken/);
assert.match(source, /editedDuringWait|fieldSnapshot/);

console.log('location detect tests passed');
