/**
 * Login and register field checks.
 * These functions do not call the network and do not create an account.
 */

const AuthFormLogic = {
  phoneDigits(value) {
    return String(value == null ? '' : value).replace(/\D/g, '').slice(0, 10);
  },

  phoneProblems(value) {
    if (!/^[6-9]\d{9}$/.test(this.phoneDigits(value))) {
      return ['login.phoneInvalid'];
    }
    return [];
  },

  loginProblems(phone, password) {
    const problems = this.phoneProblems(phone);
    if (!String(password == null ? '' : password)) {
      problems.push('login.passwordRequired');
    }
    return problems;
  },

  registerProblems(name, phone, password) {
    const problems = [];
    if (!String(name == null ? '' : name).trim()) {
      problems.push('register.nameRequired');
    }
    problems.push(...this.phoneProblems(phone));
    if (String(password == null ? '' : password).length < 8) {
      problems.push('register.passwordShort');
    }
    return problems;
  },
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = AuthFormLogic;
}
