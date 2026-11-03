const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const AccountWorkspace = require('../assets/js/account/workspace.js');

const items = [
  { code: 'equipment_owner', page: 'equipment/rental.html' },
  { code: 'equipment_renter', page: 'equipment/rental.html' },
  { code: 'job_seeker', page: 'jobs/seeker.html' },
];

assert.equal(
  AccountWorkspace.href(items[0]),
  '../equipment/rental.html?workspace=equipment_owner',
);
assert.equal(AccountWorkspace.href({}), '../dashboard/dashboard.html');
assert.equal(AccountWorkspace.fromQuery('?workspace=equipment_owner'), 'equipment_owner');
assert.equal(AccountWorkspace.fromQuery('workspace=job-seeker'), '');
assert.equal(AccountWorkspace.fromQuery(''), '');
assert.deepEqual(
  AccountWorkspace.pick(items, '', ['equipment_owner', 'job_seeker']).map((item) => item.code),
  ['equipment_owner', 'job_seeker'],
);
assert.deepEqual(
  AccountWorkspace.pick(items, 'equipment_owner', ['equipment_owner', 'equipment_renter']).map((item) => item.code),
  ['equipment_owner'],
);
assert.deepEqual(
  AccountWorkspace.pick(items, 'equipment_owner', ['job_seeker']),
  [],
);

const dashboardJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/dashboard.js'), 'utf8');
const dashboardHtml = fs.readFileSync(path.join(__dirname, '../pages/dashboard/dashboard.html'), 'utf8');
const areaJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/area.js'), 'utf8');
const catalogJs = fs.readFileSync(path.join(__dirname, '../assets/js/account/catalog.js'), 'utf8');
const customerHtml = fs.readFileSync(path.join(__dirname, '../pages/services/customer.html'), 'utf8');
const providerJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/serviceRequestAccount.js'), 'utf8');
const WorkerIdentityCard = require('../assets/js/components/workerIdentityCard.js');
assert.match(dashboardJs, /AccountCatalog\.workspaceHref/);
assert.match(dashboardJs, /ProviderStatusLogic\.isProvider/);
assert.match(dashboardJs, /renderRoles/);
assert.match(dashboardJs, /renderMarketplaces/);
assert.match(dashboardJs, /mountAvailability/);
assert.match(dashboardJs, /renderAvailability/);
assert.match(dashboardJs, /account-alert/);
assert.match(dashboardJs, /retry:\s*true/);
assert.match(dashboardHtml, /id="role-list"/);
assert.match(dashboardHtml, /id="marketplace-list"/);
assert.match(dashboardHtml, /id="hub-availability"/);
assert.match(dashboardHtml, /id="account-avatar"/);
assert.match(dashboardHtml, /id="account-logout"/);
assert.match(dashboardHtml, /id="account-alert"/);
assert.match(dashboardHtml, /hub\.firstArea/);
assert.equal(dashboardHtml.includes('id="activity-list"'), false);
assert.equal(dashboardHtml.includes('id="provider-status"'), false);
assert.equal(/code:\s*'customer'/.test(catalogJs), false);
assert.match(catalogJs, /marketplaces/);
assert.match(catalogJs, /services\/customer\.html/);
assert.match(catalogJs, /jobs\/jobs-list\.html/);
assert.match(catalogJs, /equipment\/equipment-list\.html/);
assert.match(catalogJs, /jobs\/farm-jobs\.html/);
assert.match(catalogJs, /service_provider/);
assert.match(catalogJs, /agricultural_employer/);
assert.match(customerHtml, /My service requests/);
assert.match(areaJs, /AccountWorkspace\.fromQuery/);
assert.match(areaJs, /showChooser/);
assert.match(areaJs, /activityForPage/);
assert.match(areaJs, /customer-direct/);
assert.equal(areaJs.includes("item.code === 'customer'"), false);
assert.equal(areaJs.includes('DailyAccount.mountProvider(card)'), false);
assert.match(providerJs, /mountWorkspaceTabs/);
assert.match(providerJs, /workspace.tabOffers/);
const card = WorkerIdentityCard.normalize({
  worker_identity: {
    worker_id: 'KD123',
    display_name: 'Asha',
    photo_url: 'https://cdn.example/a.jpg',
    identity_verified: true,
    phone_number: '9000000000',
    rating_average: 5,
    review_count: 4,
    latitude: '12.1',
    skills: ['Wiring'],
    completed_jobs: 2,
  },
});
assert.equal(card.worker_id, 'KD123');
assert.equal(card.identity_verified, true);
assert.equal(card.photo_url, 'https://cdn.example/a.jpg');
assert.equal(card.skill_verified, false);
assert.equal(card.completed_jobs, 2);
assert.equal(Object.hasOwn(card, 'phone_number'), false);
assert.equal(Object.hasOwn(card, 'rating_average'), false);
assert.equal(Object.hasOwn(card, 'latitude'), false);

console.log('workspace tests passed');
