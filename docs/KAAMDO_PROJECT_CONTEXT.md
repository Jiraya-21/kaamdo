# KaamDo project context

Living product notes. Prefer this over re-auditing the whole codebase for routine work.

## Product boundaries

- Four marketplace sections: Daily Services, Jobs, Equipment, Farm hiring.
- **One person = one account = one phone = multiple professional roles.**
- Customer is marketplace access, not a professional role. Every signed-in account can request and track Daily Services without activating Customer.
- Professional roles (optional): Service Provider; Job Seeker / Employer; Equipment Owner / Renter; Agricultural Worker / Employer.
- Daily Services posts to `/api/v1/workers/daily-requests/` with existing matching / accept / decline.
- Matching stages stay 8 / 15 / 20 km with hard max 100 km; customer radius is a cap.
- OTP, auth, DB schema, and payments stay as-is unless explicitly approved.
- No Docker. Local default DB is SQLite; PostgreSQL remains optional via env only.
- Redis remains optional and unused unless `KAAMDO_CACHE_BACKEND=redis`.
- No React / Node build step. Plain HTML/CSS/JS frontend.
- Voice / STT / TTS / read-aloud are removed. Do not reintroduce them.
- Website languages: English (`en`), Kannada (`kn`), Hindi (`hi`), Marathi (`mr`).

## Account hub

- Compact identity bar: name, phone, logout (minimal copy).
- Marketplace destinations (every signed-in user): short taps — Helper today → `services/customer.html`; Jobs; Machines; Farm work.
- Provider accounts: single Available / Not available switch on the hub (and compact switch in provider workspace).
- Professional roles: title + Open only; verification note only when not approved.
- Add work: collapsed; title + Add. Customer cannot be added via `POST /auth/capabilities/`.
- First-area banner: Mandya; demo titles use `[Demo]`.
- Assets: `dashboard.css?v=hub4`, `dashboard.js?v=hub4`, `catalog.js?v=hub4`, `messages.js?v=hub4`.

## First-area demo data

- Command: `python manage.py seed_first_area_demo` (idempotent phones `9000005001`–`9000005005`).
- Seeds published Mandya workers, ordinary jobs, farm posts, and fee-waived equipment.
- Public list/directory district filters default to Mandya for local browsing.

## Worker identity and arrival (Daily Services)

- Permanent `kaamdo_worker_id` on `WorkerProfile` (format `KD…`).
- After assignment, owners see a digital Worker ID card (`worker_identity` / `assigned_profile`) with photo, name, ID, category, skills, identity verification flags, experience, completed jobs. Ratings omitted until real reviews exist. No phone/Aadhaar/coords.
- Arrival: assigned provider `POST .../daily-requests/{id}/arrival/signal/` → booking-specific 6-digit code. Owner verifies with `.../arrival/verify/` (login OTP is never reused). Then status → `in_progress` and `arrival_verified_at` is set.
- Completion: owner `POST .../complete/` only after verified arrival; assigned worker stays linked.
- Replacement: `DailyServiceAssignmentEvent` audit; open arrival codes superseded; fresh arrival required. Silent replacement is not allowed.
- Migration: `workers.0010_worker_identity_and_arrival`.

## Verified cleanup (prior)

- Docker and voice removed; location confirm panels removed; SMSMobileAPI `sms.ok` + `result` envelopes; Marathi parity.

## Local startup (Windows)

```powershell
cd "D:\project  kaam-do\Kaamdo.1\backend"
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

```powershell
cd "D:\project  kaam-do\Kaamdo.1"
.\venv\Scripts\python.exe -m http.server 5500 --directory frontend
```

Matching pulse (optional):

```powershell
cd "D:\project  kaam-do\Kaamdo.1\backend"
..\venv\Scripts\python.exe manage.py process_daily_matching
```

## Remaining blockers

- Live SMS handset delivery depends on the connected SMSMobileAPI phone being online; provider acceptance is not delivery proof.
- Reviews / reliability scores remain stubs — Worker ID card does not invent ratings.
- Job seeker / employer / equipment / farm public identity cards are profile-based today; Daily Services arrival OTP is intentionally not forced onto those workflows.
- Do not deploy publicly or enable payments without a separate approval.
