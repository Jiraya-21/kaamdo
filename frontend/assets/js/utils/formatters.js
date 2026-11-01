/**
 * KaamDo Formatters Utility
 * Functions for formatting currency, distance, dates, and ratings.
 */

const Formatters = {
  currency(amount) {
    if (amount == null) return 'N/A';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amount);
  },

  distance(km) {
    if (km == null) return '';
    return `${Number(km).toFixed(1)} km away`;
  },

  date(dateString) {
    if (!dateString) return '';
    return new Date(dateString).toLocaleDateString();
  }
};
