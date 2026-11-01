const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const store = new Map();
global.CONFIG = {
  STORAGE_KEYS: {
    AUTH_TOKEN: 'kaamdo_auth_token',
    USER_DATA: 'kaamdo_user_data',
    USER_ROLE: 'kaamdo_user_role',
  },
};
global.StorageUtil = {
  get(key) { return store.has(key) ? store.get(key) : null; },
  set(key, value) { store.set(key, value); },
  remove(key) { store.delete(key); },
};
global.AuthApi = {
  async getCurrentUser() {
    throw Object.assign(new Error('offline'), { status: undefined });
  },
  async logout() { return {}; },
};

const AccountSession = require('../assets/js/account/session.js');

assert.equal(AccountSession.hasCapability({ capabilities: ['customer'] }, 'customer'), true);
assert.equal(AccountSession.hasCapability({ capabilities: ['customer'] }, 'employer'), false);
assert.equal(AccountSession.hasCapability(null, 'customer'), false);

assert.equal(AccountSession.safeNextPath('/pages/workers/directory.html'), '/pages/workers/directory.html');
assert.equal(AccountSession.safeNextPath('//evil.example/phish'), '../dashboard/dashboard.html');
assert.equal(AccountSession.safeNextPath('https://evil.example'), '../dashboard/dashboard.html');
assert.equal(AccountSession.safeNextPath('/pages\\auth\\login.html'), '../dashboard/dashboard.html');
assert.equal(AccountSession.safeNextPath(''), '../dashboard/dashboard.html');

(async () => {
  const missing = await AccountSession.restore();
  assert.equal(missing.status, 'anonymous');

  store.set('kaamdo_auth_token', 'demo_token_authenticated');
  const demo = await AccountSession.restore();
  assert.equal(demo.status, 'anonymous');
  assert.equal(store.has('kaamdo_auth_token'), false);

  store.set('kaamdo_auth_token', 'saved-token');
  const offline = await AccountSession.restore();
  assert.equal(offline.status, 'offline');
  assert.equal(store.get('kaamdo_auth_token'), 'saved-token');

  global.AuthApi.getCurrentUser = async () => {
    throw Object.assign(new Error('denied'), { status: 401 });
  };
  const invalid = await AccountSession.restore();
  assert.equal(invalid.status, 'invalid');
  assert.equal(store.has('kaamdo_auth_token'), false);

  const loginJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/login.js'), 'utf8');
  const loginHtml = fs.readFileSync(path.join(__dirname, '../pages/auth/login.html'), 'utf8');
  const dashboardJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/dashboard.js'), 'utf8');
  const areaJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/area.js'), 'utf8');
  assert.match(loginJs, /AccountSession\.safeNextPath/);
  assert.match(loginHtml, /account\/session\.js/);
  assert.match(dashboardJs, /auth\/login\.html/);
  assert.match(areaJs, /auth\/login\.html/);
  const detailsJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/equipmentDetails.js'), 'utf8');
  const postJobJs = fs.readFileSync(path.join(__dirname, '../assets/js/pages/postJob.js'), 'utf8');
  assert.equal(typeof AccountSession.rememberReturnPath, 'function');
  assert.match(detailsJs, /rememberReturnPath/);
  assert.match(detailsJs, /equipment_inquiry|INQUIRY_OTP_PURPOSE/);
  assert.match(postJobJs, /rememberReturnPath/);
  assert.match(postJobJs, /hash === '#equipment'/);
  assert.match(areaJs, /rememberReturnPath/);
  console.log('session tests passed');
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
