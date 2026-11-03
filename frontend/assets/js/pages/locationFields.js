/**
 * Place fields: State → District → Taluk → Locality.
 * Locality, street and PIN are typed. Villages are not invented.
 */

const LocationFields = {
  CATALOG_PATH: '/locations/catalog/',
  cache: null,

  text(key) {
    return typeof I18n === 'undefined' ? key : I18n.t(key);
  },

  placeLabel() {
    const parts = [];
    Array.from(arguments).forEach((item) => {
      const text = String(item == null ? '' : item).replace(/\s+/g, ' ').trim();
      if (text && !parts.includes(text)) parts.push(text);
    });
    return parts.join(', ');
  },

  async loadCatalog() {
    if (this.cache) return this.cache;
    if (typeof ApiClient === 'undefined') {
      this.cache = { state: { name: 'Karnataka' }, districts: [], states: [] };
      return this.cache;
    }
    try {
      this.cache = await ApiClient.get(this.CATALOG_PATH);
    } catch (error) {
      this.cache = { state: { name: 'Karnataka' }, districts: [], states: [], failed: true };
    }
    return this.cache;
  },

  statesFrom(catalog) {
    if (catalog && Array.isArray(catalog.states) && catalog.states.length) return catalog.states;
    return [{
      name: catalog && catalog.state && catalog.state.name ? catalog.state.name : 'Karnataka',
      districts: catalog && catalog.districts ? catalog.districts : [],
    }];
  },

  stateNames(catalog) {
    return this.statesFrom(catalog).map((row) => row.name);
  },

  districtsFor(catalog, stateName) {
    const states = this.statesFrom(catalog);
    if (!stateName) {
      const names = [];
      states.forEach((state) => {
        (state.districts || []).forEach((row) => {
          if (row.name && !names.includes(row.name)) names.push(row.name);
        });
      });
      if (names.length) return names;
      return ((catalog && catalog.districts) || []).map((row) => row.name);
    }
    const match = states.find((row) => row.name === stateName);
    const rows = match ? match.districts : (catalog && catalog.districts) || [];
    return (rows || []).map((row) => row.name);
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
    const lists = [];
    this.statesFrom(catalog).forEach((state) => {
      lists.push(...(state.districts || []));
    });
    if (catalog && Array.isArray(catalog.districts)) lists.push(...catalog.districts);
    const row = lists.find((item) => item.name === district);
    return row && Array.isArray(row.taluks) ? row.taluks : [];
  },

  stateForDistrict(catalog, district) {
    const hit = this.statesFrom(catalog).find((state) => (
      (state.districts || []).some((row) => row.name === district)
    ));
    return hit ? hit.name : '';
  },

  async enhance(options) {
    const state = options.state;
    const district = options.district;
    const taluk = options.taluk;
    const onChange = options.onChange;
    const catalog = await this.loadCatalog();
    const stateNames = this.stateNames(catalog);
    let selectedState = options.selectedState || (state && state.value) || '';
    if (options.selectedDistrict && !selectedState) {
      selectedState = this.stateForDistrict(catalog, options.selectedDistrict);
    }
    if (state) this.fillSelect(state, stateNames, selectedState);
    const currentState = state ? state.value : selectedState;
    this.fillSelect(district, this.districtsFor(catalog, currentState), options.selectedDistrict);
    const taluks = this.taluksFor(catalog, district && district.value);
    this.fillSelect(taluk, taluks, options.selectedTaluk);
    if (taluk) taluk.required = taluks.length > 0;
    if (state && !state.dataset.locationBound) {
      state.dataset.locationBound = '1';
      state.addEventListener('change', () => {
        this.fillSelect(district, this.districtsFor(catalog, state.value), '');
        this.fillSelect(taluk, [], '');
        if (taluk) taluk.required = false;
        if (onChange) onChange();
      });
    }
    if (district && !district.dataset.locationBound) {
      district.dataset.locationBound = '1';
      district.addEventListener('change', () => {
        const next = this.taluksFor(catalog, district.value);
        this.fillSelect(taluk, next, '');
        if (taluk) taluk.required = next.length > 0;
        if (onChange) onChange();
      });
    }
    if (taluk && !taluk.dataset.locationBound) {
      taluk.dataset.locationBound = '1';
      taluk.addEventListener('change', () => {
        if (onChange) onChange();
      });
    }
    if (options.locality && !options.locality.dataset.locationBound) {
      options.locality.dataset.locationBound = '1';
      options.locality.addEventListener('input', () => {
        delete options.locality.dataset.autoFilled;
      });
    }
    return catalog;
  },

  async enhanceByIds(ids, onChange) {
    return this.enhance({
      state: ids.state ? document.getElementById(ids.state) : null,
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
