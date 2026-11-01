/**
 * Homepage search and Daily Services categories.
 * Worker profiles are not the customer request path.
 */

const HomePage = {
  init() {
    this.bindSearch();
    this.loadCategories();
  },

  bindSearch() {
    const searchForm = document.getElementById('home-search-form');
    if (!searchForm) return;
    searchForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const query = document.getElementById('home-search-query').value.trim();
      window.location.href = HomeLogic.searchTarget(query);
    });
  },

  async loadCategories() {
    const container = document.getElementById('featured-services-grid');
    if (!container) return;
    container.textContent = typeof I18n === 'undefined' ? 'Loading services...' : I18n.t('home.loading');
    try {
      const rows = [];
      let endpoint = HomeLogic.CATEGORY_PATH;
      while (endpoint) {
        const page = await ApiClient.get(endpoint);
        rows.push(...HomeLogic.rowsFrom(page));
        endpoint = HomeLogic.nextPath(page, CONFIG.API_BASE_URL);
      }
      this.cards = HomeLogic.categoryCards(rows);
      this.renderCategories(this.cards);
    } catch (error) {
      container.textContent = typeof I18n === 'undefined' ? 'Services could not be loaded.' : I18n.t('home.failed');
    }
  },

  renderCategories(cards) {
    const container = document.getElementById('featured-services-grid');
    if (!container) return;
    container.replaceChildren();
    if (!cards.length) {
      const empty = document.createElement('p');
      empty.className = 'text-muted';
      empty.textContent = typeof I18n === 'undefined' ? 'No services are available yet.' : I18n.t('home.empty');
      container.appendChild(empty);
      return;
    }
    cards.forEach((card) => {
      const article = document.createElement('article');
      article.className = 'worker-id-card';
      const body = document.createElement('div');
      body.className = 'worker-card-body';
      const image = document.createElement('img');
      image.src = 'assets/images/services/service.svg';
      image.alt = typeof I18n === 'undefined' ? card.name : I18n.categoryLabel(card.slug, card.name);
      image.width = 160;
      image.height = 100;
      const title = document.createElement('h3');
      title.className = 'worker-name';
      title.textContent = typeof I18n === 'undefined' ? card.name : I18n.categoryLabel(card.slug, card.name);
      const copy = document.createElement('p');
      copy.className = 'text-muted';
      copy.textContent = card.description || '';
      const action = document.createElement('a');
      action.className = 'btn btn-primary';
      action.href = card.href;
      action.textContent = typeof I18n === 'undefined' ? 'Ask for this service' : I18n.t('home.requestThis');
      body.append(title, copy, action);
      article.append(image, body);
      container.appendChild(article);
    });
  },
};

document.addEventListener('DOMContentLoaded', () => {
  HomePage.init();
});

document.addEventListener('kaamdo:language', () => {
  if (HomePage.cards) HomePage.renderCategories(HomePage.cards);
});
