const assert = require('node:assert/strict');

global.KaamdoMessages = require('../assets/js/i18n/messages.js');
const I18n = require('../assets/js/i18n/i18n.js');

const memory = {
  value: '',
  getItem() { return this.value; },
  setItem(key, next) { this.value = next; },
};

assert.equal(I18n.normalize(''), 'en');
assert.equal(I18n.normalize('KN'), 'kn');
assert.equal(I18n.normalize('fr'), 'en');
assert.equal(I18n.read(memory), 'en');
assert.equal(I18n.write(memory, 'hi'), 'hi');
assert.equal(memory.value, 'hi');
assert.equal(I18n.read(memory), 'hi');
assert.equal(I18n.write(memory, 'nope'), 'en');

I18n.current = 'kn';
assert.equal(I18n.t('nav.services'), 'ಸೇವೆಗಳು');
assert.equal(I18n.t('missing.key'), 'missing.key');
I18n.current = 'hi';
const savedHome = KaamdoMessages.hi['nav.home'];
delete KaamdoMessages.hi['nav.home'];
assert.equal(I18n.text('hi', 'nav.home'), KaamdoMessages.en['nav.home']);
KaamdoMessages.hi['nav.home'] = savedHome;
assert.equal(I18n.text('hi', 'not.translated.yet'), 'not.translated.yet');
assert.match(I18n.t('guest.title'), /[\u0900-\u097F]/);
I18n.current = 'kn';
assert.match(I18n.t('guest.title'), /[\u0C80-\u0CFF]/);
assert.equal(I18n.statusText('assigned', 'Asha').includes('Asha'), true);
assert.equal(I18n.statusText('offering', '').includes('{name}'), false);
assert.equal(I18n.categoryLabel('unknown-slug', 'Server name'), 'Server name');
assert.equal(I18n.categoryLabel('electrician', 'Electrician') === 'Electrician', false);
assert.equal(I18n.fill('guest.devCode', { code: '123456' }).includes('123456'), true);
assert.equal(I18n.t('guest.stepCatalogue').includes('1.'), true);
assert.equal(I18n.t('form.jobHeading').length > 0, true);
assert.equal(I18n.t('daily.place').length > 0, true);
assert.equal(I18n.t('booking.send').length > 0, true);
assert.equal(I18n.t('title.guest').includes('KaamDo') || I18n.t('title.guest').includes('ಕಾಮ್') || I18n.t('title.guest').length > 0, true);
assert.equal(I18n.t('guest.noCode').length > 0, true);
assert.equal(I18n.t('register.districtNote').length > 0, true);

const languages = ['en', 'kn', 'hi'];
const keys = Object.keys(KaamdoMessages.en);
languages.forEach((lang) => {
  keys.forEach((key) => {
    assert.equal(typeof KaamdoMessages[lang][key], 'string');
    assert.equal(KaamdoMessages[lang][key].length > 0, true);
  });
});

console.log('language tests passed');
