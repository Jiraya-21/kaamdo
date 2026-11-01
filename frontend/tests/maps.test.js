const assert = require('node:assert/strict');
const KaamdoMap = require('../assets/js/utils/maps.js');

assert.equal(KaamdoMap.CONFIG_PATH, '/locations/map-config/');
const off = KaamdoMap.parse({ provider: 'nominatim', enabled: true, autocomplete: true });
assert.equal(off.provider, 'none');
assert.equal(off.enabled, false);
assert.equal(off.nominatimAutocomplete, false);
assert.equal(off.inventedCentroids, false);

const on = KaamdoMap.parse({
  provider: 'osm',
  enabled: true,
  attribution: 'Map data © OpenStreetMap contributors',
});
assert.equal(on.enabled, true);
assert.match(KaamdoMap.noteText(on, true), /OpenStreetMap/);
assert.match(KaamdoMap.noteText(on, false), /does not invent/);
assert.match(KaamdoMap.noteText(off, false), /No public map/);

console.log('map config tests passed');
