/**
 * Query string for the public worker directory.
 * Filters are sent to the API so they apply before pagination.
 */

const WorkerDirectoryLogic = {
  LIST_PATH: '/workers/',
  CATEGORY_PATH: '/workers/categories/',
  DEFAULT_AVATAR: '../../assets/images/placeholders/avatar-default.svg',

  photoSrc(photoUrl) {
    const value = String(photoUrl == null ? '' : photoUrl).trim();
    if (/^https?:\/\//i.test(value)) return value;
    return this.DEFAULT_AVATAR;
  },

  clean(value) {
    return String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
  },

  coordinateText(value) {
    const text = this.clean(value);
    if (!text) return '';
    const number = Number(text);
    if (!Number.isFinite(number)) return text;
    return number.toFixed(6);
  },

  searchFromLocation(search) {
    const params = new URLSearchParams(search || '');
    const query = this.clean(params.get('q'));
    let district = this.clean(params.get('district'));
    const legacy = this.clean(params.get('loc'));
    if (!district && legacy && legacy.toLowerCase() !== 'all') district = legacy;
    if (district.toLowerCase() === 'all') district = '';
    return { query, district };
  },

  params(values) {
    const params = {};
    const query = this.clean(values.query);
    const district = this.clean(values.district);
    const category = this.clean(values.category);
    const skill = this.clean(values.skill);
    if (query && query.toLowerCase() !== 'all') params.q = query;
    if (district && district.toLowerCase() !== 'all') params.district = district;
    if (category && category.toLowerCase() !== 'all') params.category = category;
    if (skill) params.skill = skill;
    const latitude = this.coordinateText(values.latitude);
    const longitude = this.coordinateText(values.longitude);
    const radius = this.clean(values.radiusKm);
    if (latitude && longitude && radius) {
      params.latitude = latitude;
      params.longitude = longitude;
      params.radius_km = radius;
    }
    return params;
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = WorkerDirectoryLogic;
}
