/**
 * KaamDo Frontend Configuration
 * Centralized settings for API endpoints, default parameters, and storage keys.
 */

function resolveKaamdoApiBase(input) {
  const source = input || {};
  const override = typeof source.override === 'string' ? source.override.trim() : '';
  if (override) {
    return override.replace(/\/+$/, '');
  }
  const hostname = source.hostname || '';
  const origin = source.origin || '';
  if (!hostname || hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]') {
    return 'http://127.0.0.1:8000/api/v1';
  }
  // On a public host, do not call the visitor's localhost. Same-origin /api/v1
  // is used unless window.KAAMDO_API_BASE is set before this file loads.
  if (origin) {
    return String(origin).replace(/\/+$/, '') + '/api/v1';
  }
  return 'http://127.0.0.1:8000/api/v1';
}

const CONFIG = {
  API_BASE_URL: resolveKaamdoApiBase({
    override: typeof window !== 'undefined' ? window.KAAMDO_API_BASE : '',
    hostname: typeof window !== 'undefined' && window.location ? window.location.hostname : '',
    origin: typeof window !== 'undefined' && window.location ? window.location.origin : '',
  }),

  DEFAULT_SEARCH_RADIUS_KM: 20,

  // Soft first-phase focus for demos. Does not block other districts.
  FIRST_AREA_DISTRICT: 'Bidar',

  STORAGE_KEYS: {
    AUTH_TOKEN: 'kaamdo_auth_token',
    USER_DATA: 'kaamdo_user_data',
    USER_ROLE: 'kaamdo_user_role'
  }
};

Object.freeze(CONFIG);

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { CONFIG, resolveKaamdoApiBase };
}
