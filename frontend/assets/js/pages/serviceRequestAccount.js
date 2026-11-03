/**
 * Provider profile, customer direct requests, and provider decisions.
 * Uses the existing profile and service-request routes. This file does not collect a payment.
 */

const ServiceRequestAccount = {
  busy: false,
  hasProfile: false,

  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  mountCustomer(card) {
    const heading = document.createElement('h3');
    heading.textContent = this.text('direct.sentTitle');
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('direct.sentNote');
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    status.textContent = this.text('direct.loading');
    const list = document.createElement('div');
    card.append(heading, note, status, list);
    this.loadCustomer(status, list);
  },

  mountProvider(card, user) {
    if (typeof ProviderStatus !== 'undefined') {
      this.availabilityState = ProviderStatus.mountAvailability(card, {
        compact: true,
        onLoaded: (value, hasProfile, data) => {
          this.hasProfile = hasProfile;
          this.availabilityValue = value;
          if (this.profileFields && this.profileFields.availability) {
            this.profileFields.availability.value = value || 'available';
          }
          if (this.photoState && typeof ProviderStatus.applyPhoto === 'function') {
            ProviderStatus.applyPhoto(this.photoState, data && data.photo_url, hasProfile);
          }
          if (data) this.fillProfileView(data, user);
        },
        onSaved: (value) => {
          this.availabilityValue = value;
          if (this.profileFields && this.profileFields.availability) {
            this.profileFields.availability.value = value;
          }
        },
      });
    }
    const panels = this.mountWorkspaceTabs(card);
    this.mountProfileArea(panels.profile, user);
    this.mountIncoming(panels.requests);
    if (typeof DailyAccount !== 'undefined') DailyAccount.mountProvider(panels.offers);
  },

  mountWorkspaceTabs(card) {
    const nav = document.createElement('div');
    nav.className = 'workspace-tabs';
    nav.setAttribute('role', 'tablist');
    nav.setAttribute('aria-label', this.text('workspace.tabsLabel'));
    const tabs = {};
    const panels = {};
    const items = [
      ['profile', 'workspace.tabProfile'],
      ['requests', 'workspace.tabRequests'],
      ['offers', 'workspace.tabOffers'],
    ];
    items.forEach(([id, key]) => {
      const tab = document.createElement('button');
      tab.type = 'button';
      tab.className = 'workspace-tab';
      tab.id = `provider-tab-${id}`;
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-controls', `provider-panel-${id}`);
      tab.textContent = this.text(key);
      const panel = document.createElement('div');
      panel.className = 'workspace-tab-panel';
      panel.id = `provider-panel-${id}`;
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', tab.id);
      tab.addEventListener('click', () => this.showProviderTab(id, tabs, panels));
      tab.addEventListener('keydown', (event) => {
        const next = typeof ProviderStatusLogic === 'undefined'
          ? id
          : ProviderStatusLogic.nextTab(id, event.key);
        if (next !== id) {
          event.preventDefault();
          this.showProviderTab(next, tabs, panels);
          tabs[next].focus();
        }
      });
      nav.appendChild(tab);
      tabs[id] = tab;
      panels[id] = panel;
    });
    card.appendChild(nav);
    items.forEach(([id]) => card.appendChild(panels[id]));
    this.showProviderTab('profile', tabs, panels);
    return panels;
  },

  showProviderTab(id, tabs, panels) {
    Object.keys(tabs).forEach((key) => {
      const selected = key === id;
      tabs[key].setAttribute('aria-selected', selected ? 'true' : 'false');
      tabs[key].tabIndex = selected ? 0 : -1;
      tabs[key].classList.toggle('is-active', selected);
      panels[key].hidden = !selected;
    });
  },

  mountIncoming(card) {
    const heading = document.createElement('h3');
    heading.textContent = this.text('direct.incomingTitle');
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('direct.incomingNote');
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    status.textContent = this.text('direct.incomingLoading');
    const list = document.createElement('div');
    card.append(heading, note, status, list);
    this.loadIncoming(status, list);
  },

  async collect(path) {
    const rows = [];
    let endpoint = path;
    while (endpoint) {
      const page = await ApiClient.get(endpoint);
      if (Array.isArray(page)) return page;
      rows.push(...ServiceRequestAccountLogic.rowsFrom(page));
      if (!page || !page.next || !String(page.next).startsWith(CONFIG.API_BASE_URL)) break;
      endpoint = String(page.next).slice(CONFIG.API_BASE_URL.length);
    }
    return rows;
  },

  async loadCustomer(status, list) {
    try {
      const rows = (await this.collect(ServiceRequestAccountLogic.CUSTOMER_PATH))
        .map((row) => ServiceRequestAccountLogic.customerView(row));
      list.replaceChildren();
      status.textContent = rows.length
        ? this.text('direct.count', { count: rows.length })
        : this.text('direct.sentEmpty');
      rows.forEach((row) => list.appendChild(this.customerRow(row)));
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      status.textContent = ServiceRequestAccountLogic.errorText(error);
    }
  },

  customerRow(row) {
    const article = document.createElement('article');
    const copy = document.createElement('p');
    const when = row.created_at ? ` Submitted: ${row.created_at}.` : '';
    copy.textContent = `${row.provider_name}. ${row.description} Status: ${row.status}.${when}`;
    article.appendChild(copy);
    return article;
  },

  async loadIncoming(status, list) {
    try {
      const rows = (await this.collect(ServiceRequestAccountLogic.INCOMING_PATH))
        .map((row) => ServiceRequestAccountLogic.providerView(row));
      list.replaceChildren();
      status.textContent = rows.length
        ? this.text('direct.count', { count: rows.length })
        : this.text('direct.incomingEmpty');
      rows.forEach((row) => list.appendChild(this.providerRow(row)));
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      status.textContent = ServiceRequestAccountLogic.errorText(error);
    }
  },

  providerRow(row) {
    const article = document.createElement('article');
    const copy = document.createElement('p');
    const when = row.created_at ? ` Submitted: ${row.created_at}.` : '';
    const phone = row.contact_phone ? ` Contact number: ${row.contact_phone}.` : '';
    copy.textContent = `${row.description} Status: ${row.status}.${when}${phone}`;
    const actions = document.createElement('p');
    article.append(copy, actions);
    ServiceRequestAccountLogic.actions(row.status).forEach((next) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-outline btn-sm action-gap';
      button.textContent = next === 'accepted'
        ? this.text('daily.accept')
        : next === 'declined'
          ? this.text('daily.decline')
          : this.text('direct.close');
      button.addEventListener('click', () => this.decide(row, next, button, actions, copy));
      actions.appendChild(button);
    });
    return article;
  },

  async decide(row, nextStatus, button, actions, copy) {
    const gate = ServiceRequestAccountLogic.decisionGate(this.busy, row.status, nextStatus);
    if (!gate.ok) return;
    this.busy = true;
    button.disabled = true;
    const notice = document.createElement('span');
    notice.textContent = ` ${this.text('form.saving')}`;
    actions.appendChild(notice);
    try {
      const data = await ApiClient.patch(
        ServiceRequestAccountLogic.decisionPath(row.id),
        gate.payload,
      );
      row.status = data && data.status ? String(data.status) : row.status;
      copy.textContent = `${row.description} Status: ${row.status}.`;
      actions.textContent = row.status === nextStatus
        ? this.text('direct.marked', { status: row.status })
        : this.text('direct.notConfirmed');
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      notice.textContent = ` ${ServiceRequestAccountLogic.errorText(error)}`;
      button.disabled = false;
    } finally {
      this.busy = false;
    }
  },

  mountProfileArea(card, user) {
    const heading = document.createElement('h3');
    heading.textContent = this.text('direct.profileTitle');
    const view = document.createElement('div');
    view.className = 'profile-view';
    view.id = 'provider-profile-view';
    this.profileView = view;
    if (typeof ProviderStatus !== 'undefined') {
      this.photoState = ProviderStatus.mountPhoto(card, {});
    }
    card.append(heading, view);
    this.mountProfile(card, user);
    this.fillProfileView(null, user);
  },

  fillProfileView(data, user) {
    const view = this.profileView;
    if (!view) return;
    view.replaceChildren();
    const name = document.createElement('h4');
    name.textContent = (data && data.display_name)
      || (user && user.full_name)
      || this.text('account.yourAccount');
    view.appendChild(name);
    if (!data) {
      const missing = document.createElement('p');
      missing.className = 'text-muted';
      missing.textContent = this.text('direct.profileMissing');
      view.appendChild(missing);
      return;
    }
    const bio = document.createElement('p');
    bio.textContent = data.bio || this.text('profile.noBio');
    const skills = document.createElement('p');
    skills.textContent = Array.isArray(data.skills) && data.skills.length
      ? `${this.text('profile.skills')}: ${data.skills.join(', ')}`
      : this.text('profile.noSkills');
    const categories = document.createElement('p');
    const slugs = Array.isArray(data.service_categories) ? data.service_categories : [];
    const categoryNames = slugs.map((slug) => (
      typeof I18n === 'undefined' ? slug : I18n.categoryLabel(slug, slug)
    ));
    categories.textContent = categoryNames.length
      ? `${this.text('profile.categories')}: ${categoryNames.join(', ')}`
      : this.text('profile.noCategories');
    const experience = document.createElement('p');
    experience.textContent = this.text('profile.experience', {
      years: data.experience_years == null ? '' : data.experience_years,
    });
    const place = document.createElement('p');
    const location = typeof LocationFields === 'undefined'
      ? [data.locality, data.district].filter(Boolean).join(', ')
      : LocationFields.placeLabel(data.locality, data.taluk, data.district);
    place.textContent = location
      ? `${location}. ${this.text('profile.area', { km: data.service_radius_km == null ? '' : data.service_radius_km })}`
      : this.text('directory.locationMissing');
    const publication = document.createElement('p');
    publication.textContent = this.text('direct.publicationState', {
      status: data.publication_status || '',
    });
    view.append(bio, categories, skills, experience, place, publication);
    if (user && user.service_provider) {
      const verification = document.createElement('p');
      verification.textContent = this.text('account.verification', {
        status: String(user.service_provider.verification_status || '').replaceAll('_', ' '),
      });
      view.appendChild(verification);
    }
  },

  mountProfile(card, user) {
    const editor = document.createElement('details');
    editor.className = 'account-details profile-editor';
    this.profileEditor = editor;
    const summary = document.createElement('summary');
    summary.textContent = this.text('workspace.editProfile');
    const note = document.createElement('p');
    note.className = 'text-muted';
    note.textContent = this.text('direct.profileNote');
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    status.textContent = this.text('direct.profileLoading');
    const form = document.createElement('form');
    const fields = {
      skills: this.input('text'),
      bio: this.input('textarea'),
      serviceRate: this.input('text'),
      pricingBasis: this.select([['hourly', this.text('list.hourly')], ['daily', this.text('list.daily')]]),
      district: this.select([['', this.text('form.choose')]]),
      taluk: this.select([['', this.text('form.choose')]]),
      locality: this.input('text'),
      experienceYears: this.input('text'),
      serviceRadiusKm: this.input('text'),
      latitude: this.input('hidden'),
      longitude: this.input('hidden'),
      availability: this.input('hidden'),
      publicationStatus: this.select([['draft', this.text('direct.draft')], ['published', this.text('direct.published')]]),
    };
    const locate = document.createElement('button');
    locate.type = 'button';
    locate.className = 'btn btn-outline';
    locate.textContent = this.text('direct.locate');
    locate.addEventListener('click', () => this.useLocation(fields, status));
    form.append(
      this.labeled(this.text('direct.skills'), fields.skills),
      this.labeled(this.text('direct.bio'), fields.bio),
      this.labeled(this.text('direct.listedRate'), fields.serviceRate),
      this.labeled(this.text('direct.priceBasis'), fields.pricingBasis),
      this.labeled(this.text('form.district'), fields.district),
      this.labeled(this.text('form.taluk'), fields.taluk),
      this.labeled(this.text('form.locality'), fields.locality),
      this.labeled(this.text('direct.experience'), fields.experienceYears),
      this.labeled(this.text('direct.travelRadius'), fields.serviceRadiusKm),
      fields.latitude,
      fields.longitude,
      locate,
      fields.availability,
      this.labeled(this.text('direct.publication'), fields.publicationStatus),
    );
    const save = document.createElement('button');
    save.type = 'submit';
    save.className = 'btn btn-primary';
    save.textContent = this.text('direct.saveProfile');
    const categories = document.createElement('fieldset');
    categories.className = 'form-group';
    const categoryLegend = document.createElement('legend');
    categoryLegend.className = 'form-label';
    categoryLegend.textContent = this.text('direct.categories');
    const categoryList = document.createElement('div');
    categories.append(categoryLegend, categoryList);
    form.append(categories, save);
    this.categoryList = categoryList;
    this.categoriesReady = false;
    form.addEventListener('submit', (event) => this.saveProfile(event, fields, status, save));
    editor.append(summary, note, status, form);
    card.appendChild(editor);
    const verification = user && user.service_provider ? user.service_provider.verification_status : '';
    if (ServiceRequestAccountLogic.canSubmitVerification(verification)) {
      const review = document.createElement('button');
      review.type = 'button';
      review.className = 'btn btn-outline';
      review.textContent = this.text('direct.submitReview');
      review.addEventListener('click', () => this.submitVerification(status, review));
      card.appendChild(review);
    }
    this.profileFields = fields;
    this.savedCategories = [];
    this.loadCategories(status);
    this.loadProfile(fields, status);
    if (typeof LocationFields !== 'undefined') {
      LocationFields.enhance({
        district: fields.district,
        taluk: fields.taluk,
        locality: fields.locality,
      });
    }
  },

  input(kind) {
    const element = document.createElement(kind === 'textarea' ? 'textarea' : 'input');
    if (kind === 'hidden') {
      element.type = 'hidden';
      return element;
    }
    element.className = kind === 'textarea' ? 'form-textarea' : 'form-input';
    if (kind === 'textarea') element.rows = 3;
    return element;
  },

  async useLocation(fields, status) {
    if (typeof LocationDetect !== 'undefined') {
      await LocationDetect.detect({
        fields: {
          district: fields.district,
          taluk: fields.taluk,
          locality: fields.locality,
          latitude: fields.latitude,
          longitude: fields.longitude,
        },
        status,
      });
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
      status.textContent = this.text('direct.located');
    } catch (error) {
      status.textContent = this.text('daily.locationFailed');
    }
  },

  select(options) {
    const element = document.createElement('select');
    element.className = 'form-input';
    options.forEach(([value, label]) => {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = label;
      element.appendChild(option);
    });
    return element;
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

  async loadCategories(status) {
    try {
      const rows = [];
      let endpoint = ServiceRequestAccountLogic.CATEGORY_PATH;
      while (endpoint) {
        const page = await ApiClient.get(endpoint);
        rows.push(...ServiceRequestAccountLogic.rowsFrom(page));
        if (!page || !page.next || !String(page.next).startsWith(CONFIG.API_BASE_URL)) break;
        endpoint = String(page.next).slice(CONFIG.API_BASE_URL.length);
      }
      this.categoryList.replaceChildren();
      rows.forEach((category) => {
        if (!category || !category.slug) return;
        const label = document.createElement('label');
        label.className = 'choice-row';
        const box = document.createElement('input');
        box.type = 'checkbox';
        box.value = category.slug;
        const name = typeof I18n === 'undefined'
          ? (category.name || category.slug)
          : I18n.categoryLabel(category.slug, category.name || category.slug);
        label.append(box, document.createTextNode(` ${name}`));
        this.categoryList.appendChild(label);
      });
      this.categoriesReady = true;
      this.applyCategoryChecks();
    } catch (error) {
      this.categoriesReady = false;
      if (status && !status.textContent) status.textContent = ServiceRequestAccountLogic.errorText(error);
    }
  },

  checkedCategories() {
    if (!this.categoryList) return [];
    return Array.from(this.categoryList.querySelectorAll('input[type="checkbox"]:checked')).map((box) => box.value);
  },

  applyCategoryChecks() {
    if (!this.categoryList) return;
    const selected = new Set((this.savedCategories || []).map((slug) => String(slug).toLowerCase()));
    this.categoryList.querySelectorAll('input[type="checkbox"]').forEach((box) => {
      box.checked = selected.has(String(box.value).toLowerCase());
    });
  },

  async loadProfile(fields, status) {
    try {
      const data = await ApiClient.get(ServiceRequestAccountLogic.PROFILE_PATH);
      this.hasProfile = true;
      this.savedCategories = Array.isArray(data.service_categories) ? data.service_categories : [];
      this.fillProfile(fields, data);
      this.applyCategoryChecks();
      this.fillProfileView(data, null);
      if (this.profileEditor) this.profileEditor.open = false;
      status.textContent = this.text('direct.profileSaved');
    } catch (error) {
      if (error && error.status === 404) {
        this.hasProfile = false;
        status.textContent = this.text('direct.profileMissing');
        if (this.profileEditor) this.profileEditor.open = true;
        return;
      }
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      status.textContent = ServiceRequestAccountLogic.errorText(error);
    }
  },

  fillProfile(fields, data) {
    if (!data) return;
    fields.skills.value = Array.isArray(data.skills) ? data.skills.join(', ') : '';
    fields.bio.value = data.bio || '';
    fields.serviceRate.value = data.service_rate || '';
    fields.pricingBasis.value = data.pricing_basis || 'hourly';
    fields.district.value = data.district || '';
    if (fields.taluk) fields.taluk.value = data.taluk || '';
    fields.locality.value = data.locality || '';
    if (typeof LocationFields !== 'undefined') {
      LocationFields.enhance({
        district: fields.district,
        taluk: fields.taluk,
        locality: fields.locality,
        selectedDistrict: data.district || '',
        selectedTaluk: data.taluk || '',
      });
    }
    fields.experienceYears.value = data.experience_years == null ? '' : String(data.experience_years);
    fields.serviceRadiusKm.value = data.service_radius_km == null ? '' : String(data.service_radius_km);
    fields.latitude.value = data.latitude == null ? '' : String(data.latitude);
    fields.longitude.value = data.longitude == null ? '' : String(data.longitude);
    fields.availability.value = data.availability || 'available';
    fields.publicationStatus.value = data.publication_status || 'draft';
  },

  readProfile(fields) {
    return {
      skills: fields.skills.value,
      bio: fields.bio.value,
      serviceRate: fields.serviceRate.value,
      pricingBasis: fields.pricingBasis.value,
      district: fields.district.value,
      taluk: fields.taluk ? fields.taluk.value : '',
      locality: fields.locality.value,
      experienceYears: fields.experienceYears.value,
      serviceRadiusKm: fields.serviceRadiusKm.value,
      latitude: fields.latitude.value,
      longitude: fields.longitude.value,
      availability: fields.availability.value,
      publicationStatus: fields.publicationStatus.value,
      categorySlugs: this.categoriesReady ? this.checkedCategories() : undefined,
    };
  },

  async saveProfile(event, fields, status, button) {
    event.preventDefault();
    if (this.busy) return;
    const built = ServiceRequestAccountLogic.profilePayload(this.readProfile(fields));
    if (built.error) {
      status.textContent = built.error;
      return;
    }
    this.busy = true;
    button.disabled = true;
    status.textContent = this.text('direct.savingProfile');
    try {
      const data = this.hasProfile
        ? await ApiClient.patch(ServiceRequestAccountLogic.PROFILE_PATH, built.payload)
        : await ApiClient.post(ServiceRequestAccountLogic.PROFILE_PATH, built.payload);
      this.hasProfile = true;
      this.savedCategories = Array.isArray(data.service_categories) ? data.service_categories : [];
      this.fillProfile(fields, data);
      this.applyCategoryChecks();
      this.fillProfileView(data, null);
      if (this.photoState && typeof ProviderStatus !== 'undefined') {
        ProviderStatus.applyPhoto(this.photoState, data && data.photo_url, true);
      }
      if (this.availabilityState && typeof ProviderStatus !== 'undefined') {
        this.availabilityState.hasProfile = true;
        ProviderStatus.setAvailabilityUi(
          this.availabilityState,
          data && data.availability === 'unavailable' ? 'unavailable' : 'available',
          true,
        );
      }
      if (this.profileEditor) this.profileEditor.open = false;
      status.textContent = data && data.publication_status === 'published'
        ? this.text('direct.profilePublished')
        : this.text('direct.profileDraft');
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      status.textContent = ServiceRequestAccountLogic.errorText(error);
    } finally {
      this.busy = false;
      button.disabled = false;
    }
  },

  async submitVerification(status, button) {
    if (this.busy) return;
    this.busy = true;
    button.disabled = true;
    status.textContent = this.text('direct.submitting');
    try {
      const data = await ApiClient.post(ServiceRequestAccountLogic.VERIFICATION_PATH, { applicant_note: '' });
      status.textContent = data && data.status === 'pending'
        ? this.text('direct.pending')
        : this.text('direct.submitFailed');
      if (data && data.status === 'pending') button.remove();
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      status.textContent = ServiceRequestAccountLogic.errorText(error);
      button.disabled = false;
    } finally {
      this.busy = false;
    }
  },
};
