const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const LocationDetect = require('../assets/js/pages/locationDetect.js');

const guestHtml = fs.readFileSync(path.join(__dirname, '../pages/services/guest-request.html'), 'utf8');
const postHtml = fs.readFileSync(path.join(__dirname, '../pages/jobs/post-job.html'), 'utf8');
const farmJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/farmHiring.js'), 'utf8');
const dailyJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/dailyAccount.js'), 'utf8');
const postJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/postJob.js'), 'utf8');
const guestJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/guestService.js'), 'utf8');

assert.equal(guestHtml.includes('location-confirm'), false);
assert.equal(postHtml.includes('location-confirm'), false);
assert.equal(farmJs.includes('confirmHost'), false);
assert.equal(dailyJs.includes('confirmHost'), false);
assert.equal(postJs.includes('confirmHost'), false);
assert.equal(guestJs.includes('confirmHost'), false);
assert.match(guestHtml, /id="request-state"/);
assert.match(guestHtml, /id="request-district"/);
assert.match(guestHtml, /id="guest-locate"/);
assert.match(postHtml, /id="job-locate"/);
assert.match(postHtml, /id="equip-locate"/);
assert.match(farmJs, /LocationDetect\.bind/);
assert.match(dailyJs, /LocationDetect\.detect/);

async function runDetectCase() {
  const locality = { value: '', dataset: {} };
  const district = { value: '' };
  const taluk = { value: '' };
  const status = { textContent: '', classList: { remove() {}, add() {} } };
  const fields = { district, taluk, locality, latitude: { value: '' }, longitude: { value: '' } };

  global.GeolocationUtil = {
    async getCurrentCoordinates() {
      return { latitude: 12.52, longitude: 76.89 };
    },
    coordinateText(value) { return String(value); },
  };
  global.ApiClient = {
    async post() {
      return {
        available: true,
        state: 'Karnataka',
        district: 'Mandya',
        taluk: 'Maddur',
        locality: 'Town centre',
        display: 'Town centre, Maddur, Mandya',
      };
    },
  };

  const first = await LocationDetect.detect({ fields, status });
  assert.equal(first.keptEdits, false);
  assert.equal(locality.value, 'Town centre');
  assert.equal(locality.dataset.autoFilled, '1');
  assert.equal(fields.latitude.value, '12.52');

  locality.value = 'My typed place';
  delete locality.dataset.autoFilled;
  const kept = await LocationDetect.detect({ fields, status });
  assert.equal(kept.keptEdits, false);
  assert.equal(locality.value, 'My typed place');

  // Delayed response must not overwrite newer edits.
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  global.ApiClient = {
    async post() {
      await gate;
      return {
        available: true,
        district: 'OldDistrict',
        taluk: 'OldTaluk',
        locality: 'Stale GPS',
        display: 'Stale GPS',
      };
    },
  };
  const pending = LocationDetect.detect({ fields, status });
  locality.value = 'Edited while waiting';
  release();
  const stale = await pending;
  assert.equal(stale.keptEdits, true);
  assert.equal(locality.value, 'Edited while waiting');
}

runDetectCase().then(() => {
  console.log('location detect flow tests passed');
}).catch((error) => {
  console.error(error);
  process.exit(1);
});
