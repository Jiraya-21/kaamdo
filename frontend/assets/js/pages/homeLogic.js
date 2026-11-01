/**
 * Homepage Daily Services links.
 * Categories are the customer entry. This file does not load worker profiles.
 */

const HomeLogic = {
  CATEGORY_PATH: '/workers/categories/',
  SERVICE_PAGE: 'pages/services/guest-request.html',
  DIRECTORY_PAGE: 'pages/workers/directory.html',

  rowsFrom(data) {
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data.results)) return data.results;
    return [];
  },

  nextPath(page, apiBase) {
    if (!page || !page.next || !String(page.next).startsWith(apiBase)) return '';
    return String(page.next).slice(apiBase.length);
  },

  categoryCards(rows) {
    return (Array.isArray(rows) ? rows : [])
      .filter((row) => row && row.slug && row.name)
      .map((row) => ({
        name: String(row.name),
        slug: String(row.slug),
        description: row.description ? String(row.description) : '',
        href: `${this.SERVICE_PAGE}?category=${encodeURIComponent(row.slug)}`,
      }));
  },

  searchTarget(query) {
    const text = String(query == null ? '' : query).trim();
    if (!text) return this.SERVICE_PAGE;
    return `${this.SERVICE_PAGE}?q=${encodeURIComponent(text)}`;
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = HomeLogic;
}
