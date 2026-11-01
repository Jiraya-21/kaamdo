const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/workerDirectoryLogic.js');

assert.equal(logic.LIST_PATH, '/workers/');
assert.deepEqual(logic.params({
  query: '  Older  ',
  district: 'All',
  category: 'all',
  skill: '',
  latitude: '',
  longitude: '',
  radiusKm: '20',
}), { q: 'Older' });

assert.deepEqual(logic.params({
  query: '',
  district: 'Mysuru',
  category: 'electrician',
  skill: 'Wiring',
  latitude: '12',
  longitude: '77',
  radiusKm: '10',
}), {
  district: 'Mysuru',
  category: 'electrician',
  skill: 'Wiring',
  latitude: '12.000000',
  longitude: '77.000000',
  radius_km: '10',
});

assert.equal(Object.hasOwn(logic.params({
  query: '',
  district: '',
  category: '',
  skill: '',
  latitude: '12',
  longitude: '',
  radiusKm: '10',
}), 'latitude'), false);

assert.deepEqual(logic.searchFromLocation('?q=Electrician&loc=Mandya'), {
  query: 'Electrician',
  district: 'Mandya',
});
assert.deepEqual(logic.searchFromLocation('?q=Plumber&district=Mysuru&loc=Mandya'), {
  query: 'Plumber',
  district: 'Mysuru',
});
assert.deepEqual(logic.searchFromLocation('?loc=All'), { query: '', district: '' });
assert.equal(logic.photoSrc('https://api.example/media/a.jpg'), 'https://api.example/media/a.jpg');
assert.equal(logic.photoSrc(''), logic.DEFAULT_AVATAR);
assert.equal(logic.photoSrc('javascript:alert(1)'), logic.DEFAULT_AVATAR);

console.log('worker directory logic tests passed');
