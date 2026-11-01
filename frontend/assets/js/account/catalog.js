/**
 * Account areas shown after the server confirms a capability.
 * The page address is not permission. AccountSession checks /auth/me/ first.
 */

const AccountCatalog = {
  groups: [
    {
      id: 'services',
      titleKey: 'nav.daily',
      title: 'Daily services',
      items: [
        {
          code: 'customer',
          labelKey: 'role.customer',
          summaryKey: 'role.customerSummary',
          label: 'Customer',
          page: 'services/customer.html',
          summary: 'Request a daily service by category and read its status. A worker is assigned only after one accepts.'
        },
        {
          code: 'service_provider',
          labelKey: 'role.provider',
          summaryKey: 'role.providerSummary',
          label: 'Service provider',
          page: 'services/provider.html',
          summary: 'Manage your professional profile, verification, and service requests.'
        }
      ]
    },
    {
      id: 'jobs',
      titleKey: 'nav.jobs',
      title: 'Jobs',
      items: [
        {
          code: 'job_seeker',
          labelKey: 'role.seeker',
          summaryKey: 'role.seekerSummary',
          label: 'Job seeker',
          page: 'jobs/seeker.html',
          summary: 'Search jobs, apply, and track applications.'
        },
        {
          code: 'employer',
          labelKey: 'role.employer',
          summaryKey: 'role.employerSummary',
          label: 'Employer',
          page: 'jobs/employer.html',
          summary: 'Publish jobs and accept or reject submitted applications.'
        }
      ]
    },
    {
      id: 'equipment',
      titleKey: 'nav.equipment',
      title: 'Equipment',
      items: [
        {
          code: 'equipment_owner',
          labelKey: 'role.eqOwner',
          summaryKey: 'role.eqOwnerSummary',
          label: 'Equipment owner',
          page: 'equipment/rental.html',
          summary: 'List machinery, set a rental price, and handle rental requests.'
        },
        {
          code: 'equipment_renter',
          labelKey: 'role.eqRenter',
          summaryKey: 'role.eqRenterSummary',
          label: 'Equipment renter',
          page: 'equipment/rental.html',
          summary: 'Browse equipment and request rentals.'
        }
      ]
    },
    {
      id: 'farm',
      titleKey: 'nav.farm',
      title: 'Farm hiring',
      items: [
        {
          code: 'agricultural_worker',
          labelKey: 'role.agWorker',
          summaryKey: 'role.agWorkerSummary',
          label: 'Agricultural worker',
          page: 'agriculture/hiring.html',
          summary: 'Find farm work and respond to hiring requests.'
        },
        {
          code: 'agricultural_employer',
          labelKey: 'role.agEmployer',
          summaryKey: 'role.agEmployerSummary',
          label: 'Agricultural job poster',
          page: 'agriculture/hiring.html',
          summary: 'Hire farm labour and manage agricultural jobs.'
        }
      ]
    }
  ],

  text(key, fallback) {
    if (typeof I18n === 'undefined') return fallback || key;
    return I18n.t(key);
  },

  workspaceHref(item) {
    if (typeof AccountWorkspace !== 'undefined') return AccountWorkspace.href(item);
    if (!item || !item.page || !item.code) return '../dashboard/dashboard.html';
    return `../${item.page}?workspace=${encodeURIComponent(item.code)}`;
  },

  itemLabel(item) {
    return this.text(item.labelKey, item.label);
  },

  itemSummary(item) {
    return this.text(item.summaryKey, item.summary);
  },

  groupTitle(group) {
    return this.text(group.titleKey, group.title);
  },

  allItems() {
    const items = [];
    this.groups.forEach((group) => {
      group.items.forEach((item) => {
        items.push({ ...item, groupTitle: this.groupTitle(group) });
      });
    });
    return items;
  },

  itemsForPage(page) {
    return this.allItems().filter((item) => item.page === page);
  },

  label(code) {
    const item = this.allItems().find((entry) => entry.code === code);
    return item ? this.itemLabel(item) : code;
  }
};
