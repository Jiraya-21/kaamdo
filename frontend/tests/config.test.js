const assert = require('node:assert/strict');
const { resolveKaamdoApiBase } = require('../assets/js/config.js');

assert.equal(resolveKaamdoApiBase({}), 'http://127.0.0.1:8000/api/v1');
assert.equal(
  resolveKaamdoApiBase({ hostname: 'localhost', origin: 'http://localhost:5500' }),
  'http://127.0.0.1:8000/api/v1',
);
assert.equal(
  resolveKaamdoApiBase({ hostname: '127.0.0.1', origin: 'http://127.0.0.1:5500' }),
  'http://127.0.0.1:8000/api/v1',
);
assert.equal(
  resolveKaamdoApiBase({ hostname: 'app.example.test', origin: 'https://app.example.test' }),
  'https://app.example.test/api/v1',
);
assert.equal(
  resolveKaamdoApiBase({
    override: 'https://api.example.test/api/v1/',
    hostname: 'app.example.test',
    origin: 'https://app.example.test',
  }),
  'https://api.example.test/api/v1',
);

console.log('api base config tests passed');
