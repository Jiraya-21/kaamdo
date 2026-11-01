/**
 * Daily Services lists on the customer and service-provider account pages.
 * Accept and decline use the existing offer response. This file does not call mock payment.
 */

const DailyAccount = {
  busy: false,

  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  label(slug, name) {
    return typeof I18n === 'undefined' ? name : I18n.categoryLabel(slug, name);
  },

  statusLine(status, workerName, reason) {
    const extra = DailyAccountLogic.reasonSentence(reason);
    if (extra) return extra;
    return typeof I18n === 'undefined'
      ? DailyAccountLogic.statusSentence(status, workerName)
      : I18n.statusText(status, workerName);
  },

  mountCustomer(card, user) {
    this.viewer = user || this.viewer || null;
    const heading = document.createElement('h2');
    heading.textContent = this.text('daily.requestTitle');
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('daily.customerNote');
    const form = document.createElement('form');
    const category = document.createElement('select');
    category.className = 'form-input';
    category.required = true;
    const categoryPlaceholder = document.createElement('option');
    categoryPlaceholder.value = '';
    categoryPlaceholder.textContent = this.text('guest.chooseCategory');
    category.appendChild(categoryPlaceholder);
    const description = document.createElement('textarea');
    description.className = 'form-textarea';
    description.rows = 4;
    description.maxLength = 1000;
    description.required = true;
    const place = document.createElement('input');
    place.className = 'form-input';
    place.maxLength = 120;
    place.autocomplete = 'street-address';
    const placeHelp = document.createElement('p');
    placeHelp.className = 'text-muted';
    placeHelp.textContent = this.text('daily.placeHelp');
    const latitude = document.createElement('input');
    latitude.type = 'hidden';
    const longitude = document.createElement('input');
    longitude.type = 'hidden';
    const radius = document.createElement('input');
    radius.className = 'form-input';
    radius.type = 'number';
    radius.min = '8';
    radius.max = '50';
    radius.value = '15';
    radius.required = true;
    const locate = document.createElement('button');
    locate.type = 'button';
    locate.className = 'btn btn-outline';
    locate.textContent = this.text('daily.locate');
    const save = document.createElement('button');
    save.type = 'submit';
    save.className = 'btn btn-primary action-gap';
    save.textContent = this.text('daily.save');
    const placeGroup = this.labeled(this.text('daily.place'), place);
    placeGroup.appendChild(placeHelp);
    form.append(
      this.labeled(this.text('daily.category'), category),
      this.labeled(this.text('daily.work'), description),
      placeGroup,
      latitude,
      longitude,
      this.labeled(this.text('daily.radius'), radius),
      locate,
      save,
    );
    const formStatus = document.createElement('p');
    formStatus.setAttribute('role', 'status');
    const listNote = document.createElement('p');
    listNote.className = 'text-muted';
    listNote.textContent = this.text('daily.customerNote');
    const status = document.createElement('p');
    status.id = 'daily-customer-status';
    status.setAttribute('role', 'status');
    status.textContent = this.text('daily.loading');
    const list = document.createElement('div');
    list.id = 'daily-customer-list';
    card.append(heading, note, form, formStatus, listNote, status, list);
    locate.addEventListener('click', () => this.useLocation(latitude, longitude, formStatus));
    form.addEventListener('submit', (event) => this.saveRequest(event, {
      category, description, place, latitude, longitude, radius, formStatus, status, list, save,
    }));
    this.loadCategories(category, formStatus);
    this.loadCustomer(status, list);
  },

  labeled(text, control) {
    const wrap = document.createElement('div');
    wrap.className = 'form-group';
    const label = document.createElement('label');
    label.className = 'form-label';
    label.textContent = text;
    wrap.append(label, control);
    return wrap;
  },

  async loadCategories(select, status) {
    try {
      const rows = [];
      let endpoint = DailyAccountLogic.CATEGORY_PATH;
      while (endpoint) {
        const page = await ApiClient.get(endpoint);
        rows.push(...DailyAccountLogic.rowsFrom(page));
        if (!page || !page.next || !String(page.next).startsWith(CONFIG.API_BASE_URL)) break;
        endpoint = String(page.next).slice(CONFIG.API_BASE_URL.length);
      }
      rows.forEach((row) => {
        if (!row || !row.id || !row.name) return;
        const option = document.createElement('option');
        option.value = String(row.id);
        option.dataset.slug = row.slug || '';
        option.dataset.fallback = row.name || '';
        option.textContent = this.label(row.slug, row.name);
        select.appendChild(option);
      });
      if (!rows.length) status.textContent = this.text('daily.noCategories');
    } catch (error) {
      status.textContent = DailyAccountLogic.errorText(error);
    }
  },

  async useLocation(latitude, longitude, status) {
    if (typeof GeolocationUtil === 'undefined') {
      status.textContent = this.text('daily.locationFailed');
      return;
    }
    try {
      const position = await GeolocationUtil.getCurrentCoordinates();
      latitude.value = GeolocationUtil.coordinateText(position.latitude);
      longitude.value = GeolocationUtil.coordinateText(position.longitude);
      status.textContent = this.text('daily.located');
    } catch (error) {
      status.textContent = this.text('daily.locationFailed');
    }
  },

  async saveRequest(event, fields) {
    event.preventDefault();
    const values = {
      categoryId: fields.category.value,
      description: fields.description.value,
      place: fields.place.value,
      latitude: fields.latitude.value,
      longitude: fields.longitude.value,
      radiusKm: fields.radius.value,
    };
    const problems = DailyAccountLogic.requestProblems(values);
    if (problems.length) {
      fields.formStatus.textContent = problems.includes(
        'Use this phone location before saving. A place name is kept with the request, but it does not find a worker by itself.',
      )
        ? this.text('guest.needLocation')
        : problems.join(' ');
      return;
    }
    if (this.busy) return;
    this.busy = true;
    fields.save.disabled = true;
    fields.formStatus.textContent = this.text('daily.saving');
    try {
      const data = await ApiClient.post(DailyAccountLogic.REQUESTS_PATH, DailyAccountLogic.requestPayload(values));
      const result = DailyAccountLogic.createResult(data);
      fields.formStatus.textContent = result.text;
      if (result.ok) {
        fields.description.value = '';
        fields.place.value = '';
        this.loadCustomer(fields.status, fields.list);
      }
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      fields.formStatus.textContent = DailyAccountLogic.errorText(error);
    } finally {
      this.busy = false;
      fields.save.disabled = false;
    }
  },

  mountProvider(card) {
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('daily.offerNote');
    const status = document.createElement('p');
    status.id = 'daily-provider-status';
    status.setAttribute('role', 'status');
    status.textContent = this.text('daily.offerLoading');
    const list = document.createElement('div');
    list.id = 'daily-provider-list';
    card.append(note, status, list);
    this.loadProvider(status, list);
  },

  async loadCustomer(status, list) {
    try {
      const data = await ApiClient.get(DailyAccountLogic.REQUESTS_PATH);
      const rows = DailyAccountLogic.rowsFrom(data).map((row) => DailyAccountLogic.customerView(row));
      const state = DailyAccountLogic.listState(null, rows, this.text('daily.empty'));
      list.replaceChildren();
      status.textContent = state.kind === 'empty'
        ? state.text
        : this.text('daily.count', { count: rows.length });
      rows.forEach((row) => list.appendChild(this.customerRow(row)));
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      status.textContent = DailyAccountLogic.errorText(error);
    }
  },

  async loadProvider(status, list) {
    try {
      const data = await ApiClient.get(DailyAccountLogic.OFFERS_PATH);
      const rows = DailyAccountLogic.rowsFrom(data).map((row) => DailyAccountLogic.offerView(row));
      const state = DailyAccountLogic.listState(null, rows, this.text('daily.offerEmpty'));
      list.replaceChildren();
      status.textContent = state.kind === 'empty'
        ? state.text
        : this.text('daily.offerCount', { count: rows.length });
      rows.forEach((row) => list.appendChild(this.offerRow(row)));
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      status.textContent = DailyAccountLogic.errorText(error);
    }
  },

  customerRow(row) {
    const article = document.createElement('article');
    const copy = document.createElement('p');
    const sentence = this.statusLine(
      row.status,
      row.assigned_profile && row.assigned_profile.display_name,
      row.match_reason,
    );
    const placeValue = row.assigned_profile && (row.status === 'assigned' || row.status === 'in_progress' || row.status === 'completed')
      ? [row.assigned_profile.locality, row.assigned_profile.district].filter(Boolean).join(', ')
      : '';
    const place = placeValue ? this.text('daily.workerPlace', { place: placeValue }) : '';
    const when = row.created_at ? this.text('daily.opened', { when: row.created_at }) : '';
    copy.textContent = `${this.text('guest.referenceLabel')} ${row.reference}. ${row.category}. ${row.description} ${sentence}${place} ${row.radius_km} km.${when}`;
    article.appendChild(copy);
    if (
      DailyAccountLogic.testPaymentEnabled(this.viewer)
      && DailyAccountLogic.canSkipPayment(row.status)
    ) {
      const skip = document.createElement('button');
      skip.type = 'button';
      skip.className = 'btn btn-outline action-gap';
      skip.textContent = this.text('pay.skip');
      const notice = document.createElement('p');
      notice.className = 'text-muted';
      notice.textContent = this.text('pay.testBanner');
      skip.addEventListener('click', () => this.skipPayment(row, skip, notice, copy));
      article.append(notice, skip);
    }
    this.requestActions(article, row, copy);
    return article;
  },

  requestActions(article, row, copy) {
    if (row.can_expand && row.expand_to_km) {
      const expand = document.createElement('button');
      expand.type = 'button';
      expand.className = 'btn btn-outline btn-sm action-gap';
      expand.textContent = this.text('track.expand', { km: row.expand_to_km });
      expand.addEventListener('click', () => this.expandRequest(row, expand, copy));
      article.appendChild(expand);
    }
    if (row.status && row.status !== 'cancelled' && row.status !== 'completed' && row.status !== 'in_progress') {
      const cancel = document.createElement('button');
      cancel.type = 'button';
      cancel.className = 'btn btn-outline btn-sm action-gap';
      cancel.textContent = this.text('track.cancel');
      cancel.addEventListener('click', () => this.cancelRequest(row, cancel, copy));
      article.appendChild(cancel);
    }
  },

  async expandRequest(row, button, copy) {
    if (this.busy) return;
    this.busy = true;
    button.disabled = true;
    try {
      const data = await ApiClient.post(DailyAccountLogic.expandPath(row.reference), {
        radius_km: row.expand_to_km,
      });
      row.status = data.status || row.status;
      row.match_reason = data.match_reason || '';
      row.can_expand = false;
      copy.textContent = `${this.text('guest.referenceLabel')} ${row.reference}. ${row.category}. ${row.description} ${this.statusLine(row.status, '', row.match_reason)} ${row.radius_km} km.`;
      button.remove();
    } catch (error) {
      button.disabled = false;
      copy.textContent = DailyAccountLogic.errorText(error);
    } finally {
      this.busy = false;
    }
  },

  async cancelRequest(row, button, copy) {
    if (this.busy) return;
    this.busy = true;
    button.disabled = true;
    try {
      const data = await ApiClient.post(DailyAccountLogic.cancelPath(row.reference), {});
      row.status = data.status || 'cancelled';
      copy.textContent = `${this.text('guest.referenceLabel')} ${row.reference}. ${row.category}. ${row.description} ${this.statusLine(row.status)} ${row.radius_km} km.`;
      button.remove();
    } catch (error) {
      button.disabled = false;
      copy.textContent = DailyAccountLogic.errorText(error);
    } finally {
      this.busy = false;
    }
  },

  async skipPayment(row, button, notice, copy) {
    if (this.busy) return;
    if (!DailyAccountLogic.testPaymentEnabled(this.viewer)) return;
    this.busy = true;
    button.disabled = true;
    notice.textContent = this.text('pay.skipping');
    try {
      const data = await ApiClient.post(DailyAccountLogic.mockPaymentPath(row.reference), {});
      if (!data || data.money_received) {
        notice.textContent = this.text('pay.skipFailed');
        button.disabled = false;
        return;
      }
      row.status = data.status || row.status;
      copy.textContent = `${this.text('guest.referenceLabel')} ${row.reference}. ${row.category}. ${row.description} ${this.statusLine(row.status)} ${row.radius_km} km.`;
      notice.textContent = data.detail || this.text('pay.skipped');
      button.remove();
    } catch (error) {
      notice.textContent = DailyAccountLogic.errorText(error) || this.text('pay.skipFailed');
      button.disabled = false;
    } finally {
      this.busy = false;
    }
  },

  offerRow(row) {
    const article = document.createElement('article');
    const copy = document.createElement('p');
    copy.textContent = `${row.request.category}. ${row.request.description} ${this.text('guest.referenceLabel')} ${row.request.reference}. ${row.request.status}. ${row.state}. ${row.request.radius_km} km.`;
    const actions = document.createElement('p');
    actions.setAttribute('role', 'status');
    article.append(copy, actions);
    this.offerButtons(actions, row, copy);
    return article;
  },

  offerButtons(actions, row, copy) {
    actions.replaceChildren();
    if (row.state !== 'offered') return;
    ['accept', 'decline'].forEach((decision) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-outline btn-sm action-gap';
      button.textContent = this.text(decision === 'accept' ? 'daily.accept' : 'daily.decline');
      button.addEventListener('click', () => this.respond(row, decision, actions, copy));
      actions.appendChild(button);
    });
  },

  async respond(row, decision, actions, copy) {
    const gate = DailyAccountLogic.respondGate(this.busy, row, decision);
    if (!gate.ok) return;
    this.busy = true;
    actions.textContent = this.text('job.saving');
    try {
      const data = await ApiClient.post(DailyAccountLogic.respondPath(row.id), gate.payload);
      const next = DailyAccountLogic.applyResponse(row, data);
      row.state = next.state;
      row.request.status = next.request.status;
      copy.textContent = `${row.request.category}. ${row.request.description} ${this.text('guest.referenceLabel')} ${row.request.reference}. ${row.request.status}. ${row.state}. ${row.request.radius_km} km.`;
      actions.textContent = DailyAccountLogic.responseText(data);
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      actions.textContent = DailyAccountLogic.errorText(error);
      this.offerButtons(actions, row, copy);
    } finally {
      this.busy = false;
    }
  },
};
