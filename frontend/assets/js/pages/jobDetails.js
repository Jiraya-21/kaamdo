/**
 * One published ordinary job, loaded from the API.
 * Apply sends a message to the existing applications endpoint.
 */

const JobDetails = {
  jobId: null,
  kind: '',

  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  workType(value) {
    const keys = {
      full_time: 'list.fullTime',
      part_time: 'list.partTime',
      temporary: 'list.temporary',
      contract: 'list.contract',
    };
    return keys[value] ? this.text(keys[value]) : '';
  },

  init() {
    const params = new URLSearchParams(window.location.search);
    this.jobId = params.get('id');
    this.kind = params.get('kind') === 'agricultural' ? 'agricultural' : '';
    const paths = JobDetailsLogic.paths(this.kind, this.jobId);
    const back = document.getElementById('job-back-link');
    if (back) {
      back.href = paths.listHref;
      back.textContent = this.kind === 'agricultural' ? this.text('detail.backFarm') : this.text('detail.backJobs');
    }
    this.load();
  },

  root() {
    return document.getElementById('job-detail');
  },

  async load() {
    const root = this.root();
    if (!root) return;
    if (!this.jobId) {
      root.textContent = this.text('detail.missing');
      return;
    }
    root.textContent = this.text('detail.loading');
    try {
      const job = await ApiClient.get(JobDetailsLogic.paths(this.kind, this.jobId).job);
      this.render(job);
    } catch (error) {
      root.textContent = error && error.status === 404
        ? this.text('detail.unavailable')
        : this.text('detail.failed');
    }
  },

  render(job) {
    const root = this.root();
    root.replaceChildren();

    const title = document.createElement('h1');
    title.style.fontSize = '1.85rem';
    title.textContent = job.title;

    const place = document.createElement('p');
    place.className = 'text-muted';
    const where = [job.locality, job.district].filter(Boolean).join(', ');
    place.textContent = [where, this.workType(job.work_type)].filter(Boolean).join(' · ');

    const wage = document.createElement('p');
    wage.textContent = job.wage_negotiable
      ? this.text('list.wageNegotiable')
      : this.text('list.wage', { amount: job.wage_amount, period: job.wage_period });

    const poster = document.createElement('p');
    poster.className = 'text-muted';
    poster.textContent = job.poster_name ? this.text('detail.postedBy', { name: job.poster_name }) : '';

    const description = document.createElement('p');
    description.textContent = job.description;
    const scheduleText = this.kind === 'agricultural' ? JobDetailsLogic.scheduleText(job) : '';
    const schedule = document.createElement('p');
    schedule.textContent = scheduleText;

    const form = document.createElement('form');
    form.style.marginTop = '20px';
    const label = document.createElement('label');
    label.className = 'form-label';
    label.htmlFor = 'application-message';
    label.textContent = this.text('detail.message');
    const input = document.createElement('textarea');
    input.id = 'application-message';
    input.className = 'form-textarea';
    input.maxLength = 1000;
    input.rows = 4;
    const button = document.createElement('button');
    button.type = 'submit';
    button.className = 'btn btn-primary';
    button.style.marginTop = '12px';
    button.textContent = this.text('detail.apply');
    const notice = document.createElement('p');
    notice.id = 'application-notice';
    notice.setAttribute('role', 'status');
    form.append(label, input, button, notice);
    form.addEventListener('submit', (event) => this.apply(event, button, notice, input));

    const blocks = [title, place, wage, poster, description];
    if (scheduleText) blocks.push(schedule);
    blocks.push(form);
    root.append(...blocks);
  },

  noticeText(error) {
    const data = error && error.data;
    if (error && error.status === 401) return '';
    if (!data) return this.text('detail.applyFailed');
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.non_field_errors) && data.non_field_errors.length) {
      return data.non_field_errors.join(' ');
    }
    if (Array.isArray(data) && data.length) return String(data[0]);
    if (typeof data === 'object') {
      const first = Object.values(data)[0];
      if (Array.isArray(first) && first.length) return String(first[0]);
      if (typeof first === 'string') return first;
    }
    return this.text('detail.applyFailed');
  },

  async apply(event, button, notice, input) {
    event.preventDefault();
    notice.textContent = '';
    const token = StorageUtil.get(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    if (!token) {
      window.location.href = '../auth/login.html';
      return;
    }
    button.disabled = true;
    try {
      await ApiClient.post(JobDetailsLogic.paths(this.kind, this.jobId).apply, {
        message: input.value,
      });
      notice.textContent = this.text('detail.applied');
      input.value = '';
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      notice.textContent = this.noticeText(error);
    } finally {
      button.disabled = false;
    }
  },
};

document.addEventListener('DOMContentLoaded', () => JobDetails.init());

document.addEventListener('kaamdo:language', () => JobDetails.init());
