# KaamDo Testing Guide & Quality Assurance Strategy

This document outlines the testing strategy, test locations, and execution instructions for the KaamDo platform.

---

## 1. Backend Testing Structure

Each Django application includes an isolated `tests/` directory to ensure maintainability:

```text
backend/
├── accounts/tests/test_auth.py           # Registration, login, role validation, permissions
├── workers/tests/test_workers.py         # Worker profile CRUD, 20 km radius calculation, availability
├── jobs/tests/test_jobs.py               # Job postings, hire requests, price revisions, lifecycle
├── equipment/tests/test_equipment.py     # Equipment listings, rental availability, booking requests
├── reviews/tests/test_reviews.py         # Completed-job review validation, unauthorized review blocks
└── notifications/tests/test_notifications.py # In-app notification creation and mark-as-read
```

### Running Backend Tests
From the `backend` directory with the virtual environment activated:

```powershell
# Run all tests across the entire project
python manage.py test

# Run tests for a specific module
python manage.py test accounts
python manage.py test workers
python manage.py test jobs

# Run with verbose output
python manage.py test -v 2
```

---

## 2. Key Test Scenarios to Cover in Future Phases

### Accounts & Auth
- [ ] Users can register with each valid role (`CUSTOMER`, `WORKER`, `FARMER`, etc.).
- [ ] Duplicate phone numbers and emails are rejected.
- [ ] Unauthenticated requests to protected endpoints return `401 Unauthorized`.

### Worker Discovery & Radius Filtering
- [ ] Workers outside the designated radius (e.g., > 20 km) are excluded from search results.
- [ ] Workers within the radius are sorted accurately by distance or rating.
- [ ] Inactive or unavailable workers are hidden from directory listings when filtered.

### Price Agreement & Revisions
- [ ] Both parties must agree before a price change is marked as accepted.
- [ ] Submitting a price revision without a reason is rejected with a `400 Bad Request`.
- [ ] Price revision history correctly logs past offers and timestamps.

### Verified Reviews
- [ ] A customer cannot post a review for a worker unless a job contract with `status="COMPLETED"` exists between them.
- [ ] Duplicate reviews for the same job are prevented.

---

## 3. Frontend Testing Approach

Because the frontend is built with vanilla JavaScript, automated unit tests can be introduced in later stages using standard tools (such as Jest or Vitest) or browser-level end-to-end tests (such as Playwright). 

Manual verification test steps:
1. Form validation checks for required fields, phone numbers, and coordinate ranges.
2. Token expiration handling and redirection to `login.html`.
3. Offline or server unreachable alerts displayed via toast notifications.
