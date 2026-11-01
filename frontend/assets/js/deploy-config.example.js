/**
 * Copy this file to deploy-config.js on the static host only.
 * Set the public API origin. Do not point production at localhost.
 * Load this file before config.js.
 */
window.KAAMDO_API_BASE = 'https://YOUR-API-HOST.onrender.com/api/v1';
window.KAAMDO_MAP_PROVIDER = 'none';
window.KAAMDO_MAP_ATTRIBUTION = 'Map data © OpenStreetMap contributors';
