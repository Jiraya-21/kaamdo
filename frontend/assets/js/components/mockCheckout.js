/**
 * Simple Razorpay-style mock checkout for exhibition / local testing.
 * Never collects real money.
 */

const MockCheckout = {
  open({ title, amountInr, note, onConfirm }) {
    this.close();
    const overlay = document.createElement('div');
    overlay.id = 'mock-checkout-overlay';
    overlay.className = 'mock-checkout-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');

    const panel = document.createElement('div');
    panel.className = 'mock-checkout-panel';

    const heading = document.createElement('h2');
    heading.className = 'mock-checkout-title';
    heading.textContent = title || 'Pay inspection fee';

    const amount = document.createElement('p');
    amount.className = 'mock-checkout-amount';
    amount.textContent = `₹${amountInr || '0.00'}`;

    const copy = document.createElement('p');
    copy.className = 'mock-checkout-note';
    copy.textContent = note || 'Pay the inspection fee to continue.';

    const actions = document.createElement('div');
    actions.className = 'mock-checkout-actions';

    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.className = 'btn btn-outline';
    cancel.textContent = 'Cancel';
    cancel.addEventListener('click', () => this.close());

    const pay = document.createElement('button');
    pay.type = 'button';
    pay.className = 'btn btn-primary';
    pay.textContent = 'Pay';
    pay.addEventListener('click', async () => {
      pay.disabled = true;
      cancel.disabled = true;
      pay.textContent = 'Paying…';
      try {
        if (typeof onConfirm === 'function') await onConfirm();
        this.close();
      } catch (error) {
        pay.disabled = false;
        cancel.disabled = false;
        pay.textContent = 'Pay';
        copy.textContent = (error && error.message) || 'Payment could not be recorded.';
        copy.classList.add('is-error');
      }
    });

    actions.append(cancel, pay);
    panel.append(heading, amount, copy, actions);
    overlay.appendChild(panel);
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) this.close();
    });
    document.body.appendChild(overlay);
  },

  close() {
    const existing = document.getElementById('mock-checkout-overlay');
    if (existing) existing.remove();
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = MockCheckout;
}
