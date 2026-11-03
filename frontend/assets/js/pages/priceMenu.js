/**
 * Public company price menu page.
 */

const PriceMenuPage = {
  async init() {
    const notice = document.getElementById('price-menu-notice');
    try {
      const data = await ApiClient.get('/workers/price-menu/');
      this.render(data);
      if (notice) {
        notice.textContent = data.mock_checkout
          ? (typeof I18n === 'undefined'
            ? 'Test checkout is on. Payments here do not take real money.'
            : I18n.t('priceMenu.testOn'))
          : (typeof I18n === 'undefined'
            ? 'Live gateway payment is not connected yet. This menu still shows the fees.'
            : I18n.t('priceMenu.testOff'));
        notice.classList.add('is-info');
      }
    } catch (error) {
      if (notice) {
        notice.textContent = (error && error.message) || 'Price menu could not load.';
        notice.classList.add('is-error');
      }
    }
  },

  render(data) {
    const steps = document.getElementById('price-menu-steps');
    const inspection = document.getElementById('price-menu-inspection');
    const extras = document.getElementById('price-menu-extras');
    if (steps) {
      steps.replaceChildren();
      (data.steps || []).forEach((line) => {
        const item = document.createElement('li');
        item.textContent = line;
        steps.appendChild(item);
      });
    }
    if (inspection) {
      inspection.replaceChildren();
      if (data.inspection_fee) inspection.appendChild(this.card(data.inspection_fee, true));
    }
    if (extras) {
      extras.replaceChildren();
      (data.extras || []).forEach((row) => extras.appendChild(this.card(row, false)));
    }
  },

  card(row, isInspection) {
    const article = document.createElement('article');
    article.className = `price-menu-card${isInspection ? ' is-inspection' : ''}`;
    const title = document.createElement('h3');
    title.textContent = row.title || '';
    const desc = document.createElement('p');
    desc.textContent = row.description || '';
    const amount = document.createElement('div');
    amount.className = 'price-menu-amount';
    amount.textContent = `₹${row.amount_inr || '0.00'}`;
    article.append(title, desc, amount);
    return article;
  },
};

document.addEventListener('DOMContentLoaded', () => PriceMenuPage.init());
