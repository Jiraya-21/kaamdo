/**
 * KaamDo API Client
 * Centralized HTTP request utility with token injection and error handling.
 */

const ApiClient = {
  /**
   * Performs an HTTP request against the Django REST API.
   * @param {string} endpoint - API path (e.g., '/workers/')
   * @param {object} options - Fetch options (method, headers, body)
   * @returns {Promise<any>}
   */
  async request(endpoint, options = {}) {
    const url = `${CONFIG.API_BASE_URL}${endpoint}`;
    const token = StorageUtil.get(CONFIG.STORAGE_KEYS.AUTH_TOKEN);

    const isForm = typeof FormData !== 'undefined' && options.body instanceof FormData;
    const headers = {
      'Accept': 'application/json',
      ...(token && { 'Authorization': `Token ${token}` }),
      ...options.headers
    };
    if (isForm) {
      delete headers['Content-Type'];
    } else if (!headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    let response;
    try {
      response = await fetch(url, { ...options, headers });
    } catch (error) {
      throw {
        status: 0,
        data: { detail: 'The server could not be reached. Try again in a moment.' },
      };
    }

    if (response.status === 204) return null;

    let data = null;
    try {
      data = await response.json();
    } catch (error) {
      data = null;
    }
    if (!response.ok) {
      throw { status: response.status, data };
    }
    return data;
  },

  get(endpoint, params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `${endpoint}?${query}` : endpoint;
    return this.request(path, { method: 'GET' });
  },

  post(endpoint, body) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  },

  postForm(endpoint, formData) {
    return this.request(endpoint, {
      method: 'POST',
      body: formData
    });
  },

  put(endpoint, body) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body)
    });
  },

  patch(endpoint, body) {
    return this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body)
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
};
