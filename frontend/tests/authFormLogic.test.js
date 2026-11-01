const assert = require('node:assert/strict');
const logic = require('../assets/js/pages/authFormLogic.js');

assert.equal(logic.phoneDigits('98 76-543210'), '9876543210');
assert.deepEqual(logic.phoneProblems('98765'), ['login.phoneInvalid']);
assert.deepEqual(logic.phoneProblems('1234567890'), ['login.phoneInvalid']);
assert.deepEqual(logic.phoneProblems('9876543210'), []);
assert.deepEqual(logic.loginProblems('9876543210', ''), ['login.passwordRequired']);
assert.deepEqual(logic.loginProblems('123', ''), ['login.phoneInvalid', 'login.passwordRequired']);
assert.deepEqual(logic.registerProblems('', '9876543210', 'short'), ['register.nameRequired', 'register.passwordShort']);
assert.deepEqual(logic.registerProblems('Asha Rao', '9876543210', 'SafePass!234'), []);

console.log('auth form logic tests passed');
