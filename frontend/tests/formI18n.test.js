const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const guestHtml = fs.readFileSync(
  path.join(__dirname, '../pages/services/guest-request.html'),
  'utf8',
);
const guestJs = fs.readFileSync(
  path.join(__dirname, '../assets/js/pages/guestService.js'),
  'utf8',
);
const dailyJs = fs.readFileSync(
  path.join(__dirname, '../assets/js/pages/dailyAccount.js'),
  'utf8',
);
const postHtml = fs.readFileSync(
  path.join(__dirname, '../pages/jobs/post-job.html'),
  'utf8',
);

assert.match(guestHtml, /data-guest-step="service"/);
assert.match(guestHtml, /id="service-catalogue"/);
assert.match(guestHtml, /id="guest-details-section"[^>]*hidden/);
assert.match(guestHtml, /id="guest-review-section"[^>]*hidden/);
assert.match(guestJs, /aria-hidden/);
assert.match(guestHtml, /otpUi\.js/);
assert.match(guestHtml, /id="guest-phone-fields"/);
assert.equal(guestHtml.includes('id="manual-location-fields"'), false);
assert.match(guestHtml, /id="request-district"/);
assert.equal(guestHtml.includes('type="number" id="request-latitude"'), false);
assert.equal(guestHtml.includes('id="guest-status-form"'), false);
assert.match(guestJs, /showStep\('service'\)/);
assert.match(guestJs, /showSignedInHint/);
assert.match(guestJs, /renderCatalogue/);
assert.match(dailyJs, /type = 'hidden'/);
assert.equal(dailyJs.includes("labeled('Latitude'"), false);
assert.equal(dailyJs.includes("labeled('Longitude'"), false);
assert.match(dailyJs, /daily.place/);
assert.match(postHtml, /data-i18n="form.jobHeading"/);
assert.match(postHtml, /data-i18n="form.equipHeading"/);
assert.match(postHtml, /data-i18n="form.submitJob"/);
const dashboardHtml = fs.readFileSync(
  path.join(__dirname, '../pages/dashboard/dashboard.html'),
  'utf8',
);
assert.match(dashboardHtml, /id="role-list"/);
assert.match(dashboardHtml, /id="provider-status"/);
assert.match(dashboardHtml, /id="test-payment-banner"/);
assert.match(dashboardHtml, /account\/workspace\.js/);
assert.match(dashboardHtml, /providerStatus\.js/);
assert.equal(dashboardHtml.includes('id="mode-switcher"'), false);
assert.equal(dashboardHtml.includes('id="account-logout"'), false);
assert.match(postHtml, /class="form-two-col"/);
assert.match(postHtml, /account\/session\.js/);
assert.equal(postHtml.includes('grid-template-columns:1fr 1fr'), false);

const bookingJs = fs.readFileSync(
  path.join(__dirname, '../assets/js/components/bookingFlow.js'),
  'utf8',
);
const listHtml = fs.readFileSync(
  path.join(__dirname, '../pages/equipment/equipment-list.html'),
  'utf8',
);
assert.match(bookingJs, /BookingFlowLogic\.sendResult/);
assert.equal(bookingJs.includes('Enter the verification code to continue'), false);
assert.match(bookingJs, /booking\.noCode/);
assert.equal(listHtml.includes('rent-equipment.html'), false);
assert.match(listHtml, /data-i18n="title.equipment"/);

const equipDetailsHtml = fs.readFileSync(
  path.join(__dirname, '../pages/equipment/equipment-details.html'),
  'utf8',
);
assert.match(equipDetailsHtml, /data-i18n="equipDetail.back"/);
assert.equal(equipDetailsHtml.includes('Back to Equipment'), false);
assert.match(equipDetailsHtml, /api\/authApi\.js/);
assert.match(equipDetailsHtml, /account\/session\.js/);

const registerHtml = fs.readFileSync(
  path.join(__dirname, '../pages/auth/register.html'),
  'utf8',
);
assert.match(registerHtml, /data-i18n="register.districtNote"/);
assert.equal(registerHtml.includes('<option>Mandya</option>'), false);
assert.equal(guestJs.includes("getElementById('status-reference').value = this.savedReference"), false);
assert.match(guestJs, /guest\.savedSummary/);

console.log('form i18n markup tests passed');
