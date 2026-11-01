/**
 * KaamDo Storage Utility
 * Safe wrapper around browser localStorage for auth tokens and preferences.
 */

const StorageUtil = {
  get(key) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    } catch {
      return localStorage.getItem(key);
    }
  },

  set(key, value) {
    try {
      const stringValue = typeof value === 'object' ? JSON.stringify(value) : value;
      localStorage.setItem(key, stringValue);
    } catch (e) {
      console.error('StorageUtil error setting key:', key, e);
    }
  },

  remove(key) {
    localStorage.removeItem(key);
  },

  clear() {
    localStorage.clear();
  }
};
