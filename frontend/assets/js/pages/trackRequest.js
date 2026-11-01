/**
 * Guest request tracking. The private key is typed here and is not read from the URL.
 */

const TrackRequestPage = {
  busy: false,

  init() {
    this.bind();
    this.showSignedInLink();
    this.prefillReference();
  },

  bind() {
    document.getElementById('guest-status-form').addEventListener('submit', (event) => this.checkStatus(event));
  },

  text(key) {
    return typeof I18n === 'undefined' ? key : I18n.t(key);
  },

  show(id, text, kind) {
    const notice = document.getElementById(id);
    if (!notice) return;
    notice.textContent = text || '';
    notice.classList.remove('is-error', 'is-success', 'is-info');
    if (text && kind) notice.classList.add(`is-${kind}`);
  },

  showSignedInLink() {
    const link = document.getElementById('track-my-requests');
    if (!link || typeof StorageUtil === 'undefined' || typeof CONFIG === 'undefined') return;
    const token = StorageUtil.get(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    const signedIn = typeof token === 'string' && token.trim() !== '' && token !== 'demo_token_authenticated';
    link.hidden = !signedIn;
  },

  prefillReference() {
    const query = new URLSearchParams(window.location.search);
    const parsed = GuestServiceLogic.ignoreTrackingKeyInQuery(query);
    if (parsed.reference) {
      document.getElementById('status-reference').value = parsed.reference;
    }
    document.getElementById('status-access-key').value = '';
  },

  setBusy(busy) {
    this.busy = busy;
    const button = document.getElementById('status-submit');
    if (button) button.disabled = busy;
  },

  async checkStatus(event) {
    event.preventDefault();
    if (this.busy) return;
    const reference = document.getElementById('status-reference').value;
    const accessKey = document.getElementById('status-access-key').value;
    const problems = GuestServiceLogic.statusProblems(reference, accessKey);
    if (problems.length) {
      this.clearResult();
      this.show('status-notice', problems.join(' '), 'error');
      return;
    }
    this.setBusy(true);
    this.show('status-notice', this.text('guest.checking'), 'info');
    try {
      const status = await ApiClient.post(
        GuestServiceLogic.STATUS_PATH,
        GuestServiceLogic.statusPayload(reference, accessKey),
      );
      const view = GuestServiceLogic.statusView(status);
      this.show('status-notice', view.ok ? '' : view.text, view.ok ? '' : 'error');
      this.renderStatus(view);
    } catch (error) {
      this.clearResult();
      this.show('status-notice', GuestServiceLogic.errorText(error), 'error');
    } finally {
      this.setBusy(false);
    }
  },

  clearResult() {
    const root = document.getElementById('status-result');
    if (!root) return;
    root.replaceChildren();
    root.hidden = true;
  },

  addRow(list, label, value) {
    const dt = document.createElement('dt');
    dt.textContent = label;
    const dd = document.createElement('dd');
    dd.textContent = value;
    list.append(dt, dd);
  },

  renderStatus(view) {
    const root = document.getElementById('status-result');
    if (!root) return;
    root.replaceChildren();
    if (!view.ok) {
      root.hidden = true;
      return;
    }
    const heading = document.createElement('h3');
    heading.textContent = this.text('track.resultHeading');
    const list = document.createElement('dl');
    const workerName = view.assignedProfile && view.assignedProfile.display_name;
    const statusText = typeof I18n === 'undefined'
      ? view.text
      : I18n.statusText(view.status, workerName);
    this.addRow(list, this.text('track.needNumberTitle'), String(view.reference));
    this.addRow(list, this.text('guest.statusLabel'), statusText);
    const accepted = view.status === 'assigned' || view.status === 'in_progress' || view.status === 'completed';
    if (accepted && view.assignedProfile) {
      const place = [view.assignedProfile.locality, view.assignedProfile.district].filter(Boolean).join(', ');
      const skills = view.assignedProfile.skills.join(', ');
      const worker = [view.assignedProfile.display_name, skills, place].filter(Boolean).join(' · ');
      if (worker) this.addRow(list, this.text('track.providerLabel'), worker);
    }
    root.append(heading, list);
    if (view.canExpand && view.expandToKm) {
      const expand = document.createElement('button');
      expand.type = 'button';
      expand.className = 'btn btn-outline action-gap';
      expand.textContent = typeof I18n === 'undefined'
        ? `Allow a ${view.expandToKm} km search`
        : I18n.fill('track.expand', { km: view.expandToKm });
      expand.addEventListener('click', () => this.expand(view, expand));
      root.appendChild(expand);
    }
    if (view.canCancel) {
      const cancel = document.createElement('button');
      cancel.type = 'button';
      cancel.className = 'btn btn-outline action-gap';
      cancel.textContent = this.text('track.cancel');
      cancel.addEventListener('click', () => this.cancel(view, cancel));
      root.appendChild(cancel);
    }
    root.hidden = false;
  },

  trackingKeys() {
    return {
      reference: document.getElementById('status-reference').value,
      accessKey: document.getElementById('status-access-key').value,
    };
  },

  async expand(view, button) {
    if (this.busy) return;
    this.setBusy(true);
    button.disabled = true;
    try {
      const keys = this.trackingKeys();
      const data = await ApiClient.post(
        GuestServiceLogic.EXPAND_PATH,
        GuestServiceLogic.expandPayload(keys.reference, keys.accessKey, view.expandToKm),
      );
      this.show('status-notice', data.detail || this.text('track.expanded'), 'success');
      this.renderStatus(GuestServiceLogic.statusView({
        reference: data.reference || view.reference,
        status: data.status,
        radius_km: data.radius_km || view.radiusKm,
        match_reason: data.match_reason,
        search_radius_km: data.search_radius_km,
        can_expand: false,
        assigned_profile: view.assignedProfile,
      }));
    } catch (error) {
      this.show('status-notice', GuestServiceLogic.errorText(error), 'error');
      button.disabled = false;
    } finally {
      this.setBusy(false);
    }
  },

  async cancel(view, button) {
    if (this.busy) return;
    this.setBusy(true);
    button.disabled = true;
    try {
      const keys = this.trackingKeys();
      const data = await ApiClient.post(
        GuestServiceLogic.CANCEL_PATH,
        GuestServiceLogic.cancelPayload(keys.reference, keys.accessKey),
      );
      this.show('status-notice', data.detail || this.text('track.cancelled'), 'success');
      this.renderStatus(GuestServiceLogic.statusView(Object.assign({}, view, data, {
        status: data.status || 'cancelled',
        can_expand: false,
        canCancel: false,
      })));
    } catch (error) {
      this.show('status-notice', GuestServiceLogic.errorText(error), 'error');
      button.disabled = false;
    } finally {
      this.setBusy(false);
    }
  },
};

document.addEventListener('DOMContentLoaded', () => TrackRequestPage.init());
document.addEventListener('kaamdo:language', () => TrackRequestPage.showSignedInLink());
