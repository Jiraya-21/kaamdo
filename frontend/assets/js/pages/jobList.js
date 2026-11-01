/**
 * Public ordinary jobs. Login is not required to read this list.
 * Work type, district, and search are sent to the API before pagination.
 */

function listText(key, values) {
  let text = typeof I18n === 'undefined' ? key : I18n.t(key);
  Object.keys(values || {}).forEach((name) => {
    text = text.split(`{${name}}`).join(String(values[name]));
  });
  return text;
}

const WORK_TYPE_KEYS = {
  full_time: 'list.fullTime',
  part_time: 'list.partTime',
  temporary: 'list.temporary',
  contract: 'list.contract',
};

const JobList = {
  jobs: [],
  loadError: '',
  requestId: 0,
  selectedWorkType: '',
  listPath: '/jobs/',
  detailKind: '',

  async init() {
    if (document.body.dataset.jobList === 'agricultural') {
      this.listPath = '/jobs/agricultural/';
      this.detailKind = 'agricultural';
    }
    this.bindControls();
    if (typeof LocationFields !== 'undefined') {
      await LocationFields.enhance({
        district: document.getElementById('job-district-input'),
        onChange: () => this.load(),
      });
    }
    await this.load();
  },

  filterValues() {
    return {
      query: document.getElementById('job-search-input')?.value || '',
      district: document.getElementById('job-district-input')?.value || '',
      workType: this.selectedWorkType,
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
    const container = document.getElementById('jobs-list-container');
    if (container) {
      container.textContent = listText(this.detailKind === 'agricultural' ? 'list.loadingFarm' : 'list.loadingJobs');
    }
    try {
      const params = JobListLogic.params(this.filterValues());
      const rows = await this.collect(this.listPath, params, true);
      if (requestId !== this.requestId) return;
      this.jobs = rows;
    } catch (error) {
      if (requestId !== this.requestId) return;
      this.jobs = [];
      this.loadError = error && error.status === 400
        ? listText('list.badFilter')
        : listText('list.jobsFailed');
    }
    this.render();
  },

  bindControls() {
    const searchInput = document.getElementById('job-search-input');
    if (searchInput) searchInput.addEventListener('change', () => this.load());
    const districtInput = document.getElementById('job-district-input');
    if (districtInput) districtInput.addEventListener('change', () => this.load());
    document.querySelectorAll('.job-work-type-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        document.querySelectorAll('.job-work-type-chip').forEach((item) => item.classList.remove('active'));
        chip.classList.add('active');
        this.selectedWorkType = chip.dataset.workType || '';
        this.load();
      });
    });
  },

  render() {
    const container = document.getElementById('jobs-list-container');
    const count = document.getElementById('jobs-results-count');
    if (!container) return;
    if (count) {
      const countKey = this.detailKind === 'agricultural' ? 'list.showingFarm' : 'list.showingJobs';
      count.textContent = this.loadError ? '' : listText(countKey, { count: this.jobs.length });
    }
    container.replaceChildren();
    if (this.loadError) {
      const error = document.createElement('p');
      error.textContent = this.loadError;
      container.appendChild(error);
      return;
    }
    if (!this.jobs.length) {
      const empty = document.createElement('p');
      empty.className = 'text-muted';
      empty.textContent = listText(this.detailKind === 'agricultural' ? 'list.emptyFarm' : 'list.emptyJobs');
      container.appendChild(empty);
      return;
    }
    this.jobs.forEach((job) => container.appendChild(this.card(job)));
  },

  card(job) {
    const card = document.createElement('article');
    card.className = 'card';
    card.style.padding = '20px';
    card.style.marginBottom = '16px';
    const title = document.createElement('h3');
    title.textContent = job.title;
    const place = document.createElement('p');
    place.className = 'text-muted';
    const where = typeof LocationFields === 'undefined'
      ? [job.locality, job.district].filter(Boolean).join(', ')
      : LocationFields.placeLabel(job.locality, job.taluk, job.district);
    const workType = WORK_TYPE_KEYS[job.work_type] ? listText(WORK_TYPE_KEYS[job.work_type]) : '';
    place.textContent = [where, workType].filter(Boolean).join(' · ');
    const wage = document.createElement('p');
    const periodKey = `list.${job.wage_period}`;
    const periodText = listText(periodKey);
    wage.textContent = job.wage_negotiable
      ? listText('list.wageNegotiable')
      : listText('list.wage', {
        amount: job.wage_amount,
        period: periodText === periodKey ? job.wage_period : periodText,
      });
    const copy = document.createElement('p');
    copy.textContent = job.description;
    const link = document.createElement('a');
    link.className = 'btn btn-primary btn-sm';
    link.href = this.detailKind === 'agricultural'
      ? `job-details.html?kind=agricultural&id=${job.id}`
      : `job-details.html?id=${job.id}`;
    link.textContent = listText('list.viewJob');
    card.append(title, place, wage, copy, link);
    return card;
  },
};

document.addEventListener('DOMContentLoaded', () => JobList.init());
document.addEventListener('kaamdo:language', () => {
  if (JobList.jobs) JobList.render();
});
