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

  trackViewRequested() {
    const query = new URLSearchParams(window.location.search);
    const view = query.get('view');
    // My requests = status only. Create form only when ?view=new.
    return view !== 'new';
  },

  mountCustomer(card, user) {
    this.viewer = user || this.viewer || null;
    const trackOnly = this.trackViewRequested();

    const trackPanel = document.createElement('section');
    trackPanel.id = 'daily-track-panel';
    trackPanel.className = 'daily-track-panel';
    const trackHeading = document.createElement('h2');
    trackHeading.textContent = this.text('daily.trackTitle');
    const trackNote = document.createElement('p');
    trackNote.className = 'text-muted';
    trackNote.textContent = this.text('daily.trackNote');
    const status = document.createElement('p');
    status.id = 'daily-customer-status';
    status.setAttribute('role', 'status');
    status.textContent = this.text('daily.loading');
    const list = document.createElement('div');
    list.id = 'daily-customer-list';
    list.className = 'daily-track-list';
    trackPanel.append(trackHeading, trackNote, status, list);
    card.appendChild(trackPanel);

    const titleEl = document.getElementById('area-title');
    if (titleEl) titleEl.textContent = this.text('daily.trackTitle');
    this.loadCustomer(status, list);

    // Track page: existing requests only. New booking is a separate link.
    if (trackOnly) {
      const ask = document.createElement('a');
      ask.className = 'btn btn-outline btn-block action-gap';
      ask.href = 'guest-request.html';
      ask.textContent = this.text('track.newRequest');
      card.appendChild(ask);
      return;
    }

    this.mountCreateForm(card, status, list);
  },

  mountCreateForm(card, status, list) {
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
    const state = document.createElement('select');
    state.className = 'form-select';
    const district = document.createElement('select');
    district.className = 'form-select';
    const taluk = document.createElement('select');
    taluk.className = 'form-select';
    const place = document.createElement('input');
    place.className = 'form-input';
    place.maxLength = 120;
    place.autocomplete = 'street-address';
    const street = document.createElement('input');
    street.className = 'form-input';
    street.maxLength = 120;
    const pin = document.createElement('input');
    pin.className = 'form-input';
    pin.maxLength = 6;
    pin.inputMode = 'numeric';
    const placeHelp = document.createElement('p');
    placeHelp.className = 'text-muted';
    placeHelp.textContent = this.text('daily.placeHelp');
    const latitude = document.createElement('input');
    latitude.type = 'hidden';
    const longitude = document.createElement('input');
    longitude.type = 'hidden';
    const radiusHost = document.createElement('div');
    const radius = document.createElement('input');
    radius.required = true;
    if (typeof RadiusControl !== 'undefined') RadiusControl.mount(radiusHost, radius);
    else {
      radius.type = 'number';
      radius.min = '5';
      radius.max = '100';
      radius.step = '5';
      radius.value = '60';
      radiusHost.appendChild(radius);
    }
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
      this.labeled(this.text('form.state'), state),
      this.labeled(this.text('form.district'), district),
      this.labeled(this.text('form.taluk'), taluk),
      placeGroup,
      this.labeled(this.text('form.street'), street),
      this.labeled(this.text('form.pin'), pin),
      latitude,
      longitude,
      this.labeled(this.text('daily.radius'), radiusHost),
      locate,
      save,
    );
    const formStatus = document.createElement('p');
    formStatus.setAttribute('role', 'status');
    const heading = document.createElement('h2');
    heading.textContent = this.text('daily.requestTitle');
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('daily.customerNote');
    card.append(heading, note, form, formStatus);
    locate.addEventListener('click', () => this.useLocation({
      state, district, taluk, locality: place, street, pin, latitude, longitude,
    }, formStatus));
    form.addEventListener('submit', (event) => this.saveRequest(event, {
      category, description, state, district, taluk, place, street, pin, latitude, longitude, radius, formStatus, status, list, save,
    }));
    this.loadCategories(category, formStatus);
    if (typeof LocationFields !== 'undefined') {
      LocationFields.enhance({ state, district, taluk, locality: place });
    }
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

  async useLocation(fields, status) {
    if (typeof LocationDetect !== 'undefined') {
      await LocationDetect.detect({ fields, status });
      return;
    }
    if (typeof GeolocationUtil === 'undefined') {
      status.textContent = this.text('daily.locationFailed');
      return;
    }
    try {
      const position = await GeolocationUtil.getCurrentCoordinates();
      fields.latitude.value = GeolocationUtil.coordinateText(position.latitude);
      fields.longitude.value = GeolocationUtil.coordinateText(position.longitude);
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
      district: fields.district ? fields.district.value : '',
      taluk: fields.taluk ? fields.taluk.value : '',
      street: fields.street ? fields.street.value : '',
      pin: fields.pin ? fields.pin.value : '',
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
      const emptyText = this.text('daily.trackEmpty');
      const state = DailyAccountLogic.listState(null, rows, emptyText);
      this.customerStatus = status;
      this.customerList = list;
      list.replaceChildren();
      status.textContent = state.kind === 'empty'
        ? emptyText
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
    this.appendWorkerCard(article, row);
    this.mountPaymentActions(article, row, copy);
    this.requestActions(article, row, copy);
    this.mountOwnerArrival(article, row, copy);
    return article;
  },

  mountPaymentActions(article, row, copy) {
    const payment = row.payment || {};
    const notice = document.createElement('p');
    notice.className = 'text-muted';
    if (DailyAccountLogic.canPayInspection(row)) {
      notice.textContent = this.text('pay.inspectionHelp', {
        amount: payment.inspection_fee_inr || payment.payment_amount_inr || '99.00',
      });
      const pay = document.createElement('button');
      pay.type = 'button';
      pay.className = 'btn btn-primary action-gap';
      pay.textContent = this.text('pay.inspection');
      pay.addEventListener('click', () => this.openInspectionCheckout(row, pay, notice, copy));
      article.append(notice, pay);
      return;
    }
    if (DailyAccountLogic.canPayExtras(row)) {
      notice.textContent = this.text('pay.extrasHelp', { amount: payment.extras_due_inr || '0.00' });
      const pay = document.createElement('button');
      pay.type = 'button';
      pay.className = 'btn btn-primary action-gap';
      pay.textContent = this.text('pay.extras');
      pay.addEventListener('click', () => this.openExtrasCheckout(row, pay, notice, copy));
      article.append(notice, pay);
      return;
    }
    if (
      DailyAccountLogic.testPaymentEnabled(this.viewer)
      && DailyAccountLogic.canSkipPayment(row.status)
    ) {
      notice.textContent = this.text('pay.testBanner');
      const skip = document.createElement('button');
      skip.type = 'button';
      skip.className = 'btn btn-outline action-gap';
      skip.textContent = this.text('pay.skip');
      skip.addEventListener('click', () => this.skipPayment(row, skip, notice, copy));
      article.append(notice, skip);
    }
  },

  openInspectionCheckout(row, button, notice, copy) {
    const amount = (row.payment && (row.payment.inspection_fee_inr || row.payment.payment_amount_inr)) || '99.00';
    if (typeof MockCheckout === 'undefined') {
      this.skipPayment(row, button, notice, copy);
      return;
    }
    MockCheckout.open({
      title: this.text('pay.razorpayTitle'),
      amountInr: amount,
      note: this.text('pay.inspectionNote'),
      onConfirm: async () => {
        const data = await ApiClient.post(DailyAccountLogic.mockPaymentPath(row.reference), {});
        if (!data || data.money_received) throw new Error(this.text('pay.skipFailed'));
        row.status = data.status || row.status;
        row.payment = data.payment || row.payment;
        copy.textContent = `${this.text('guest.referenceLabel')} ${row.reference}. ${row.category}. ${row.description} ${this.statusLine(row.status)} ${row.radius_km} km.`;
        notice.textContent = data.detail || this.text('pay.skipped');
        button.remove();
      },
    });
  },

  openExtrasCheckout(row, button, notice, copy) {
    const amount = (row.payment && row.payment.extras_due_inr) || '0.00';
    if (typeof MockCheckout === 'undefined') return;
    MockCheckout.open({
      title: this.text('pay.razorpayExtrasTitle'),
      amountInr: amount,
      note: this.text('pay.extrasNote'),
      onConfirm: async () => {
        const data = await ApiClient.post(DailyAccountLogic.extraPaymentPath(row.reference), {});
        if (!data || data.money_received) throw new Error(this.text('pay.skipFailed'));
        row.payment = data.payment || row.payment;
        notice.textContent = data.detail || this.text('pay.extrasPaid');
        button.remove();
      },
    });
  },

  appendWorkerCard(article, row) {
    const shown = row.status === 'assigned' || row.status === 'in_progress' || row.status === 'completed';
    if (!shown || typeof WorkerIdentityCard === 'undefined') return;
    const card = WorkerIdentityCard.render(row.worker_identity || row.assigned_profile);
    if (card) article.appendChild(card);
  },

  mountOwnerArrival(article, row, copy) {
    const panel = document.createElement('div');
    panel.className = 'arrival-panel';
    const notice = document.createElement('p');
    notice.setAttribute('role', 'status');
    if (DailyAccountLogic.canVerifyArrival(row.status)) {
      const note = document.createElement('p');
      note.className = 'text-muted';
      note.textContent = this.text('arrival.ownerNote');
      const input = document.createElement('input');
      input.className = 'form-input';
      input.inputMode = 'numeric';
      input.maxLength = 6;
      input.autocomplete = 'one-time-code';
      input.setAttribute('aria-label', this.text('arrival.codeInput'));
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-primary';
      button.textContent = this.text('arrival.verify');
      button.addEventListener('click', () => this.verifyArrival(row, input, button, notice, copy));
      panel.append(note, input, button, notice);
      article.appendChild(panel);
      return;
    }
    if (DailyAccountLogic.canComplete(row.status, row.arrival_verified_at)) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-primary';
      button.textContent = this.text('arrival.complete');
      button.addEventListener('click', () => this.completeRequest(row, button, notice, copy));
      panel.append(button, notice);
      article.appendChild(panel);
    }
  },

  async verifyArrival(row, input, button, notice, copy) {
    const payload = DailyAccountLogic.arrivalCodePayload(input.value);
    if (!/^\d{6}$/.test(payload.code)) {
      notice.textContent = this.text('arrival.codeInvalid');
      return;
    }
    if (this.busy) return;
    this.busy = true;
    button.disabled = true;
    notice.textContent = this.text('arrival.verifying');
    try {
      const data = await ApiClient.post(DailyAccountLogic.arrivalVerifyPath(row.reference), payload);
      notice.textContent = (data && data.detail) || this.text('arrival.verified');
      if (data && data.status) {
        row.status = data.status;
        row.arrival_verified_at = data.arrival_verified_at || row.arrival_verified_at;
        copy.textContent = `${this.text('guest.referenceLabel')} ${row.reference}. ${row.category}. ${row.description} ${this.statusLine(row.status, row.assigned_profile && row.assigned_profile.display_name, row.match_reason)} ${row.radius_km} km.`;
      }
      if (this.customerStatus && this.customerList) this.loadCustomer(this.customerStatus, this.customerList);
    } catch (error) {
      notice.textContent = DailyAccountLogic.errorText(error);
      button.disabled = false;
    } finally {
      this.busy = false;
    }
  },

  async completeRequest(row, button, notice, copy) {
    if (this.busy) return;
    this.busy = true;
    button.disabled = true;
    notice.textContent = this.text('arrival.completing');
    try {
      const data = await ApiClient.post(DailyAccountLogic.completePath(row.reference), {});
      notice.textContent = (data && data.detail) || this.text('arrival.completed');
      if (data && data.status) {
        row.status = data.status;
        copy.textContent = `${this.text('guest.referenceLabel')} ${row.reference}. ${row.category}. ${row.description} ${this.statusLine(row.status, row.assigned_profile && row.assigned_profile.display_name)} ${row.radius_km} km.`;
      }
      button.remove();
      if (this.customerStatus && this.customerList) this.loadCustomer(this.customerStatus, this.customerList);
    } catch (error) {
      notice.textContent = DailyAccountLogic.errorText(error);
      button.disabled = false;
    } finally {
      this.busy = false;
    }
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
    if (
      !DailyAccountLogic.testPaymentEnabled(this.viewer)
      && !DailyAccountLogic.canPayInspection(row)
    ) return;
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
    const offerState = this.text(`offer.${row.state}`);
    copy.textContent = `${row.request.category}. ${row.request.description} ${this.text('guest.referenceLabel')} ${row.request.reference}. ${this.statusLine(row.request.status)} ${offerState === `offer.${row.state}` ? '' : offerState} ${row.request.radius_km} km.`;
    const actions = document.createElement('p');
    actions.setAttribute('role', 'status');
    article.append(copy, actions);
    this.offerButtons(actions, row, copy);
    if (DailyAccountLogic.canSignalArrival(row)) article.appendChild(this.arrivalSignalPanel(row));
    if (row.request && row.request.can_propose_extras) {
      article.appendChild(this.extrasProposePanel(row));
    }
    return article;
  },

  extrasProposePanel(row) {
    const panel = document.createElement('div');
    panel.className = 'arrival-panel';
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('pay.workerExtrasHelp');
    const menuLink = document.createElement('a');
    menuLink.href = 'price-menu.html';
    menuLink.className = 'btn btn-outline btn-sm action-gap';
    menuLink.textContent = this.text('pay.viewMenu');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-primary btn-sm';
    button.textContent = this.text('pay.addExtras');
    const notice = document.createElement('p');
    notice.setAttribute('role', 'status');
    button.addEventListener('click', () => this.proposeExtras(row, button, notice));
    panel.append(note, menuLink, button, notice);
    return panel;
  },

  async proposeExtras(row, button, notice) {
    if (this.busy) return;
    this.busy = true;
    button.disabled = true;
    notice.textContent = this.text('pay.loadingMenu');
    try {
      const menu = await ApiClient.get(DailyAccountLogic.priceMenuPath());
      const extras = Array.isArray(menu.extras) ? menu.extras : [];
      if (!extras.length) {
        notice.textContent = this.text('pay.menuEmpty');
        button.disabled = false;
        return;
      }
      const picked = extras.slice(0, 1);
      const data = await ApiClient.post(
        DailyAccountLogic.extrasPath(row.request.reference),
        { items: picked.map((item) => item.id) },
      );
      notice.textContent = data.detail || this.text('pay.extrasAdded', { title: picked[0].title });
      if (row.request) row.request.payment = data.payment || row.request.payment;
    } catch (error) {
      notice.textContent = DailyAccountLogic.errorText(error);
      button.disabled = false;
    } finally {
      this.busy = false;
    }
  },

  arrivalSignalPanel(row) {
    const panel = document.createElement('div');
    panel.className = 'arrival-panel';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-primary';
    button.textContent = this.text('arrival.signal');
    const notice = document.createElement('p');
    notice.setAttribute('role', 'status');
    button.addEventListener('click', () => this.signalArrival(row, button, notice, panel));
    panel.append(button, notice);
    return panel;
  },

  async signalArrival(row, button, notice, panel) {
    if (this.busy) return;
    this.busy = true;
    button.disabled = true;
    notice.textContent = this.text('arrival.signalling');
    try {
      const data = await ApiClient.post(
        DailyAccountLogic.arrivalSignalPath(row.request.reference),
        {},
      );
      const code = data && String(data.code || '');
      if (!/^\d{6}$/.test(code)) {
        notice.textContent = this.text('arrival.codeMissing');
        button.disabled = false;
        return;
      }
      button.remove();
      const label = document.createElement('p');
      label.className = 'text-muted';
      label.textContent = this.text('arrival.codeLabel');
      const shown = document.createElement('p');
      shown.className = 'arrival-code';
      shown.textContent = code;
      const help = document.createElement('p');
      help.className = 'text-muted';
      help.textContent = (data && data.detail) || this.text('arrival.codeHelp');
      notice.textContent = '';
      panel.append(label, shown, help);
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      notice.textContent = DailyAccountLogic.errorText(error);
      button.disabled = false;
    } finally {
      this.busy = false;
    }
  },

  offerButtons(actions, row, copy) {
    actions.replaceChildren();
    if (row.state !== 'offered') return;
    ['accept', 'decline'].forEach((decision) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = decision === 'accept' ? 'btn btn-primary action-gap' : 'btn btn-outline action-gap';
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
      copy.textContent = `${row.request.category}. ${row.request.description} ${this.text('guest.referenceLabel')} ${row.request.reference}. ${this.statusLine(row.request.status)} ${this.text(`offer.${row.state}`)} ${row.request.radius_km} km.`;
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
