/**
 * Provider photo and availability helpers. These functions do not call the network.
 */

const ProviderStatusLogic = {
  PROFILE_PATH: '/workers/profile/',
  PHOTO_PATH: '/workers/profile/photo/',
  DEFAULT_AVATAR: '../../assets/images/placeholders/avatar-default.svg',
  MAX_BYTES: 2 * 1024 * 1024,
  ACCEPT_TYPES: ['image/jpeg', 'image/png', 'image/webp'],
  TAB_IDS: ['profile', 'requests', 'offers'],

  isProvider(user) {
    return Boolean(user && Array.isArray(user.capabilities) && user.capabilities.includes('service_provider'));
  },

  initials(name) {
    const parts = String(name || '').trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return '';
    const first = parts[0].charAt(0);
    const last = parts.length > 1 ? parts[parts.length - 1].charAt(0) : '';
    return `${first}${last}`.toUpperCase();
  },

  photoSrc(photoUrl, fallback) {
    const value = String(photoUrl == null ? '' : photoUrl).trim();
    if (/^https?:\/\//i.test(value)) return value;
    return fallback || this.DEFAULT_AVATAR;
  },

  hasUploadedPhoto(photoUrl) {
    return /^https?:\/\//i.test(String(photoUrl == null ? '' : photoUrl).trim());
  },

  fileError(file) {
    if (!file) return 'Choose a JPEG, PNG, or WebP photo.';
    if (file.size > this.MAX_BYTES) return 'Choose a photo of 2 MB or smaller.';
    const type = String(file.type || '').toLowerCase();
    const name = String(file.name || '').toLowerCase();
    const okType = this.ACCEPT_TYPES.indexOf(type) !== -1;
    const okName = /\.(jpe?g|png|webp)$/.test(name);
    if (!okType && !okName) return 'Use a JPEG, PNG, or WebP photo.';
    return '';
  },

  availabilityValue(data) {
    if (!data) return '';
    if (data.availability === 'unavailable') return 'unavailable';
    if (data.availability === 'available') return 'available';
    return '';
  },

  nextAvailability(current) {
    return current === 'available' ? 'unavailable' : 'available';
  },

  nextTab(current, key) {
    const ids = this.TAB_IDS;
    const index = ids.indexOf(current);
    const start = index === -1 ? 0 : index;
    if (key === 'ArrowRight' || key === 'ArrowDown') return ids[(start + 1) % ids.length];
    if (key === 'ArrowLeft' || key === 'ArrowUp') return ids[(start - 1 + ids.length) % ids.length];
    if (key === 'Home') return ids[0];
    if (key === 'End') return ids[ids.length - 1];
    return current;
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = ProviderStatusLogic;
}
