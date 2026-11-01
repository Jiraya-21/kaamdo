# KaamDo REST API Design Specification

All endpoints are prefixed with `/api/v1/` and exchange payloads in standard `application/json` format.

---

## 1. Accounts & Authentication (`/api/v1/auth/`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/auth/register/` | Register new user with selected role (Customer, Worker, Farmer, etc.) | No |
| `POST` | `/auth/login/` | Authenticate user, return auth token & user profile summary | No |
| `POST` | `/auth/logout/` | Invalidate active auth token | Yes |
| `GET` | `/auth/me/` | Get current user's role, profile, and basic details | Yes |
| `PUT/PATCH` | `/auth/me/` | Update user details (name, email, phone, avatar) | Yes |

---

## 2. Worker Profiles & Discovery (`/api/v1/workers/`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/workers/` | Search and discover workers (supports `?lat=`, `?lng=`, `?radius=20`, `?skill=`, `?sort=`) | No |
| `GET` | `/workers/<id>/` | View complete public worker profile, skills, rates, and reviews | No |
| `POST` | `/workers/profile/` | Create or initialize worker profile details | Yes (Worker) |
| `PUT/PATCH` | `/workers/profile/` | Update worker profile (rate, skills, availability, service radius) | Yes (Worker) |
| `POST` | `/workers/verify/` | Submit identity verification request | Yes (Worker) |

---

## 3. Jobs, Requests & Price Agreement (`/api/v1/jobs/`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/jobs/` | List available open jobs with optional filters | No |
| `POST` | `/jobs/` | Post a new job opportunity | Yes (Customer/Employer) |
| `GET` | `/jobs/<id>/` | View details of a specific job | No |
| `POST` | `/jobs/<id>/apply/` | Worker applies for a posted job with proposed rate | Yes (Worker) |
| `POST` | `/jobs/hire-request/` | Customer sends direct hire request to a specific worker | Yes (Customer) |
| `GET` | `/jobs/my-requests/` | List all incoming/outgoing job and hiring requests | Yes |
| `POST` | `/jobs/requests/<id>/action/` | Accept or reject a job or hire request (`{"action": "accept"|"reject"}`) | Yes (Participant) |
| `POST` | `/jobs/requests/<id>/price-revision/` | Request a revised price with mandatory reason | Yes (Participant) |
| `POST` | `/jobs/requests/<id>/price-revision/action/` | Accept or reject price change (`{"action": "accept"|"reject"}`) | Yes (Counterparty) |
| `POST` | `/jobs/<id>/complete/` | Mark job as completed | Yes (Customer) |

---

## 4. Agricultural Equipment Rental (`/api/v1/equipment/`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/equipment/` | List available agricultural equipment (filters: category, rate, location) | No |
| `GET` | `/equipment/<id>/` | View equipment details, specs, hourly/daily rental rates, owner info | No |
| `POST` | `/equipment/` | List new equipment for rent | Yes (Equipment Owner/Farmer) |
| `PUT/PATCH` | `/equipment/<id>/` | Update equipment details, availability, or rental rate | Yes (Owner) |
| `DELETE` | `/equipment/<id>/` | Remove equipment listing | Yes (Owner) |
| `POST` | `/equipment/<id>/rent/` | Submit a rental booking request (dates, duration, delivery terms) | Yes (Farmer/Customer) |
| `GET` | `/equipment/rentals/` | List user's rental requests (sent and received) | Yes |
| `POST` | `/equipment/rentals/<id>/action/` | Owner accepts or rejects rental request (`{"action": "accept"|"reject"}`) | Yes (Owner) |

---

## 5. Ratings & Reviews (`/api/v1/reviews/`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/reviews/worker/<worker_id>/` | Get verified reviews and ratings for a worker | No |
| `POST` | `/reviews/` | Submit a review (Rating 1-5, review text) strictly linked to a completed job | Yes (Customer) |

---

## 6. Notifications (`/api/v1/notifications/`)

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/notifications/` | List current user's notifications (newest first) | Yes |
| `POST` | `/notifications/<id>/read/` | Mark single notification as read | Yes |
| `POST` | `/notifications/read-all/` | Mark all user notifications as read | Yes |
