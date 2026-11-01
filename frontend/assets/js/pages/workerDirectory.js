/**
 * KaamDo Worker Directory Controller
 * Renders Square Worker ID cards, 20km radius filtering, search, and booking triggers.
 */

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const WorkerDirectory = {
  workers: [],
  loadError: '',
  requestId: 0,
  origin: null,
  currentRadiusKm: 20,
  selectedCategory: 'All',
  searchQuery: '',

  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  label(slug, name) {
    return typeof I18n === 'undefined' ? name : I18n.categoryLabel(slug, name);
  },

  async init() {
    this.workers = [];
    this.loadError = '';
    const preset = WorkerDirectoryLogic.searchFromLocation(window.location.search);
    this.searchQuery = preset.query;
    const searchInput = document.getElementById('worker-search-input');
    const districtInput = document.getElementById('worker-district-input');
    if (searchInput) searchInput.value = preset.query;
    if (typeof LocationFields !== 'undefined') {
      await LocationFields.enhance({
        district: districtInput,
        selectedDistrict: preset.district,
        onChange: () => this.load(),
      });
    }
    if (districtInput && preset.district) districtInput.value = preset.district;
    this.bindControls();
    await this.loadCategories();
    await this.load();
  },

  filterValues() {
    return {
      query: this.searchQuery,
      district: document.getElementById('worker-district-input')?.value || '',
      category: this.selectedCategory,
      skill: '',
      latitude: this.origin ? String(this.origin.latitude) : '',
      longitude: this.origin ? String(this.origin.longitude) : '',
      radiusKm: this.origin ? String(this.currentRadiusKm) : '',
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
        if (page && page.next) this.loadError = this.text('directory.partial');
        break;
      }
      endpoint = String(page.next).slice(CONFIG.API_BASE_URL.length);
    }
    return rows;
  },

  mapRow(row) {
    const worker = {
      id: row.id,
      name: row.display_name || this.text('directory.workerFallback'),
      primarySkill: (row.skills && row.skills[0]) || this.text('directory.serviceFallback'),
      allSkills: row.skills || [],
      location: typeof LocationFields === 'undefined'
        ? [row.locality, row.district].filter(Boolean).join(', ')
        : LocationFields.placeLabel(row.locality, row.taluk, row.district),
      latitude: null,
      longitude: null,
      distanceKm: null,
      photo: WorkerDirectoryLogic.photoSrc(row.photo_url),
        availabilityLabel: row.availability === 'available'
          ? this.text('directory.available')
          : row.availability === 'unavailable'
            ? this.text('directory.unavailable')
            : this.text('directory.availabilityUnknown'),
      rateLabel: row.service_rate ? `${row.service_rate} ${row.pricing_basis || ''}`.trim() : this.text('directory.rateMissing'),
    };
    if (this.origin && typeof DistanceKm !== 'undefined') {
      worker.distanceKm = DistanceKm.between(
        this.origin.latitude,
        this.origin.longitude,
        worker.latitude,
        worker.longitude,
      );
    }
    return worker;
  },

  async load() {
    const requestId = ++this.requestId;
    this.loadError = '';
    const grid = document.getElementById('worker-grid-container');
    if (grid) grid.textContent = this.text('directory.loading');
    try {
      const params = WorkerDirectoryLogic.params(this.filterValues());
      const rows = await this.collect(WorkerDirectoryLogic.LIST_PATH, params, true);
      if (requestId !== this.requestId) return;
      this.workers = rows.map((row) => this.mapRow(row));
    } catch (error) {
      if (requestId !== this.requestId) return;
      this.workers = [];
      this.loadError = error && error.status === 400
        ? this.text('directory.badLocation')
        : this.text('directory.failed');
    }
    this.render();
  },

  async loadCategories() {
    const container = document.querySelector('.filter-chips-container');
    if (!container) return;
    try {
      const rows = await this.collect(WorkerDirectoryLogic.CATEGORY_PATH, {}, true);
      rows.forEach((category) => {
        if (!category || !category.slug) return;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'filter-chip category-chip';
        button.dataset.category = category.slug;
        button.textContent = this.label(category.slug, category.name || category.slug);
        container.appendChild(button);
      });
    } catch (error) {
      this.loadError = this.text('directory.categoriesFailed');
    }
    this.bindCategoryChips();
  },

  bindControls() {
    // Radius Slider
    const radiusSlider = document.getElementById('radius-slider');
    const radiusBadge = document.getElementById('radius-badge');
    if (radiusSlider && radiusBadge) {
      radiusSlider.addEventListener('change', (e) => {
        this.currentRadiusKm = Number(e.target.value);
        radiusBadge.textContent = `${this.currentRadiusKm} km`;
        if (this.origin) this.load();
      });
    }

    const searchInput = document.getElementById('worker-search-input');
    if (searchInput) {
      searchInput.addEventListener('change', (e) => {
        this.searchQuery = e.target.value;
        this.load();
      });
    }

    const districtInput = document.getElementById('worker-district-input');
    if (districtInput) {
      districtInput.addEventListener('change', () => this.load());
    }

    // Geolocation Button
    const geoBtn = document.getElementById('use-geolocation-btn');
    if (geoBtn) {
      geoBtn.addEventListener('click', async () => {
        geoBtn.textContent = this.text('directory.locating');
        try {
          const coords = await GeolocationUtil.getCurrentCoordinates();
          geoBtn.textContent = this.text('directory.located');
          this.origin = coords;
          this.load();
        } catch (err) {
          geoBtn.textContent = this.text('directory.locationFailed');
          console.warn('Geolocation permission not granted or unavailable:', err);
        }
      });
    }
  },

  bindCategoryChips() {
    const chips = document.querySelectorAll('.category-chip');
    chips.forEach((chip) => {
      if (chip.dataset.bound === 'yes') return;
      chip.dataset.bound = 'yes';
      chip.addEventListener('click', () => {
        chips.forEach((item) => item.classList.remove('active'));
        chip.classList.add('active');
        this.selectedCategory = chip.dataset.category || 'All';
        this.load();
      });
    });
  },

  render() {
    const grid = document.getElementById('worker-grid-container');
    const countEl = document.getElementById('results-count');
    if (!grid) return;

    const filtered = this.workers;

    if (countEl) countEl.textContent = this.text('directory.showing', { count: filtered.length });

    if (filtered.length === 0) {
      const message = this.loadError
        ? this.loadError
        : this.text('directory.empty');
      grid.innerHTML = `
        <div class="state-container" style="grid-column: 1 / -1;">
          <div class="state-icon">🔍</div>
          <h3>${escapeHtml(message)}</h3>
        </div>
      `;
      return;
    }

    grid.innerHTML = filtered.map(w => `
      <div class="worker-id-card" data-worker-id="${w.id}">
        <!-- 1:1 Aspect Ratio Photo with Status Indicators -->
        <div class="worker-card-photo-wrapper">
          <img 
            src="${w.photo}" 
            alt="${escapeHtml(w.name)} - ${escapeHtml(w.primarySkill)}" 
            class="worker-card-photo"
            loading="lazy"
            onerror="this.onerror=null; this.src='../../assets/images/placeholders/avatar-default.svg';"
          >
          
        </div>

        <div class="worker-card-body">
          <div class="worker-name-row">
            <h3 class="worker-name">${escapeHtml(w.name)}</h3>
          </div>
          
          <div class="worker-primary-skill">${escapeHtml(w.primarySkill)}</div>

          <div class="worker-card-meta">
            <span>${escapeHtml(w.distanceKm == null ? (w.location || this.text('directory.locationMissing')) : this.text('directory.distance', { km: w.distanceKm.toFixed(1) }))}</span>
            <span style="color:var(--primary-green); font-weight:600;">${escapeHtml(w.availabilityLabel || this.text('directory.availabilityUnknown'))}</span>
          </div>

          <div class="worker-rate-box">
            <span class="rate-amount" style="font-size:0.95rem;">${escapeHtml(w.rateLabel)}</span>
          </div>

          <!-- Actions -->
          <div class="worker-card-actions">
            <a href="../../pages/workers/profile.html?id=${w.id}" class="btn btn-outline btn-sm">${escapeHtml(this.text('directory.profile'))}</a>
            <button class="btn btn-primary btn-sm book-worker-btn" data-id="${escapeHtml(w.id)}">${escapeHtml(this.text('directory.ask'))}</button>
          </div>
        </div>
      </div>
    `).join('');

    // Attach Booking Trigger to buttons
    grid.querySelectorAll('.book-worker-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const workerId = e.currentTarget.dataset.id;
        const worker = this.workers.find(item => String(item.id) === String(workerId));
        if (worker && typeof BookingFlow !== 'undefined') {
          BookingFlow.openBooking(worker);
        }
      });
    });
  }
};

document.addEventListener('DOMContentLoaded', () => {
  WorkerDirectory.init();
});

document.addEventListener('kaamdo:language', () => {
  WorkerDirectory.render();
});
