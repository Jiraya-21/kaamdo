/**
 * Farm hiring on the agriculture account page.
 * Create uses POST /jobs/agricultural/. Apply uses the agricultural applications endpoint.
 */

const FarmHiring = {
  busy: false,

  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  periodLabel(value) {
    const key = `list.${value === 'hourly' ? 'hourly' : value === 'weekly' ? 'weekly' : value === 'monthly' ? 'monthly' : 'daily'}`;
    return this.text(key);
  },

  mountEmployer(card) {
    const form = document.createElement('form');
    form.id = 'farm-create-form';
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('farm.note');
    const title = this.input('farm-title', 'text', 120);
    const district = document.createElement('select');
    district.id = 'farm-district';
    district.className = 'form-select';
    const taluk = document.createElement('select');
    taluk.id = 'farm-taluk';
    taluk.className = 'form-select';
    const locality = this.input('farm-locality', 'text', 120);
    const headcount = this.input('farm-headcount', 'number');
    headcount.min = '1';
    headcount.max = '100';
    headcount.value = '1';
    const wage = this.input('farm-wage', 'number');
    wage.min = '0.01';
    wage.step = '0.01';
    const period = document.createElement('select');
    period.id = 'farm-wage-period';
    period.className = 'form-select';
    ['hourly', 'daily', 'weekly', 'monthly'].forEach((value) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = this.periodLabel(value);
      if (value === 'daily') option.selected = true;
      period.appendChild(option);
    });
    const negotiable = document.createElement('input');
    negotiable.type = 'checkbox';
    negotiable.id = 'farm-negotiable';
    const description = document.createElement('textarea');
    description.id = 'farm-description';
    description.className = 'form-textarea';
    description.maxLength = 2000;
    description.rows = 4;
    const start = this.input('farm-start', 'date');
    const end = this.input('farm-end', 'date');
    const hours = this.input('farm-hours', 'text', 80);
    const status = document.createElement('p');
    status.id = 'farm-notice';
    status.setAttribute('role', 'status');
    const button = document.createElement('button');
    button.type = 'submit';
    button.className = 'btn btn-primary';
    button.id = 'farm-submit';
    button.textContent = this.text('farm.submit');
    const negotiableLabel = document.createElement('label');
    negotiableLabel.className = 'form-label';
    negotiableLabel.htmlFor = 'farm-negotiable';
    negotiableLabel.append(negotiable, document.createTextNode(` ${this.text('form.wageNegotiable')}`));
    form.append(
      note,
      this.labeled(this.text('farm.title'), title),
      this.labeled(this.text('form.district'), district),
      this.labeled(this.text('form.taluk'), taluk),
      this.labeled(this.text('form.locality'), locality),
      this.labeled(this.text('form.vacancies'), headcount),
      this.labeled(this.text('form.wageAmount'), wage),
      this.labeled(this.text('form.wagePeriod'), period),
      negotiableLabel,
      this.labeled(this.text('form.description'), description),
      this.labeled(this.text('farm.start'), start),
      this.labeled(this.text('farm.end'), end),
      this.labeled(this.text('farm.hours'), hours),
      status,
      button,
    );
    if (typeof LocationFields !== 'undefined') {
      LocationFields.enhance({ district, taluk, locality });
    }
    form.addEventListener('submit', (event) => this.submitPost(event, button, status));
    const editor = document.createElement('details');
    editor.className = 'account-details';
    const summary = document.createElement('summary');
    summary.textContent = this.text('farm.createPost');
    editor.append(summary, form);
    card.appendChild(editor);
  },

  mountWorker(card) {
    const browse = document.createElement('a');
    browse.className = 'btn btn-outline';
    browse.href = '../jobs/farm-jobs.html';
    browse.textContent = this.text('farm.browseListings');
    const list = document.createElement('div');
    list.id = 'farm-list';
    list.textContent = this.text('farm.loading');
    card.append(browse, list);
    this.loadPosts(list);
  },

  input(id, type, maxLength) {
    const field = document.createElement('input');
    field.id = id;
    field.type = type;
    field.className = 'form-input';
    if (maxLength) field.maxLength = maxLength;
    return field;
  },

  labeled(text, control) {
    const group = document.createElement('div');
    group.className = 'form-group';
    const label = document.createElement('label');
    label.className = 'form-label';
    label.htmlFor = control.id;
    label.textContent = text;
    group.append(label, control);
    return group;
  },

  values() {
    return {
      title: document.getElementById('farm-title').value,
      description: document.getElementById('farm-description').value,
      district: document.getElementById('farm-district').value,
      taluk: document.getElementById('farm-taluk') ? document.getElementById('farm-taluk').value : '',
      locality: document.getElementById('farm-locality').value,
      wageAmount: document.getElementById('farm-wage').value,
      wageNegotiable: document.getElementById('farm-negotiable').checked,
      wagePeriod: document.getElementById('farm-wage-period').value,
      headcount: document.getElementById('farm-headcount').value,
      workStart: document.getElementById('farm-start').value,
      workEnd: document.getElementById('farm-end').value,
      workingHours: document.getElementById('farm-hours').value,
    };
  },

  async submitPost(event, button, status) {
    event.preventDefault();
    if (this.busy) return;
    const values = this.values();
    const problems = PostFormLogic.farmProblems(values);
    if (problems.length) {
      status.textContent = problems.join(' ');
      return;
    }
    this.busy = true;
    button.disabled = true;
    try {
      const data = await ApiClient.post(PostFormLogic.FARM_PATH, PostFormLogic.farmPayload(values));
      status.textContent = PostFormLogic.farmResult(data).text;
    } catch (error) {
      status.textContent = PostFormLogic.errorText(error);
    } finally {
      this.busy = false;
      button.disabled = false;
    }
  },

  async loadPosts(list) {
    try {
      const page = await ApiClient.get(PostFormLogic.FARM_PATH);
      const rows = page && page.results ? page.results : [];
      list.replaceChildren();
      if (!rows.length) {
        list.textContent = this.text('farm.empty');
        return;
      }
      rows.forEach((job) => list.appendChild(this.jobCard(job)));
    } catch (error) {
      list.textContent = this.text('farm.failed');
    }
  },

  jobCard(job) {
    const card = document.createElement('article');
    card.className = 'account-card';
    const title = document.createElement('h3');
    title.textContent = job.title;
    const place = document.createElement('p');
    place.className = 'text-muted';
    place.textContent = typeof LocationFields === 'undefined'
      ? [job.locality, job.district].filter(Boolean).join(', ')
      : LocationFields.placeLabel(job.locality, job.taluk, job.district);
    const wage = document.createElement('p');
    wage.textContent = job.wage_negotiable
      ? this.text('list.wageNegotiable')
      : this.text('list.wage', { amount: job.wage_amount, period: this.periodLabel(job.wage_period) });
    const dates = document.createElement('p');
    const start = job.work_start || '';
    const end = job.work_end || '';
    dates.textContent = start || end
      ? this.text('farm.dates', { start: start || this.text('farm.open'), end: end || this.text('farm.open') })
      : '';
    const hours = document.createElement('p');
    hours.textContent = job.working_hours ? this.text('farm.hoursLine', { hours: job.working_hours }) : '';
    const description = document.createElement('p');
    description.textContent = job.description;
    const form = document.createElement('form');
    const message = document.createElement('textarea');
    message.className = 'form-textarea';
    message.maxLength = 1000;
    message.rows = 3;
    const button = document.createElement('button');
    button.type = 'submit';
    button.className = 'btn btn-primary btn-sm';
    button.textContent = this.text('farm.apply');
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    form.append(this.labeled(this.text('farm.message'), message), status, button);
    form.addEventListener('submit', (event) => this.apply(event, job.id, message, button, status));
    card.append(title, place, wage, dates, hours, description, form);
    return card;
  },

  async apply(event, jobId, message, button, status) {
    event.preventDefault();
    if (this.busy) return;
    const text = PostFormLogic.clean(message.value);
    if (text.length > 1000) {
      status.textContent = this.text('farm.messageLimit');
      return;
    }
    this.busy = true;
    button.disabled = true;
    try {
      await ApiClient.post(PostFormLogic.farmApplyPath(jobId), { message: text });
      status.textContent = this.text('farm.applied');
      message.value = '';
    } catch (error) {
      status.textContent = PostFormLogic.errorText(error);
    } finally {
      this.busy = false;
      button.disabled = false;
    }
  },
};
