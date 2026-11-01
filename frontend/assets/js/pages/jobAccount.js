/**
 * Employer jobs and job-seeker applications.
 * Seekers can withdraw a submitted application. Employers can accept or reject one.
 */

const JobAccount = {
  busy: false,

  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  mountEmployer(card, paths) {
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('job.postsNote');
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    status.textContent = this.text('job.loadingPosts');
    const list = document.createElement('div');
    card.append(note, status, list);
    this.loadEmployer(paths || JobAccountLogic.ORDINARY, status, list);
  },

  mountSeeker(card, paths) {
    const browse = document.createElement('a');
    browse.className = 'btn btn-outline';
    browse.href = paths && paths === JobAccountLogic.FARM
      ? '../jobs/farm-jobs.html'
      : '../jobs/jobs-list.html';
    browse.textContent = this.text(paths && paths === JobAccountLogic.FARM ? 'farm.browseListings' : 'job.browseListings');
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('job.appsNote');
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    status.textContent = this.text('job.loadingApps');
    const list = document.createElement('div');
    card.append(browse, note, status, list);
    this.loadSeeker(paths || JobAccountLogic.ORDINARY, status, list);
  },

  async collect(path) {
    const rows = [];
    let endpoint = path;
    while (endpoint) {
      const page = await ApiClient.get(endpoint);
      if (page && Array.isArray(page.results)) rows.push(...page.results);
      if (!page || !page.next || !String(page.next).startsWith(CONFIG.API_BASE_URL)) break;
      endpoint = String(page.next).slice(CONFIG.API_BASE_URL.length);
    }
    return rows;
  },

  async loadEmployer(paths, status, list) {
    try {
      const jobs = (await this.collect(paths.mine)).map((row) => JobAccountLogic.jobView(row));
      const state = JobAccountLogic.listState(null, jobs, this.text('job.noPosts'));
      list.replaceChildren();
      status.textContent = state.kind === 'empty' ? state.text : this.text('job.postsCount', { count: jobs.length });
      for (const job of jobs) {
        const applications = (await this.collect(paths.jobApplications(job.id)))
          .map((row) => JobAccountLogic.applicationView(row));
        list.appendChild(this.jobBlock(paths, job, applications));
      }
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      status.textContent = JobAccountLogic.errorText(error);
    }
  },

  async loadSeeker(paths, status, list) {
    try {
      const rows = (await this.collect(paths.applications)).map((row) => JobAccountLogic.applicationView(row));
      const state = JobAccountLogic.listState(null, rows, this.text('job.noSeekerApps'));
      list.replaceChildren();
      status.textContent = state.kind === 'empty' ? state.text : this.text('job.appsCount', { count: rows.length });
      rows.forEach((row) => list.appendChild(this.seekerRow(paths, row)));
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      status.textContent = JobAccountLogic.errorText(error);
    }
  },

  jobBlock(paths, job, applications) {
    const block = document.createElement('section');
    const title = document.createElement('h3');
    title.textContent = job.title;
    const meta = document.createElement('p');
    meta.textContent = `${(typeof LocationFields === 'undefined' ? [job.locality, job.district] : [job.locality, job.taluk, job.district]).filter(Boolean).join(', ')}. Status: ${job.status}. Review: ${job.review_status}.`;
    block.append(title, meta);
    if (JobAccountLogic.closeGate(false, job).ok) {
      const close = document.createElement('button');
      close.type = 'button';
      close.className = 'btn btn-outline btn-sm action-gap';
      close.textContent = this.text('job.close');
      close.addEventListener('click', () => this.closePost(paths, job, close, meta));
      block.appendChild(close);
    }
    if (!applications.length) {
      const empty = document.createElement('p');
      empty.className = 'text-muted';
      empty.textContent = this.text('job.noApps');
      block.appendChild(empty);
      return block;
    }
    applications.forEach((application) => {
      const article = document.createElement('article');
      const copy = document.createElement('p');
      const when = application.created_at ? ` Submitted: ${application.created_at}.` : '';
      copy.textContent = `${application.applicant_name}. ${application.message} Status: ${application.status}.${when}`;
      const actions = document.createElement('p');
      actions.setAttribute('role', 'status');
      article.append(copy, actions);
      JobAccountLogic.employerActions(application).forEach((status) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-outline btn-sm';
        button.style.marginRight = '8px';
        button.textContent = this.text(status === 'accepted' ? 'job.accept' : 'job.reject');
        button.addEventListener('click', () => this.decide(paths, job, application, status, button, actions, copy));
        actions.appendChild(button);
      });
      block.appendChild(article);
    });
    return block;
  },

  async closePost(paths, job, button, meta) {
    const gate = JobAccountLogic.closeGate(this.busy, job);
    if (!gate.ok) return;
    this.busy = true;
    button.disabled = true;
    try {
      const data = await ApiClient.patch(paths.detail(job.id), gate.payload);
      job.status = data && data.status ? String(data.status) : 'closed';
      meta.textContent = `${(typeof LocationFields === 'undefined' ? [job.locality, job.district] : [job.locality, job.taluk, job.district]).filter(Boolean).join(', ')}. Status: ${job.status}. Review: ${job.review_status}.`;
      button.remove();
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      button.disabled = false;
      meta.textContent = JobAccountLogic.errorText(error);
    } finally {
      this.busy = false;
    }
  },

  async decide(paths, job, application, status, button, actions, copy) {
    const gate = JobAccountLogic.decisionGate(this.busy, application, status);
    if (!gate.ok) return;
    this.busy = true;
    Array.from(actions.querySelectorAll('button')).forEach((item) => { item.disabled = true; });
    const notice = document.createElement('span');
    notice.textContent = ` ${this.text('job.saving')}`;
    actions.appendChild(notice);
    try {
      const data = await ApiClient.patch(paths.decision(job.id, application.id), gate.payload);
      application.status = data && data.status ? String(data.status) : application.status;
      copy.textContent = `${application.applicant_name}. ${application.message} Status: ${application.status}.`;
      Array.from(actions.querySelectorAll('button')).forEach((item) => item.remove());
      notice.textContent = application.status === 'accepted'
        ? ` ${this.text('job.accepted')}`
        : application.status === 'rejected'
          ? ` ${this.text('job.rejected')}`
          : ` ${this.text('job.withdrawFailed')}`;
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      notice.textContent = ` ${JobAccountLogic.errorText(error)}`;
      Array.from(actions.querySelectorAll('button')).forEach((item) => { item.disabled = false; });
    } finally {
      this.busy = false;
    }
  },

  seekerRow(paths, application) {
    const article = document.createElement('article');
    const copy = document.createElement('p');
    const place = [application.job_locality, application.job_district].filter(Boolean).join(', ');
    const when = application.created_at ? ` Submitted: ${application.created_at}.` : '';
    copy.textContent = `${application.job_title}. ${place}. Job status: ${application.job_status}. Your status: ${application.status}.${when} ${application.message}`;
    const actions = document.createElement('p');
    actions.setAttribute('role', 'status');
    article.append(copy, actions);
    if (application.status === 'submitted') {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-outline btn-sm';
      button.textContent = this.text('job.withdraw');
      button.addEventListener('click', () => this.withdraw(paths, application, button, actions, copy));
      actions.appendChild(button);
    }
    return article;
  },

  async withdraw(paths, application, button, actions, copy) {
    const gate = JobAccountLogic.withdrawGate(this.busy, application);
    if (!gate.ok) return;
    this.busy = true;
    button.disabled = true;
    const notice = document.createElement('span');
    notice.textContent = ` ${this.text('job.saving')}`;
    actions.appendChild(notice);
    try {
      const data = await ApiClient.patch(paths.application(application.id), gate.payload);
      const next = JobAccountLogic.applyWithdraw(application, data);
      application.status = next.status;
      copy.textContent = `${application.job_title}. Job status: ${application.job_status}. Your status: ${application.status}.`;
      button.remove();
      notice.textContent = application.status === 'withdrawn'
        ? ` ${this.text('job.withdrawn')}`
        : ` ${this.text('job.withdrawFailed')}`;
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      notice.textContent = ` ${JobAccountLogic.errorText(error)}`;
      button.disabled = false;
    } finally {
      this.busy = false;
    }
  },
};
