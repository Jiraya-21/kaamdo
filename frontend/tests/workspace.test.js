const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const AccountWorkspace = require('../assets/js/account/workspace.js');

const items = [
  { code: 'equipment_owner', page: 'equipment/rental.html' },
  { code: 'equipment_renter', page: 'equipment/rental.html' },
  { code: 'customer', page: 'services/customer.html' },
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
  AccountWorkspace.pick(items, '', ['equipment_owner', 'customer']).map((item) => item.code),
  ['equipment_owner', 'customer'],
);
assert.deepEqual(
  AccountWorkspace.pick(items, 'equipment_owner', ['equipment_owner', 'equipment_renter']).map((item) => item.code),
  ['equipment_owner'],
);
assert.deepEqual(
  AccountWorkspace.pick(items, 'equipment_owner', ['customer']),
  [],
);

const dashboardJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/dashboard.js'), 'utf8');
const dashboardHtml = fs.readFileSync(path.join(__dirname, '../pages/dashboard/dashboard.html'), 'utf8');
const areaJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/area.js'), 'utf8');
const providerJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/serviceRequestAccount.js'), 'utf8');
assert.match(dashboardJs, /AccountCatalog\.workspaceHref/);
assert.match(dashboardJs, /ProviderStatusLogic\.isProvider/);
assert.match(dashboardJs, /renderRoles/);
assert.match(dashboardHtml, /id="role-list"/);
assert.match(dashboardHtml, /id="provider-status"/);
assert.match(dashboardHtml, /id="account-avatar"/);
assert.equal(dashboardHtml.includes('id="account-logout"'), false);
assert.match(areaJs, /AccountWorkspace\.fromQuery/);
assert.match(areaJs, /showChooser/);
assert.match(areaJs, /customer-direct/);
assert.equal(areaJs.includes('DailyAccount.mountProvider(card)'), false);
assert.match(providerJs, /mountWorkspaceTabs/);
assert.match(providerJs, /workspace.tabOffers/);

console.log('workspace tests passed');
