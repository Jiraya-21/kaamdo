/**
 * Query string for the public equipment list.
 * Filters are sent to the API so they apply before pagination.
 */

const EquipmentListLogic = {
  LIST_PATH: '/equipment/',

  clean(value) {
    return String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
  },

  params(values) {
    const params = {};
    const query = this.clean(values && values.query);
    const district = this.clean(values && values.district);
    const pricing = this.clean(values && values.pricingBasis);
    const operator = this.clean(values && values.operatorIncluded).toLowerCase();
    if (query) params.q = query;
    if (district && district.toLowerCase() !== 'all') params.district = district;
    if (pricing === 'hourly' || pricing === 'daily') params.pricing_basis = pricing;
    if (operator === 'true' || operator === 'false') params.operator_included = operator;
    return params;
  },

  rateText(item) {
    if (!item) return '';
    return `${item.rate} ${item.pricing_basis}`;
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = EquipmentListLogic;
}
