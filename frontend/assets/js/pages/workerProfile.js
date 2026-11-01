/**
 * Published worker profile.
 * Details come from the public worker API. Ratings and reliability scores are not available.
 */

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const WorkerProfilePage = {
  worker: null,
  row: null,

  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  init() {
    this.load();
  },

  async load() {
    const container = document.getElementById('worker-profile-app');
    if (!container) return;
    const params = new URLSearchParams(window.location.search);
    const workerId = params.get('id');
    if (!/^\d+$/.test(workerId || '')) {
      container.innerHTML = `<div class="container worker-profile-page"><p>${escapeHtml(this.text('profile.choose'))}</p></div>`;
      return;
    }
    container.innerHTML = `<div class="container worker-profile-page"><p class="text-muted">${escapeHtml(this.text('profile.loading'))}</p></div>`;
    try {
      const row = await ApiClient.get(`/workers/${workerId}/`);
      this.row = row;
      this.mapRow(row);
      this.render();
    } catch (error) {
      const missing = error && error.status === 404;
      container.innerHTML = `<div class="container worker-profile-page"><p>${escapeHtml(missing ? this.text('profile.choose') : this.text('directory.failed'))}</p></div>`;
    }
  },

  mapRow(row) {
    const available = row.availability === 'available';
    this.worker = {
      id: row.id,
      name: row.display_name || this.text('directory.workerFallback'),
      skills: row.skills || [],
      bio: row.bio || '',
      location: [row.locality, row.district].filter(Boolean).join(', ') || this.text('directory.locationMissing'),
      experience: row.experience_years,
      radiusKm: row.service_radius_km,
      available,
      availabilityLabel: available
        ? this.text('directory.available')
        : row.availability === 'unavailable'
          ? this.text('directory.unavailable')
          : this.text('directory.availabilityUnknown'),
      categories: Array.isArray(row.service_categories) ? row.service_categories : [],
      photo: typeof ProviderStatusLogic === 'undefined'
        ? '../../assets/images/placeholders/avatar-default.svg'
        : ProviderStatusLogic.photoSrc(row.photo_url),
      rateLabel: row.service_rate
        ? `${row.service_rate} ${row.pricing_basis || ''}`.trim()
        : this.text('directory.rateMissing'),
    };
  },

  render() {
    const w = this.worker;
    const container = document.getElementById('worker-profile-app');
    if (!container || !w) return;
    const skills = w.skills.length
      ? w.skills.map((skill) => `<span class="filter-chip">${escapeHtml(skill)}</span>`).join('')
      : `<span class="text-muted">${escapeHtml(this.text('profile.noSkills'))}</span>`;
    const categoryNames = w.categories.map((slug) => (
      typeof I18n === 'undefined' ? slug : I18n.categoryLabel(slug, slug)
    ));
    const availabilityClass = w.available ? 'is-available' : 'is-unavailable';

    container.innerHTML = `
      <div class="container worker-profile-page">
        <a href="directory.html" class="btn btn-outline btn-sm">${escapeHtml(this.text('profile.back'))}</a>
        <div class="card worker-profile-hero">
          <img class="worker-avatar" src="${escapeHtml(w.photo)}" alt="${escapeHtml(this.text('profile.photoAlt', { name: w.name }))}">
          <div>
            <h1>${escapeHtml(w.name)}</h1>
            <p class="worker-profile-meta">
              <span>${escapeHtml(w.location)}</span>
              <span>${escapeHtml(this.text('profile.experience', { years: w.experience == null ? '' : w.experience }))}</span>
              <span>${escapeHtml(this.text('profile.area', { km: w.radiusKm == null ? '' : w.radiusKm }))}</span>
            </p>
            <p class="worker-availability ${availabilityClass}">
              <span class="worker-availability-dot" aria-hidden="true"></span>
              <span>${escapeHtml(w.availabilityLabel)}</span>
            </p>
            <p class="text-muted">${escapeHtml(this.text('profile.availabilityNote'))}</p>
          </div>
          <div>
            <div class="worker-rate">
              <span class="text-muted">${escapeHtml(this.text('profile.listedRate'))}</span>
              <div>${escapeHtml(w.rateLabel)}</div>
            </div>
            <button type="button" id="book-worker-direct-btn" class="btn btn-primary btn-block">${escapeHtml(this.text('profile.ask'))}</button>
            <p class="text-muted">${escapeHtml(this.text('profile.askNote'))}</p>
          </div>
        </div>
        <div class="card worker-profile-body">
          <h2>${escapeHtml(this.text('profile.about'))}</h2>
          <p>${escapeHtml(w.bio) || escapeHtml(this.text('profile.noBio'))}</p>
          <h3>${escapeHtml(this.text('profile.categories'))}</h3>
          <p>${categoryNames.length ? escapeHtml(categoryNames.join(', ')) : escapeHtml(this.text('profile.noCategories'))}</p>
          <h3>${escapeHtml(this.text('profile.skills'))}</h3>
          <div class="worker-skill-list">${skills}</div>
          <p class="text-muted">${escapeHtml(this.text('profile.publishedNote'))}</p>
          <p class="text-muted">${escapeHtml(this.text('profile.noRatings'))}</p>
        </div>
      </div>
    `;

    const bookBtn = document.getElementById('book-worker-direct-btn');
    if (bookBtn) {
      bookBtn.addEventListener('click', () => {
        if (typeof BookingFlow !== 'undefined') BookingFlow.openBooking(w);
      });
    }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  WorkerProfilePage.init();
});

document.addEventListener('kaamdo:language', () => {
  if (WorkerProfilePage.row) {
    WorkerProfilePage.mapRow(WorkerProfilePage.row);
    WorkerProfilePage.render();
  }
});
