/**
 * KaamDo Auth API
 * API routes for authentication and user account management.
 */

const AuthApi = {
  // POST /api/v1/auth/register/
  register(userData) {
    return ApiClient.post('/auth/register/', userData);
  },

  // POST /api/v1/auth/login/
  login(credentials) {
    return ApiClient.post('/auth/login/', credentials);
  },

  // POST /api/v1/auth/logout/
  logout() {
    return ApiClient.post('/auth/logout/', {});
  },

  // GET /api/v1/auth/me/
  getCurrentUser() {
    return ApiClient.get('/auth/me/');
  },

  // POST /api/v1/auth/capabilities/
  enableCapability(capability) {
    return ApiClient.post('/auth/capabilities/', { capability });
  },

  // PATCH /api/v1/auth/mode/
  setActiveMode(activeMode) {
    return ApiClient.patch('/auth/mode/', { active_mode: activeMode });
  },

  sendOtp(phoneNumber, purpose) {
    return ApiClient.post('/auth/otp/send/', {
      phone_number: phoneNumber,
      purpose: purpose || 'account',
    });
  },

  verifyOtp(phoneNumber, purpose, code) {
    return ApiClient.post('/auth/otp/verify/', {
      phone_number: phoneNumber,
      purpose,
      code,
    });
  },

  formatError(error) {
    if (!error || !error.status) {
      return 'Could not reach the server. Start the Django server and try again.';
    }
    const data = error.data;
    if (!data) {
      return 'Request failed.';
    }
    if (typeof data.detail === 'string') {
      return data.detail;
    }
    const messages = [];
    Object.keys(data).forEach((key) => {
      const value = data[key];
      messages.push(Array.isArray(value) ? value.join(' ') : String(value));
    });
    return messages.join(' ') || 'Request failed.';
  }
};
