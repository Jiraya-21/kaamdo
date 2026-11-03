/**
 * Customer search-distance slider. Matching still expands 8, 15, then 20 km
 * up to this chosen cap. Jobs and listings without radius_km do not use this.
 */

const RadiusControl = {
  MIN: 5,
  MAX: 100,
  STEP: 5,
  DEFAULT: 60,

  snap(value) {
    if (value === '' || value == null) return this.DEFAULT;
    const number = Number(value);
    if (!Number.isFinite(number)) return this.DEFAULT;
    const rounded = Math.round(number / this.STEP) * this.STEP;
    if (rounded < this.MIN) return this.MIN;
    if (rounded > this.MAX) return this.MAX;
    return rounded;
  },

  label(value) {
    return `${this.snap(value)} km`;
  },

  problems(value) {
    const number = Number(value);
    if (!Number.isInteger(number) || number < this.MIN || number > this.MAX || number % this.STEP !== 0) {
      return [`Choose a radius from ${this.MIN} to ${this.MAX} kilometres.`];
    }
    return [];
  },

  bind(input, readout) {
    if (!input) return input;
    input.type = 'range';
    input.min = String(this.MIN);
    input.max = String(this.MAX);
    input.step = String(this.STEP);
    input.value = String(this.snap(input.value || this.DEFAULT));
    input.classList.add('radius-slider-input');
    const paint = () => {
      input.value = String(this.snap(input.value));
      if (readout) readout.textContent = this.label(input.value);
    };
    if (!input.dataset.radiusBound) {
      input.dataset.radiusBound = '1';
      input.addEventListener('input', paint);
      input.addEventListener('change', paint);
    }
    paint();
    return input;
  },

  mount(host, existing) {
    const wrap = host || document.createElement('div');
    wrap.classList.add('radius-slider');
    const input = existing || document.createElement('input');
    const readout = document.createElement('p');
    readout.className = 'radius-readout';
    readout.setAttribute('aria-live', 'polite');
    if (!input.isConnected) wrap.appendChild(input);
    wrap.appendChild(readout);
    this.bind(input, readout);
    return input;
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = RadiusControl;
}
