/**
 * KaamDo DOM Utilities
 * Helper functions for DOM querying, event binding, and HTML element rendering.
 */

const DomUtil = {
  $(selector, context = document) {
    return context.querySelector(selector);
  },

  $$(selector, context = document) {
    return Array.from(context.querySelectorAll(selector));
  },

  setHtml(element, htmlString) {
    if (element) element.innerHTML = htmlString;
  },

  show(element) {
    if (element) element.style.display = '';
  },

  hide(element) {
    if (element) element.style.display = 'none';
  }
};
