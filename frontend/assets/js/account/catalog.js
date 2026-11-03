/**
 * Account destinations and professional roles.
 * Customer is not a professional role. Marketplace links are for every signed-in user.
 * Role workspaces still require the matching capability from /auth/me/.
 */

const AccountCatalog = {
  /**
   * Marketplace destinations open to every signed-in account.
   * Daily Services goes to the authenticated request/track page (no Customer role).
   */
  marketplaces: [
    {
      id: 'daily',
      labelKey: 'hub.needDaily',
      label: 'Helper today',
      href: '../services/customer.html',
      summaryKey: 'hub.marketDaily',
      summary: 'Plumber, electrician, and other daily work.',
    },
    {
      id: 'jobs',
      labelKey: 'hub.needJobs',
      label: 'Jobs',
      href: '../jobs/jobs-list.html',
      summaryKey: 'hub.marketJobs',
      summary: 'See jobs near your place.',
    },
    {
      id: 'equipment',
      labelKey: 'hub.needEquipment',
      label: 'Machines',
      href: '../equipment/equipment-list.html',
      summaryKey: 'hub.marketEquipment',
      summary: 'Tractor and other machines.',
    },
    {
      id: 'farm',
      labelKey: 'hub.needFarm',
      label: 'Farm work',
      href: '../jobs/farm-jobs.html',
      summaryKey: 'hub.marketFarm',
      summary: 'Farm hiring near you.',
    },
  ],

  /** Kept for AreaPage: signed-in Daily Services request/track page. */
  activities: [
    {
      id: 'service_requests',
      labelKey: 'activity.serviceRequests',
      summaryKey: 'activity.serviceRequestsSummary',
      label: 'My service requests',
      page: 'services/customer.html',
      summary: 'Request a daily service and read its status. A worker is assigned only after one accepts.',
    },
  ],

  groups: [
    {
      id: 'services',
      titleKey: 'nav.daily',
      title: 'Daily services',
      items: [
        {
          code: 'service_provider',
          labelKey: 'role.provider',
          summaryKey: 'role.providerSummary',
          label: 'Daily service provider',
          page: 'services/provider.html',
          summary: 'Daily services. Manage profile, verification, and work offers.',
        },
      ],
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
          summary: 'Search jobs, apply, and track applications.',
        },
        {
          code: 'employer',
          labelKey: 'role.employer',
          summaryKey: 'role.employerSummary',
          label: 'Employer',
          page: 'jobs/employer.html',
          summary: 'Publish jobs and accept or reject submitted applications.',
        },
      ],
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
          summary: 'List machinery, set a rental price, and handle rental requests.',
        },
        {
          code: 'equipment_renter',
          labelKey: 'role.eqRenter',
          summaryKey: 'role.eqRenterSummary',
          label: 'Equipment renter',
          page: 'equipment/rental.html',
          summary: 'Browse equipment and request rentals.',
        },
      ],
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
          summary: 'Find farm work and respond to hiring requests.',
        },
        {
          code: 'agricultural_employer',
          labelKey: 'role.agEmployer',
          summaryKey: 'role.agEmployerSummary',
          label: 'Agricultural job poster',
          page: 'agriculture/hiring.html',
          summary: 'Hire farm labour and manage agricultural jobs.',
        },
      ],
    },
  ],

  text(key, fallback) {
    if (typeof I18n === 'undefined') return fallback || key;
    const value = I18n.t(key);
    return value === key && fallback ? fallback : value;
  },

  activityForPage(page) {
    return (this.activities || []).find((item) => item.page === page) || null;
  },

  activityHref(item) {
    if (!item || !item.page) return '../dashboard/dashboard.html';
    return `../${item.page}`;
  },

  marketplaceHref(item) {
    return item && item.href ? item.href : '../dashboard/dashboard.html';
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
  },
};
