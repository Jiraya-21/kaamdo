/**
 * Karnataka place fields: State → District → Taluk → Locality.
 * Locality is typed by the user. Villages are not invented.
 */

const LocationFields = {
  CATALOG_PATH: '/locations/catalog/',
  cache: null,

  text(key) {
    return typeof I18n === 'undefined' ? key : I18n.t(key);
  },

  placeLabel(locality, taluk, district) {
    const parts = [];
    [locality, taluk, district].forEach((item) => {
      const text = String(item == null ? '' : item).replace(/\s+/g, ' ').trim();
      if (text && !parts.includes(text)) parts.push(text);
    });
    return parts.join(', ');
  },

  async loadCatalog() {
    if (this.cache) return this.cache;
    if (typeof ApiClient === 'undefined') {
      this.cache = { state: { name: 'Karnataka' }, districts: [] };
      return this.cache;
    }
    try {
      this.cache = await ApiClient.get(this.CATALOG_PATH);
    } catch (error) {
      this.cache = { state: { name: 'Karnataka' }, districts: [], failed: true };
    }
    return this.cache;
  },

  fillSelect(select, names, selected) {
    if (!select) return;
    const current = selected || select.value || '';
    select.replaceChildren();
    const blank = document.createElement('option');
    blank.value = '';
    blank.textContent = this.text('form.choose');
    select.appendChild(blank);
    names.forEach((name) => {
      const option = document.createElement('option');
      option.value = name;
      option.textContent = name;
      if (name === current) option.selected = true;
      select.appendChild(option);
    });
  },

  taluksFor(catalog, district) {
    const row = (catalog.districts || []).find((item) => item.name === district);
    return row && Array.isArray(row.taluks) ? row.taluks : [];
  },

  async enhance(options) {
    const district = options.district;
    const taluk = options.taluk;
    const onChange = options.onChange;
    const catalog = await this.loadCatalog();
    const names = (catalog.districts || []).map((row) => row.name);
    this.fillSelect(district, names, options.selectedDistrict);
    this.fillSelect(taluk, this.taluksFor(catalog, district && district.value), options.selectedTaluk);
    if (district && !district.dataset.locationBound) {
      district.dataset.locationBound = '1';
      district.addEventListener('change', () => {
        this.fillSelect(taluk, this.taluksFor(catalog, district.value), '');
        if (onChange) onChange();
      });
    }
    if (taluk && !taluk.dataset.locationBound) {
      taluk.dataset.locationBound = '1';
      taluk.addEventListener('change', () => {
        if (onChange) onChange();
      });
    }
    return catalog;
  },

  async enhanceByIds(ids, onChange) {
    return this.enhance({
      district: document.getElementById(ids.district),
      taluk: document.getElementById(ids.taluk),
      locality: document.getElementById(ids.locality),
      onChange,
    });
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = LocationFields;
}
