/**
 * Role cards open one workspace. The URL is not permission.
 */

const AccountWorkspace = {
  href(item) {
    if (!item || !item.page || !item.code) return '../dashboard/dashboard.html';
    return `../${item.page}?workspace=${encodeURIComponent(item.code)}`;
  },

  fromQuery(search) {
    const text = String(search == null ? '' : search);
    const query = text.startsWith('?') ? text.slice(1) : text;
    const value = new URLSearchParams(query).get('workspace') || '';
    return /^[a-z_]+$/.test(value) ? value : '';
  },

  owned(items, codes) {
    const allowed = Array.isArray(codes) ? codes : [];
    return (items || []).filter((item) => allowed.indexOf(item.code) !== -1);
  },

  pick(items, workspace, codes) {
    const owned = this.owned(items, codes);
    if (!workspace) return owned;
    return owned.filter((item) => item.code === workspace);
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = AccountWorkspace;
}
