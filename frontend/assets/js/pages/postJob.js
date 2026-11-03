/**
 * Submits the ordinary job form and the equipment listing form.
 * Success text comes from the API response, not from the button click.
 */

const PostFormController = {
  busy: false,

  text(key) {
    return typeof I18n === 'undefined' ? key : I18n.t(key);
  },

  init() {
    this.bindTabs();
    this.bindForms();
    this.bindSignIn();
    this.bindPlaces();
    if (window.location.hash === '#equipment') {
      const tab = document.getElementById('tab-list-equip');
      if (tab) tab.click();
    }
  },

  bindTabs() {
    const tabJob = document.getElementById('tab-post-job');
    const tabEquip = document.getElementById('tab-list-equip');
    const formJob = document.getElementById('form-post-job');
    const formEquip = document.getElementById('form-list-equip');
    if (!tabJob || !tabEquip) return;
    tabJob.addEventListener('click', () => {
      tabJob.classList.add('btn-primary');
      tabJob.classList.remove('btn-outline');
      tabEquip.classList.add('btn-outline');
      tabEquip.classList.remove('btn-primary');
      if (formJob) formJob.style.display = 'block';
      if (formEquip) formEquip.style.display = 'none';
    });
    tabEquip.addEventListener('click', () => {
      tabEquip.classList.add('btn-primary');
      tabEquip.classList.remove('btn-outline');
      tabJob.classList.add('btn-outline');
      tabJob.classList.remove('btn-primary');
      if (formJob) formJob.style.display = 'none';
      if (formEquip) formEquip.style.display = 'block';
    });
  },

  bindPlaces() {
    if (typeof LocationFields !== 'undefined') {
      LocationFields.enhanceByIds({ state: 'job-state', district: 'job-district', taluk: 'job-taluk', locality: 'job-locality' });
      LocationFields.enhanceByIds({ state: 'equip-state', district: 'equip-district', taluk: 'equip-taluk', locality: 'equip-locality' });
    }
    if (typeof LocationDetect === 'undefined') return;
    LocationDetect.bind({
      button: document.getElementById('job-locate'),
      status: document.getElementById('job-location-state'),
      fields: {
        state: document.getElementById('job-state'),
        district: document.getElementById('job-district'),
        taluk: document.getElementById('job-taluk'),
        locality: document.getElementById('job-locality'),
      },
    });
    LocationDetect.bind({
      button: document.getElementById('equip-locate'),
      status: document.getElementById('equip-location-state'),
      fields: {
        state: document.getElementById('equip-state'),
        district: document.getElementById('equip-district'),
        taluk: document.getElementById('equip-taluk'),
        locality: document.getElementById('equip-locality'),
      },
    });
  },

  bindForms() {
    const jobForm = document.getElementById('job-create-form');
    const equipmentForm = document.getElementById('equipment-create-form');
    if (jobForm) jobForm.addEventListener('submit', (event) => this.submitJob(event));
    if (equipmentForm) equipmentForm.addEventListener('submit', (event) => this.submitEquipment(event));
  },

  bindSignIn() {
    document.querySelectorAll('a[href="../auth/login.html"]').forEach((link) => {
      link.addEventListener('click', () => {
        if (typeof AccountSession !== 'undefined') AccountSession.rememberReturnPath();
      });
    });
  },

  requireSignIn(notice) {
    if (this.signedIn()) return true;
    if (typeof AccountSession !== 'undefined') AccountSession.rememberReturnPath();
    this.show(notice, this.text('form.needSignIn'));
    return false;
  },

  signedIn() {
    const token = StorageUtil.get(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    return typeof token === 'string' && token.trim() && token !== 'demo_token_authenticated';
  },

  show(notice, text) {
    if (notice) notice.textContent = text;
  },

  async submitJob(event) {
    event.preventDefault();
    const notice = document.getElementById('job-notice');
    const button = document.getElementById('job-submit');
    if (this.busy) return;
    const values = {
      title: document.getElementById('job-title').value,
      description: document.getElementById('job-description').value,
      district: document.getElementById('job-district').value,
      taluk: document.getElementById('job-taluk') ? document.getElementById('job-taluk').value : '',
      locality: document.getElementById('job-locality').value,
      workType: document.getElementById('job-work-type').value,
      wageAmount: document.getElementById('job-wage-amount').value,
      wageNegotiable: document.getElementById('job-wage-negotiable').checked,
      wagePeriod: document.getElementById('job-wage-period').value,
      headcount: document.getElementById('job-headcount').value,
    };
    const problems = PostFormLogic.jobProblems(values);
    if (problems.length) {
      this.show(notice, problems.join(' '));
      return;
    }
    if (!this.requireSignIn(notice)) return;
    this.busy = true;
    button.disabled = true;
    this.show(notice, this.text('form.saving'));
    try {
      const saved = await ApiClient.post(PostFormLogic.JOB_PATH, PostFormLogic.jobPayload(values));
      const result = PostFormLogic.jobResult(saved);
      this.show(notice, result.text);
    } catch (error) {
      if (error && error.status === 401) {
        if (typeof AccountSession !== 'undefined') AccountSession.rememberReturnPath();
        window.location.href = '../auth/login.html';
        return;
      }
      this.show(notice, PostFormLogic.errorText(error));
    } finally {
      this.busy = false;
      button.disabled = false;
    }
  },

  async submitEquipment(event) {
    event.preventDefault();
    const notice = document.getElementById('equipment-notice');
    const button = document.getElementById('equipment-submit');
    if (this.busy) return;
    const values = {
      title: document.getElementById('equip-title').value,
      description: document.getElementById('equip-description').value,
      district: document.getElementById('equip-district').value,
      taluk: document.getElementById('equip-taluk') ? document.getElementById('equip-taluk').value : '',
      locality: document.getElementById('equip-locality').value,
      pricingBasis: document.getElementById('equip-pricing-basis').value,
      rate: document.getElementById('equip-rate').value,
      operatorIncluded: document.getElementById('equip-operator').checked,
      availabilityNote: document.getElementById('equip-availability').value,
    };
    const problems = PostFormLogic.equipmentProblems(values);
    if (problems.length) {
      this.show(notice, problems.join(' '));
      return;
    }
    if (!this.requireSignIn(notice)) return;
    this.busy = true;
    button.disabled = true;
    this.show(notice, this.text('form.saving'));
    try {
      const saved = await ApiClient.post(
        PostFormLogic.EQUIPMENT_PATH,
        PostFormLogic.equipmentPayload(values),
      );
      const photoInput = document.getElementById('equip-photo');
      const file = photoInput && photoInput.files && photoInput.files[0];
      if (file && saved && saved.id) {
        const body = new FormData();
        body.append('photo', file, file.name);
        await ApiClient.postForm(`/equipment/${saved.id}/photo/`, body);
        if (photoInput) photoInput.value = '';
      }
      const result = PostFormLogic.equipmentResult(saved);
      this.show(notice, result.text);
    } catch (error) {
      if (error && error.status === 401) {
        if (typeof AccountSession !== 'undefined') AccountSession.rememberReturnPath();
        window.location.href = '../auth/login.html';
        return;
      }
      this.show(notice, PostFormLogic.errorText(error));
    } finally {
      this.busy = false;
      button.disabled = false;
    }
  },
};

document.addEventListener('DOMContentLoaded', () => PostFormController.init());
