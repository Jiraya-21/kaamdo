/**
 * Shared GPS + reverse-geocode helper for Daily Services, jobs, equipment, and farm hiring.
 * Permission is requested only after a click. Results fill the existing form fields.
 * There is no second confirmation panel and no duplicate address fields.
 */

const LocationDetect = {
  REVERSE_PATH: '/locations/reverse/',
  STORAGE_KEY: 'kaamdo_confirmed_place',
  detectToken: 0,

  text(key) {
    return typeof I18n === 'undefined' ? key : I18n.t(key);
  },

  gpsErrorKey(error) {
    const code = error && error.code;
    if (code === 1) return 'location.permissionDenied';
    if (code === 2) return 'location.unavailable';
    if (code === 3) return 'location.timeout';
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      return 'location.unsupported';
    }
    return 'guest.locationFailed';
  },

  hasTypedPlace(fields) {
    const state = fields && fields.state ? String(fields.state.value || '').trim() : '';
    const district = fields && fields.district ? String(fields.district.value || '').trim() : '';
    const taluk = fields && fields.taluk ? String(fields.taluk.value || '').trim() : '';
    const locality = fields && fields.locality ? String(fields.locality.value || '').trim() : '';
    const street = fields && fields.street ? String(fields.street.value || '').trim() : '';
    const auto = fields && fields.locality && fields.locality.dataset.autoFilled === '1';
    return Boolean(state || district || taluk || street || (locality && !auto));
  },

  cleanPart(value) {
    return String(value == null ? '' : value).replace(/\s+/g, ' ').trim().toLowerCase();
  },

  displayName(suggestion) {
    if (!suggestion) return '';
    const label = String(suggestion.display || '').replace(/\s+/g, ' ').trim();
    if (label) return label;
    const parts = [];
    [suggestion.street, suggestion.locality, suggestion.village, suggestion.taluk, suggestion.district, suggestion.postcode].forEach((item) => {
      const text = String(item || '').replace(/\s+/g, ' ').trim();
      if (text && !parts.includes(text)) parts.push(text);
    });
    return parts.join(', ');
  },

  fieldSnapshot(fields) {
    const row = fields || {};
    return [
      this.cleanPart(row.state && row.state.value),
      this.cleanPart(row.district && row.district.value),
      this.cleanPart(row.taluk && row.taluk.value),
      this.cleanPart(row.locality && row.locality.value),
      this.cleanPart(row.street && row.street.value),
      this.cleanPart(row.pin && row.pin.value),
    ].join('|');
  },

  remember(suggestion, coords) {
    if (typeof sessionStorage === 'undefined') return;
    const label = this.displayName(suggestion);
    sessionStorage.setItem(this.STORAGE_KEY, JSON.stringify({
      state: suggestion && suggestion.state || '',
      district: suggestion && suggestion.district || '',
      taluk: suggestion && suggestion.taluk || '',
      locality: suggestion && suggestion.locality || '',
      street: suggestion && suggestion.street || '',
      postcode: suggestion && suggestion.postcode || '',
      display: label,
      latitude: coords && coords.latitude != null ? String(coords.latitude) : '',
      longitude: coords && coords.longitude != null ? String(coords.longitude) : '',
    }));
  },

  loadRemembered() {
    if (typeof sessionStorage === 'undefined') return null;
    try {
      const raw = sessionStorage.getItem(this.STORAGE_KEY);
      if (!raw) return null;
      const row = JSON.parse(raw);
      if (!row || typeof row !== 'object') return null;
      return row;
    } catch (error) {
      return null;
    }
  },

  setCoordinates(fields, coords) {
    if (!fields || !coords) return;
    const lat = typeof GeolocationUtil === 'undefined'
      ? String(coords.latitude)
      : GeolocationUtil.coordinateText(coords.latitude);
    const lon = typeof GeolocationUtil === 'undefined'
      ? String(coords.longitude)
      : GeolocationUtil.coordinateText(coords.longitude);
    if (fields.latitude) fields.latitude.value = lat;
    if (fields.longitude) fields.longitude.value = lon;
  },

  async reverse(coords) {
    if (typeof ApiClient === 'undefined' || !coords) {
      return { available: false, reason: 'disabled', district: '', taluk: '', locality: '', display: '' };
    }
    try {
      return await ApiClient.post(this.REVERSE_PATH, {
        latitude: coords.latitude,
        longitude: coords.longitude,
      });
    } catch (error) {
      const data = error && error.data && typeof error.data === 'object' ? error.data : null;
      if (data && Object.prototype.hasOwnProperty.call(data, 'available')) return data;
      return { available: false, reason: 'provider_unavailable', district: '', taluk: '', locality: '', display: '' };
    }
  },

  fillIfEmpty(node, value, force) {
    if (!node || value == null || value === '') return;
    const typed = String(node.value || '').trim();
    const auto = node.dataset && node.dataset.autoFilled === '1';
    if (!typed || force || auto) {
      node.value = value;
      if (node.tagName !== 'SELECT') {
        if (!node.dataset) node.dataset = {};
        node.dataset.autoFilled = '1';
      }
    }
  },

  async applySuggestion(fields, suggestion, force) {
    if (!fields || !suggestion) return;
    const overwrite = force === true;
    const canReplaceCatalog = overwrite || !this.hasTypedPlace(fields);
    if (canReplaceCatalog && typeof LocationFields !== 'undefined' && fields.district && fields.taluk) {
      await LocationFields.enhance({
        state: fields.state,
        district: fields.district,
        taluk: fields.taluk,
        locality: fields.locality,
        selectedState: suggestion.state || '',
        selectedDistrict: suggestion.district || '',
        selectedTaluk: suggestion.taluk || '',
      });
    } else if (canReplaceCatalog) {
      this.fillIfEmpty(fields.state, suggestion.state, overwrite);
      this.fillIfEmpty(fields.district, suggestion.district, overwrite);
      this.fillIfEmpty(fields.taluk, suggestion.taluk, overwrite);
    }
    this.fillIfEmpty(fields.locality, suggestion.locality || suggestion.village, overwrite);
    this.fillIfEmpty(fields.street, suggestion.street, overwrite);
    this.fillIfEmpty(fields.pin, suggestion.postcode, overwrite);
  },

  showStatus(status, keyOrText, kind, asKey) {
    if (!status) return;
    status.textContent = asKey === false ? (keyOrText || '') : this.text(keyOrText);
    status.classList.remove('is-error', 'is-success', 'is-info');
    if (kind) status.classList.add(`is-${kind}`);
  },

  async detect(options) {
    const fields = options.fields || {};
    const status = options.status;
    const token = (this.detectToken += 1);
    const before = this.fieldSnapshot(fields);

    if (typeof GeolocationUtil === 'undefined') {
      this.showStatus(status, 'location.unsupported', 'error');
      return null;
    }
    this.showStatus(status, 'guest.locating', 'info');

    let coords;
    try {
      coords = await GeolocationUtil.getCurrentCoordinates();
    } catch (error) {
      if (token !== this.detectToken) return null;
      this.showStatus(status, this.gpsErrorKey(error), 'error');
      return null;
    }
    if (token !== this.detectToken) return null;

    this.setCoordinates(fields, coords);
    if (typeof KaamdoMap !== 'undefined' && options.mapHost) {
      KaamdoMap.renderNote(options.mapHost, true);
    }

    const suggestion = await this.reverse(coords);
    if (token !== this.detectToken) return null;

    const editedDuringWait = this.fieldSnapshot(fields) !== before;
    if (!suggestion || suggestion.available !== true || !this.displayName(suggestion)) {
      this.showStatus(status, 'location.geocodeFailed', 'info');
      return { coords, suggestion: suggestion || { available: false } };
    }

    if (editedDuringWait) {
      this.showStatus(
        status,
        this.displayName(suggestion) || this.text('guest.located'),
        'success',
        false,
      );
      return { coords, suggestion, keptEdits: true };
    }

    const hadManual = this.hasTypedPlace(fields);
    await this.applySuggestion(fields, suggestion, false);
    if (!hadManual) this.remember(suggestion, coords);

    this.showStatus(
      status,
      this.displayName(suggestion) || this.text('guest.located'),
      'success',
      false,
    );
    return { coords, suggestion, keptEdits: false };
  },

  bind(options) {
    const button = options.button;
    if (!button || button.dataset.locationDetectBound === '1') return;
    button.dataset.locationDetectBound = '1';
    button.addEventListener('click', () => this.detect(options));
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = LocationDetect;
}
