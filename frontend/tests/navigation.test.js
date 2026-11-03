const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const navbar = fs.readFileSync(
  path.join(__dirname, '../assets/js/components/navbar.js'),
  'utf8',
);
const home = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');

assert.match(navbar, /pages\/services\/guest-request\.html/);
assert.match(navbar, /pages\/jobs\/jobs-list\.html/);
assert.match(navbar, /pages\/equipment\/equipment-list\.html/);
assert.match(navbar, /pages\/jobs\/farm-jobs\.html/);
assert.equal(navbar.includes('directory.html'), false);
assert.equal(navbar.includes('nav.services'), false);
assert.equal(navbar.includes('nav.workers'), false);
assert.equal((navbar.match(/dashboard\.html/g) || []).length, 1);
assert.match(navbar, /class="skip-link"/);
assert.match(navbar, /href="#app-content"/);
assert.match(home, /pages\/services\/guest-request\.html/);
const guestPage = fs.readFileSync(
  path.join(__dirname, '../pages/services/guest-request.html'),
  'utf8',
);
assert.match(guestPage, /track-request.html/);
assert.equal(fs.existsSync(path.join(__dirname, '../pages/services/track-request.html')), true);
assert.match(home, /pages\/jobs\/jobs-list\.html/);
assert.match(home, /pages\/equipment\/equipment-list\.html/);
assert.match(home, /pages\/jobs\/farm-jobs\.html/);
assert.equal(home.includes('directory.html'), false);
assert.match(home, /assets\/images\/placeholders\/hero-bg\.jpg/);
assert.match(home, /assets\/images\/marketplace\/daily\.jpg/);
assert.match(home, /assets\/images\/logo\.png/);
assert.match(home, /home-track-bar/);
assert.match(home, /track-request\.html\?guest=1/);
assert.equal(home.includes('images.unsplash.com'), false);
assert.match(navbar, /assets\/images\/logo\.png/);

console.log('navigation tests passed');
