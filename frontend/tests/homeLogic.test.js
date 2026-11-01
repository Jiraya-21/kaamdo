const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/homeLogic.js');

assert.equal(logic.CATEGORY_PATH, '/workers/categories/');
assert.equal(logic.searchTarget(''), logic.SERVICE_PAGE);
assert.equal(logic.searchTarget(' Electrician '), `${logic.SERVICE_PAGE}?q=Electrician`);
assert.equal(logic.searchTarget('').includes('directory'), false);
const cards = logic.categoryCards([
  { id: 1, name: 'Electrician', slug: 'electrician', description: 'Wiring' },
  { name: 'Missing slug' },
]);
assert.equal(cards.length, 1);
assert.equal(cards[0].href, `${logic.SERVICE_PAGE}?category=electrician`);
assert.equal(cards[0].href.includes('profile'), false);
assert.equal(logic.nextPath({ next: 'http://127.0.0.1:8000/api/v1/workers/categories/?page=2' }, 'http://127.0.0.1:8000/api/v1'), '/workers/categories/?page=2');
assert.equal(logic.nextPath({ next: 'https://example.test/next' }, 'http://127.0.0.1:8000/api/v1'), '');

console.log('home logic tests passed');
