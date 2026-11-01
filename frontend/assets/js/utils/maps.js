/**
 * Optional map note. Default is off.
 * This file never calls Nominatim and never invents listing pins.
 */

const KaamdoMap = {
  CONFIG_PATH: '/locations/map-config/',

  parse(data) {
    const row = data && typeof data === 'object' ? data : {};
    return {
      provider: row.provider === 'osm' ? 'osm' : 'none',
      enabled: row.enabled === true && row.provider === 'osm',
      autocomplete: false,
      nominatimAutocomplete: false,
      pinPolicy: 'device_gps_only',
      inventedCentroids: false,
      attribution: row.enabled === true ? String(row.attribution || '') : '',
    };
  },

  noteText(config, hasDeviceFix) {
    if (!config || !config.enabled) {
      return 'No public map is configured. Matching uses this phone location, not a district pin.';
    }
    if (!hasDeviceFix) {
      return 'Share this phone location before a map note is shown. KaamDo does not invent a pin from the district name.';
    }
    return config.attribution
      ? `Approximate area from this phone. ${config.attribution}`
      : 'Approximate area from this phone. Not a precise listing pin.';
  },

  async load() {
    if (typeof ApiClient === 'undefined') return this.parse(null);
    try {
      return this.parse(await ApiClient.get(this.CONFIG_PATH));
    } catch (error) {
      return this.parse(null);
    }
  },

  async renderNote(host, hasDeviceFix) {
    if (!host) return;
    const config = await this.load();
    host.textContent = this.noteText(config, Boolean(hasDeviceFix));
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = KaamdoMap;
}
