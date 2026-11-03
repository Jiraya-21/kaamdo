/**
 * Public equipment advertisements. Unpaid and draft listings stay off this page.
 * District, text, price basis, and operator are sent to the API before pagination.
 */

function listText(key, values) {
  let text = typeof I18n === 'undefined' ? key : I18n.t(key);
  Object.keys(values || {}).forEach((name) => {
    text = text.split(`{${name}}`).join(String(values[name]));
  });
  return text;
}

const EquipmentList = {
  equipment: [],
  loadError: '',
  requestId: 0,
  pricingBasis: '',
  operatorIncluded: '',

  async init() {
    this.bindControls();
    if (typeof LocationFields !== 'undefined') {
      await LocationFields.enhance({
        district: document.getElementById('equip-district-input'),
        selectedDistrict: '',
        onChange: () => this.load(),
      });
    }
    await this.load();
  },

  filterValues() {
    return {
      query: document.getElementById('equip-search-input')?.value || '',
      district: document.getElementById('equip-district-input')?.value || '',
      pricingBasis: this.pricingBasis,
      operatorIncluded: this.operatorIncluded,
    };
  },

  async collect(path, params, first) {
    const rows = [];
    let endpoint = path;
    let useParams = first;
    while (endpoint) {
      const page = useParams
        ? await ApiClient.get(endpoint, params)
        : await ApiClient.get(endpoint);
      useParams = false;
      if (page && Array.isArray(page.results)) rows.push(...page.results);
      if (!page || !page.next || !String(page.next).startsWith(CONFIG.API_BASE_URL)) {
        if (page && page.next) this.loadError = listText('list.partial');
        break;
      }
      endpoint = String(page.next).slice(CONFIG.API_BASE_URL.length);
    }
    return rows;
  },

  async load() {
    const requestId = ++this.requestId;
    this.loadError = '';
    const container = document.getElementById('equipment-list-container');
    if (container) container.textContent = listText('list.loadingEquipment');
    try {
      const params = EquipmentListLogic.params(this.filterValues());
      const rows = await this.collect(EquipmentListLogic.LIST_PATH, params, true);
      if (requestId !== this.requestId) return;
      this.equipment = rows;
    } catch (error) {
      if (requestId !== this.requestId) return;
      this.equipment = [];
      this.loadError = error && error.status === 400
        ? listText('list.badFilter')
        : listText('list.equipmentFailed');
    }
    this.render();
  },

  bindGroup(selector, selected, assign) {
    document.querySelectorAll(selector).forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll(selector).forEach((item) => item.classList.remove('active'));
        chip.classList.add('active');
        assign(chip.dataset[selected] || '');
        this.load();
      });
    });
  },

  bindControls() {
    const searchInput = document.getElementById('equip-search-input');
    if (searchInput) searchInput.addEventListener('change', () => this.load());
    const districtInput = document.getElementById('equip-district-input');
    if (districtInput) districtInput.addEventListener('change', () => this.load());
    this.bindGroup('.equip-price-chip', 'pricingBasis', (value) => {
      this.pricingBasis = value;
    });
    this.bindGroup('.equip-operator-chip', 'operator', (value) => {
      this.operatorIncluded = value;
    });
  },

  render() {
    const container = document.getElementById('equipment-list-container');
    const count = document.getElementById('equipment-results-count');
    if (!container) return;
    if (count) {
      count.textContent = this.loadError
        ? ''
        : listText('list.showingEquipment', { count: this.equipment.length });
    }
    container.replaceChildren();
    if (this.loadError) {
      const error = document.createElement('p');
      error.textContent = this.loadError;
      container.appendChild(error);
      return;
    }
    if (!this.equipment.length) {
      const empty = document.createElement('p');
      empty.className = 'text-muted';
      empty.textContent = listText('list.emptyEquipment');
      container.appendChild(empty);
      return;
    }
    this.equipment.forEach((item) => container.appendChild(this.card(item)));
  },

  card(item) {
    const card = document.createElement('article');
    card.className = 'card listing-card';
    const media = document.createElement('div');
    media.className = 'listing-card-media';
    const image = document.createElement('img');
    image.src = typeof KaamdoImages !== 'undefined'
      ? KaamdoImages.equipmentPhoto(item.photo_url)
      : '../../assets/images/placeholders/tractor-default.jpg';
    image.alt = item.title || '';
    image.loading = 'lazy';
    image.onerror = () => {
      image.onerror = null;
      image.src = '../../assets/images/placeholders/tractor-default.jpg';
    };
    media.appendChild(image);
    const body = document.createElement('div');
    body.className = 'listing-card-body';
    const title = document.createElement('h3');
    title.textContent = item.title;
    const place = document.createElement('p');
    place.className = 'text-muted';
    place.textContent = [item.locality, item.district].filter(Boolean).join(', ');
    const rate = document.createElement('p');
    const basisKey = `list.${item.pricing_basis}`;
    const basisText = listText(basisKey);
    rate.textContent = listText('list.rate', {
      amount: item.rate,
      basis: basisText === basisKey ? item.pricing_basis : basisText,
    });
    const operator = document.createElement('p');
    operator.textContent = item.operator_included ? listText('list.operatorYes') : listText('list.operatorNo');
    const copy = document.createElement('p');
    copy.textContent = item.description;
    const link = document.createElement('a');
    link.className = 'btn btn-primary btn-sm';
    link.href = `equipment-details.html?id=${item.id}`;
    link.textContent = listText('list.viewListing');
    body.append(title, place, rate, operator, copy, link);
    card.append(media, body);
    return card;
  },
};

document.addEventListener('DOMContentLoaded', () => EquipmentList.init());
document.addEventListener('kaamdo:language', () => {
  if (EquipmentList.equipment) EquipmentList.render();
});
