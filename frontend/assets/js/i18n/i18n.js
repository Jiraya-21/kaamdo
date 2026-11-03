/**
 * Language selection for the KaamDo pages.
 * The saved value is only a language code. It is not an account secret.
 */

const I18n = {
  STORAGE_KEY: 'kaamdo_lang',
  SUPPORTED: ['en', 'kn', 'hi', 'mr'],
  DEFAULT: 'en',

  normalize(code) {
    const value = String(code == null ? '' : code).trim().toLowerCase();
    return this.SUPPORTED.includes(value) ? value : this.DEFAULT;
  },

  read(storage) {
    try {
      return this.normalize(storage && storage.getItem(this.STORAGE_KEY));
    } catch (error) {
      return this.DEFAULT;
    }
  },

  write(storage, code) {
    const next = this.normalize(code);
    storage.setItem(this.STORAGE_KEY, next);
    return next;
  },

  currentLanguage(storage) {
    if (this.current) return this.current;
    const source = storage || (typeof localStorage !== 'undefined' ? localStorage : null);
    this.current = this.read(source);
    return this.current;
  },

  text(lang, key) {
    const selected = this.normalize(lang);
    const packs = typeof KaamdoMessages === 'undefined' ? {} : KaamdoMessages;
    const chosen = packs[selected] || {};
    const english = packs.en || {};
    if (Object.prototype.hasOwnProperty.call(chosen, key) && chosen[key]) return chosen[key];
    if (Object.prototype.hasOwnProperty.call(english, key) && english[key]) return english[key];
    return key;
  },

  t(key) {
    return this.text(this.currentLanguage(), key);
  },

  fill(key, values) {
    let text = this.t(key);
    Object.keys(values || {}).forEach((name) => {
      text = text.split(`{${name}}`).join(String(values[name] == null ? '' : values[name]));
    });
    return text;
  },

  categoryLabel(slug, fallback) {
    const key = `category.${String(slug || '').trim().toLowerCase()}`;
    const translated = this.t(key);
    return translated === key ? String(fallback || '') : translated;
  },

  statusText(status, workerName) {
    const name = workerName ? String(workerName) : '';
    return this.t(`status.${status}`).split('{name}').join(name);
  },

  apply(root) {
    const scope = root || (typeof document !== 'undefined' ? document : null);
    if (!scope || !scope.querySelectorAll) return;
    if (typeof document !== 'undefined') document.documentElement.lang = this.currentLanguage();
    scope.querySelectorAll('[data-i18n]').forEach((element) => {
      element.textContent = this.t(element.getAttribute('data-i18n'));
    });
    scope.querySelectorAll('[data-i18n-placeholder]').forEach((element) => {
      element.setAttribute('placeholder', this.t(element.getAttribute('data-i18n-placeholder')));
    });
    scope.querySelectorAll('[data-i18n-aria]').forEach((element) => {
      element.setAttribute('aria-label', this.t(element.getAttribute('data-i18n-aria')));
    });
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = I18n;
}
