/**
 * Shared real-photo paths for categories, marketplace tiles, and listing cards.
 */

const KaamdoImages = {
  ROOT: '../../assets/images',
  EXT: 'jpg',

  CATEGORY_SLUGS: {
    plumber: 'plumber',
    electrician: 'electrician',
    'house-clean': 'house-clean',
    painter: 'painter',
    'ac-repair': 'ac-repair',
    'washroom-cleaning': 'washroom-cleaning',
    'agriculture-equipment-renting': 'agriculture-equipment-renting',
  },

  MARKETPLACE: {
    daily: 'daily',
    jobs: 'jobs',
    equipment: 'equipment',
    farm: 'farm',
  },

  rootPrefix() {
    if (typeof window === 'undefined' || !window.location) return this.ROOT;
    const path = String(window.location.pathname || '');
    const isRoot = path.endsWith('index.html') || path.endsWith('/') || !path.includes('/pages/');
    return isRoot ? 'assets/images' : this.ROOT;
  },

  asset(folder, name, fallback) {
    const file = name || fallback;
    return `${this.rootPrefix()}/${folder}/${file}.${this.EXT}`;
  },

  category(slug) {
    const key = String(slug || '').trim().toLowerCase();
    return this.asset('services', this.CATEGORY_SLUGS[key], 'service');
  },

  marketplace(id) {
    const key = String(id || '').trim().toLowerCase();
    return this.asset('marketplace', this.MARKETPLACE[key], 'daily');
  },

  listing(kind) {
    if (kind === 'agricultural' || kind === 'farm') {
      return this.asset('listings', 'farm', 'farm');
    }
    if (kind === 'equipment') {
      return this.asset('listings', 'equipment', 'equipment');
    }
    return this.asset('listings', 'job', 'job');
  },

  photoOr(photoUrl, fallback) {
    const value = String(photoUrl == null ? '' : photoUrl).trim();
    if (/^https?:\/\//i.test(value)) return value;
    if (/^(\.?\.?\/|data:|blob:)/i.test(value) && value.length > 2) return value;
    return fallback;
  },

  equipmentPhoto(photoUrl) {
    return this.photoOr(photoUrl, `${this.rootPrefix()}/placeholders/tractor-default.${this.EXT}`);
  },

  avatar(photoUrl) {
    return this.photoOr(photoUrl, `${this.rootPrefix()}/placeholders/avatar-default.${this.EXT}`);
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = KaamdoImages;
}
