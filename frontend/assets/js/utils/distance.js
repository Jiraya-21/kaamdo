/**
 * Straight-line kilometres. This is not the distance by road.
 */

const DistanceKm = {
  EARTH_RADIUS_KM: 6371,

  between(latitudeA, longitudeA, latitudeB, longitudeB) {
    const raw = [latitudeA, longitudeA, latitudeB, longitudeB];
    if (raw.some((value) => value == null || value === '')) return null;
    const values = raw.map(Number);
    if (values.some((value) => !Number.isFinite(value))) return null;
    const [lat1, lon1, lat2, lon2] = values.map((value) => value * Math.PI / 180);
    const deltaLat = lat2 - lat1;
    const deltaLon = lon2 - lon1;
    const chord = Math.sin(deltaLat / 2) ** 2
      + Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) ** 2;
    const clamped = Math.min(1, Math.max(0, chord));
    return 2 * this.EARTH_RADIUS_KM * Math.asin(Math.sqrt(clamped));
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = DistanceKm;
}
