/**
 * Shared availability switch and profile photo controls.
 * Uses GET/PATCH /workers/profile/ and POST/DELETE /workers/profile/photo/.
 */

const ProviderStatus = {
  text(key, values) {
    if (typeof I18n === 'undefined') return key;
    return values ? I18n.fill(key, values) : I18n.t(key);
  },

  mountAvailability(container, hooks) {
    const wrap = document.createElement('section');
    wrap.className = 'availability-card';
    const heading = document.createElement('h2');
    heading.textContent = this.text('avail.title');
    const help = document.createElement('p');
    help.className = 'text-muted';
    help.textContent = this.text('avail.help');
    const presence = document.createElement('p');
    presence.className = 'text-muted';
    presence.textContent = this.text('avail.presenceNote');
    const label = document.createElement('label');
    label.className = 'availability-switch';
    const box = document.createElement('input');
    box.type = 'checkbox';
    box.setAttribute('role', 'switch');
    box.disabled = true;
    const dot = document.createElement('span');
    dot.className = 'availability-dot';
    dot.setAttribute('aria-hidden', 'true');
    const caption = document.createElement('span');
    caption.className = 'availability-text';
    caption.textContent = this.text('avail.offline');
    label.append(box, dot, caption);
    const switchLabel = document.createElement('span');
    switchLabel.className = 'visually-hidden';
    switchLabel.textContent = this.text('avail.switchLabel');
    label.insertBefore(switchLabel, box);
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    const needLink = document.createElement('a');
    needLink.className = 'btn btn-outline';
    needLink.hidden = true;
    wrap.append(heading, help, presence, label, status, needLink);
    container.appendChild(wrap);
    const state = {
      box,
      caption,
      wrap,
      status,
      needLink,
      value: '',
      hasProfile: false,
      busy: false,
      hooks: hooks || {},
    };
    box.addEventListener('change', () => {
      const next = box.checked ? 'available' : 'unavailable';
      box.checked = state.value === 'available';
      this.saveAvailability(state, next);
    });
    this.loadAvailability(state);
    return state;
  },

  setAvailabilityUi(state, value, enabled) {
    state.value = value;
    state.box.disabled = !enabled || state.busy;
    state.box.checked = value === 'available';
    state.box.setAttribute('aria-checked', value === 'available' ? 'true' : 'false');
    state.wrap.classList.toggle('is-available', value === 'available');
    state.wrap.classList.toggle('is-unavailable', value === 'unavailable');
    state.caption.textContent = value === 'available'
      ? this.text('avail.online')
      : this.text('avail.offline');
  },

  async loadAvailability(state) {
    state.status.textContent = this.text('direct.profileLoading');
    state.needLink.hidden = true;
    try {
      const data = await ApiClient.get(ProviderStatusLogic.PROFILE_PATH);
      const value = ProviderStatusLogic.availabilityValue(data) || 'available';
      state.hasProfile = true;
      this.setAvailabilityUi(state, value, true);
      state.status.textContent = '';
      if (state.hooks.onLoaded) state.hooks.onLoaded(value, true, data);
    } catch (error) {
      state.hasProfile = false;
      this.setAvailabilityUi(state, 'unavailable', false);
      if (error && error.status === 404) {
        state.status.textContent = this.text('avail.needProfileLink');
        const item = typeof AccountCatalog !== 'undefined'
          ? AccountCatalog.allItems().find((entry) => entry.code === 'service_provider')
          : null;
        state.needLink.hidden = false;
        state.needLink.href = item && typeof AccountCatalog !== 'undefined'
          ? AccountCatalog.workspaceHref(item)
          : '../services/provider.html?workspace=service_provider';
        state.needLink.textContent = this.text('avail.needProfileLink');
      } else if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      } else {
        state.status.textContent = this.errorText(error);
      }
      if (state.hooks.onLoaded) state.hooks.onLoaded('', false, null);
    }
  },

  async saveAvailability(state, next) {
    if (state.busy || !state.hasProfile) return;
    const previous = state.value === 'unavailable' ? 'unavailable' : 'available';
    const packed = typeof ServiceRequestAccountLogic !== 'undefined'
      ? ServiceRequestAccountLogic.availabilityPayload(next)
      : { payload: { availability: next } };
    if (packed.error) {
      state.status.textContent = packed.error;
      return;
    }
    state.busy = true;
    this.setAvailabilityUi(state, previous, false);
    state.status.textContent = this.text('avail.saving');
    try {
      const data = await ApiClient.patch(ProviderStatusLogic.PROFILE_PATH, packed.payload);
      const result = typeof ServiceRequestAccountLogic !== 'undefined'
        ? ServiceRequestAccountLogic.availabilityResult(data, next)
        : { ok: data && data.availability === next, value: data && data.availability, text: 'Could not confirm availability.' };
      if (!result.ok) {
        this.setAvailabilityUi(state, previous, true);
        state.status.textContent = result.text;
        return;
      }
      this.setAvailabilityUi(state, result.value, true);
      state.status.textContent = this.text('avail.saved');
      if (state.hooks.onSaved) state.hooks.onSaved(result.value, data);
    } catch (error) {
      this.setAvailabilityUi(state, previous, true);
      const detail = this.errorText(error);
      state.status.textContent = detail
        ? `${this.text('avail.retry')} ${detail}`
        : this.text('avail.retry');
    } finally {
      state.busy = false;
      this.setAvailabilityUi(state, state.value, state.hasProfile);
    }
  },

  mountPhoto(container, hooks) {
    const wrap = document.createElement('div');
    wrap.className = 'photo-control';
    const figure = document.createElement('div');
    figure.className = 'photo-preview';
    const img = document.createElement('img');
    img.alt = this.text('profile.avatarAlt');
    img.src = ProviderStatusLogic.DEFAULT_AVATAR;
    figure.appendChild(img);
    const actions = document.createElement('div');
    actions.className = 'photo-actions';
    const file = document.createElement('input');
    file.type = 'file';
    file.accept = 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp';
    file.className = 'visually-hidden';
    file.disabled = true;
    file.disabled = true;
    file.id = `photo-file-${Math.random().toString(36).slice(2, 8)}`;
    const add = document.createElement('label');
    add.className = 'btn btn-outline';
    add.setAttribute('for', file.id);
    add.textContent = this.text('photo.add');
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'btn btn-outline';
    remove.textContent = this.text('photo.remove');
    remove.hidden = true;
    const hint = document.createElement('p');
    hint.className = 'text-muted';
    hint.textContent = this.text('photo.hint');
    const status = document.createElement('p');
    status.setAttribute('role', 'status');
    actions.append(add, file, remove);
    wrap.append(figure, actions, hint, status);
    container.appendChild(wrap);
    const state = {
      img,
      add,
      remove,
      file,
      status,
      photoUrl: '',
      hasProfile: false,
      busy: false,
      hooks: hooks || {},
    };
    file.addEventListener('change', () => this.uploadPhoto(state));
    remove.addEventListener('click', () => this.removePhoto(state));
    return state;
  },

  applyPhoto(state, photoUrl, hasProfile) {
    state.hasProfile = Boolean(hasProfile);
    state.photoUrl = ProviderStatusLogic.hasUploadedPhoto(photoUrl) ? photoUrl : '';
    state.img.src = ProviderStatusLogic.photoSrc(state.photoUrl);
    state.img.alt = state.photoUrl ? this.text('photo.replace') : this.text('profile.avatarAlt');
    state.add.textContent = state.photoUrl ? this.text('photo.replace') : this.text('photo.add');
    state.remove.hidden = !state.photoUrl;
    state.file.disabled = !state.hasProfile || state.busy;
    state.remove.disabled = !state.hasProfile || state.busy || !state.photoUrl;
    if (!state.hasProfile) {
      state.status.textContent = this.text('photo.missing');
    }
    if (state.hooks.onChanged) state.hooks.onChanged(state.photoUrl);
  },

  async uploadPhoto(state) {
    const file = state.file.files && state.file.files[0];
    state.file.value = '';
    if (!state.hasProfile || state.busy) return;
    const problem = ProviderStatusLogic.fileError(file);
    if (problem) {
      state.status.textContent = problem;
      return;
    }
    const body = new FormData();
    body.append('photo', file, file.name);
    state.busy = true;
    state.file.disabled = true;
    state.remove.disabled = true;
    state.status.textContent = this.text('photo.saving');
    try {
      const data = await ApiClient.postForm(ProviderStatusLogic.PHOTO_PATH, body);
      this.applyPhoto(state, data && data.photo_url, true);
      state.status.textContent = this.text('photo.saved');
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      state.status.textContent = this.errorText(error) || this.text('photo.failed');
    } finally {
      state.busy = false;
      this.applyPhoto(state, state.photoUrl, state.hasProfile);
    }
  },

  async removePhoto(state) {
    if (!state.hasProfile || state.busy || !state.photoUrl) return;
    state.busy = true;
    state.file.disabled = true;
    state.remove.disabled = true;
    state.status.textContent = this.text('photo.removing');
    try {
      const data = await ApiClient.delete(ProviderStatusLogic.PHOTO_PATH);
      this.applyPhoto(state, data && data.photo_url, true);
      state.status.textContent = this.text('photo.removed');
    } catch (error) {
      if (error && error.status === 401) {
        window.location.href = '../auth/login.html';
        return;
      }
      state.status.textContent = this.errorText(error) || this.text('photo.removeFailed');
    } finally {
      state.busy = false;
      this.applyPhoto(state, state.photoUrl, state.hasProfile);
    }
  },

  errorText(error) {
    if (typeof ServiceRequestAccountLogic !== 'undefined') {
      return ServiceRequestAccountLogic.errorText(error);
    }
    if (!error || !error.data) return '';
    if (typeof error.data.detail === 'string') return error.data.detail;
    if (error.data.photo) {
      const photo = error.data.photo;
      if (Array.isArray(photo) && photo[0]) return String(photo[0]);
    }
    return '';
  },
};
