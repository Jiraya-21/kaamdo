/**
 * KaamDo Geolocation Utility
 * Helper to obtain user GPS coordinates for radius-based worker discovery.
 * Coordinates are rounded to 6 decimal places so they fit the server fields.
 */

const GeolocationUtil = {
  DECIMALS: 6,

  coordinateText(value) {
    if (value == null || value === '') return '';
    const number = Number(value);
    if (!Number.isFinite(number)) return '';
    return number.toFixed(this.DECIMALS);
  },

  /**
   * Prompts user for current position.
   * @returns {Promise<{latitude: number, longitude: number}>}
   */
  getCurrentCoordinates() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('Geolocation is not supported by this browser.'));
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            latitude: Number(GeolocationUtil.coordinateText(position.coords.latitude)),
            longitude: Number(GeolocationUtil.coordinateText(position.coords.longitude)),
          });
        },
        (error) => {
          reject(error);
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    });
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = GeolocationUtil;
}
