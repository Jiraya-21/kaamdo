# KaamDo pre-release checklist

Prepared 27 October 2026 (final acceptance pass). This does not authorize a public launch, live payments, bulk SMS, DNS changes, or migrating `backend/db.sqlite3`.

Statuses: **PASS** verified · **FAIL** defect remains · **BLOCKED** needs you or an external service · **NOT TESTED** · **NOT APPLICABLE**.

No API keys, passwords, OTPs, tracking keys, or full live phone numbers are written here.

---

## 1. What this pass did

Used the existing matching engine. Did not rebuild matching. Did not enable payments. Did not deploy.

- Isolated consistent copy of `backend/db.sqlite3` via sqlite3 `backup()` from a read-only URI.
- Live file hash and size verified unchanged after copy, after acceptance, and after isolated API work.
- `workers.0008` was already present on the live snapshot (`showmigrations` `[X]`). This pass did **not** run `migrate` against the live file. `migrate workers 0008` on the copy printed `No migrations to apply`.
- A separate empty isolated database applied the full graph through `workers.0008` successfully.
- Matching lifecycle, SQLite parallel accept, scheduler, suites, SMS config, and isolated signed-in API workflows were run.

Temporary isolated API: `127.0.0.1:8001` with `config.isolated_copy_settings`. Isolated OTP and visit payment forced `unconfigured`.

### Wrap-up (this session)

Re-checked files and leftover processes. Did not migrate or write `backend/db.sqlite3`. Did not send SMS. Did not restart matching.

| Item | Result |
| --- | --- |
| Live SQLite re-hash | **PASS** — SHA256 `868a73bd2496bb9ed8660d653413d5d90583133cc0337b8647e755233f18e8e7`, size **536576**, `mtime_ns` **1793067070425361000** unchanged |
| Live `workers.0008` (read-only `django_migrations`) | **PASS** — `[X]` already present (`0001`–`0008`). This wrap-up did not run `migrate` |
| Isolated copy still on disk | **PASS** — `C:\Users\karna-gr\AppData\Local\Temp\kaamdo-accept-jqunyw17\db-copy.sqlite3` exists; copy SHA256 `44a3d14429cb05842ec89d9856537e143c02d98b485381869aede4ead56b63fe` (lifecycle writes); `0008` present; leftover rows `accept_users=6`, `daily_requests=13`, `offers=14` |
| Frontend API default | **PASS** — leftover test default `8001` reverted to environment-aware `http://127.0.0.1:8000/api/v1` plus `window.KAAMDO_API_BASE`. `config.test.js` **PASS**. No `8001` left in `frontend/assets/js/config.js` |
| Leftover isolated API / matching loop | **PASS** (stopped) — leftover `runserver 127.0.0.1:8001 --noreload` (PIDs 5748 / 16520) stopped. No `run_matching_loop` or `process_daily_matching` process. Ports **8000 / 8001 / 8768** down after wrap-up |
| Browser lock | **PASS** (unlocked) |

---

## 2. Database-copy verification

| Criterion | Result | Evidence |
| --- | --- | --- |
| Consistent copy of live SQLite | **PASS** | `sqlite3.connect(..., uri=True)` + `backup()` to `C:\Users\karna-gr\AppData\Local\Temp\kaamdo-accept-jqunyw17\db-copy.sqlite3` (earlier copy `kaamdo-accept-9k5d4a_9`) |
| Live file unchanged | **PASS** | SHA256 `868a73bd2496bb9ed8660d653413d5d90583133cc0337b8647e755233f18e8e7`, size **536576**, `mtime_ns` **1793067070425361000** before copy, after copy, after acceptance, and after isolated API work |
| `workers.0008` on copy only | **PASS** / already applied | Copy snapshot already had `0008`. Empty isolated migrate applied `workers.0008_daily_matching_state` (`ISOLATED_MIGRATE_OK`). Live `migrate` was not run |
| Existing records readable | **PASS** | Isolated copy: 6 users, 5 daily requests, 3 offers, 6 categories; matching request/offer columns ready |
| Consent / radius / attempts / reason / expiry fields | **PASS** | Isolated lifecycle wrote `search_radius_km`, `consented_radius_km`, `match_reason`, `expires_at` |
| Live database written | **PASS** (not written) | Hash/size/mtime unchanged |

The first isolated-migrate helper called `django.setup()` against default settings, then overrode `DATABASES`. It printed `No migrations to apply` and tempfile size 0, so it did **not** apply to the empty file. Live hash still matched. The helper was then pointed at `config.isolated_copy_settings` and a new empty file; that run applied every app through `workers.0008`.

Live `showmigrations workers` already showed `[X] 0008_daily_matching_state` before this pass. Do not treat that as this pass upgrading the user’s file.

---

## 3. Matching acceptance (isolated copy)

Second isolated runner, all listed items **PASS**:

| Criterion | Result | Persisted state |
| --- | --- | --- |
| Initial offers | **PASS** | `offering` / `offering`, `search_radius_km=8`, 2 offers; 12 km worker excluded |
| Decline → next batch | **PASS** | Status stayed `offering`; second offer `offered` |
| Timeout without customer refresh | **PASS** | `process_due_matching`: `expired_offers=1`; offer `expired`; request `no_acceptance` / `pool_exhausted` |
| Radius consent + expand | **PASS** | `consented_radius_km=15`, `search_radius_km=15`, 1 new offer |
| Busy provider skipped | **PASS** | Far worker with an open offer was not offered on a second request |
| Assignment | **PASS** | `assigned` / `assigned`, `assigned_profile_id` set |
| Late accept cannot override | **PASS** | `ValidationError`; assignment unchanged |
| Cancellation | **PASS** | `cancelled` / `cancelled`; 0 open offers |
| Exhaustion | **PASS** | Unique empty category → `no_workers` / `needs_radius_consent` |
| Retries do not duplicate offers | **PASS** | Offer profile set 3 = 3 after a second `advance_matching` |
| Duplicate notifications | **NOT APPLICABLE** | Matching does not create notification or SMS rows. No fan-out to duplicate |
| Customer-facing status = backend | **PASS** | Isolated statuses matched persisted `DailyServiceRequest.status` and `match_reason` |

First isolated run had exhaustion **FAIL** (shared category picked leftover workers) and assignment `match_reason` still `offering`. Those were fixed (unique empty category; accept path sets `match_reason=assigned`). Second run passed. Automated suite still **221** OK after the accept-reason change.

---

## 4. Concurrency

| Criterion | Result | Evidence |
| --- | --- | --- |
| PostgreSQL / staging engine | **BLOCKED** | `psql` missing; `psycopg` / `psycopg2` not installed |
| Parallel accepts, independent connections | **PASS** (SQLite only) | Two threads, `connections.close_all()`, barrier; outcomes `OperationalError` + `accepted`; `accepted_offers=1`; one `assigned_profile_id` |
| Sequential second accept | **PASS** (not claimed as simultaneous) | Automated late-accept / leftover-withdrawn tests |
| Simultaneous accept on PostgreSQL | **NOT TESTED** | No staging PostgreSQL on this machine |

SQLite serialized the writers. One attempt hit `OperationalError` (database locked). That is a safe failure, not a second winner. It is **not** proof of PostgreSQL `select_for_update` under two committed transactions.

---

## 5. Expiry scheduling

| Criterion | Result | Evidence |
| --- | --- | --- |
| `manage.py process_daily_matching` | **PASS** | Isolated: `expired_offers=0 requests=1`. Lifecycle timeout used the same `process_due_matching` path (`expired_offers=1`) |
| `run_matching_loop --interval 15` | **PASS** | Isolated, `PYTHONUNBUFFERED=1`, then stopped. Printed `matching loop every 15s` and three ticks `expired_offers=0 requests=1` |
| Expiry/reassignment without a page refresh | **PASS** (backend) | Timeout test expired the offer and updated request status with no HTTP from the customer |
| Customer UI updates without refresh | **NOT TESTED** | Track and account pages do not poll. A customer must look up or reload to see the new status |
| Process stop | **PASS** (observed) | After `Stop-Process`, no further ticks. Offers that expire while the loop is down stay offered until the next command/loop |
| Process restart | **PASS** (observed) | Restart runs `process_due_matching` immediately, then sleeps |
| Docker / new infra | **NOT APPLICABLE** | None installed |

`runserver` does not schedule matching. Automatic continuation exists only while `process_daily_matching` or `run_matching_loop` is actually running.

---

## 6. Browser acceptance

| Criterion | Result | Notes |
| --- | --- | --- |
| Unsigned track-request page (desktop) | **PASS** | `http://127.0.0.1:8768/pages/services/track-request.html`: request number + tracking key fields; key not read from URL; Kannada/English controls present (earlier this day and this pass) |
| Signed-in customer matching UI | **NOT TESTED** | Browser tab automation dropped mid-pass. Isolated API: customer list **PASS**, expand **PASS**, cancel **PASS** |
| Signed-in provider matching UI | **NOT TESTED** | Isolated API: offers list **PASS**, accept **PASS**. Decline on the signed-in fixture **NOT TESTED** (provider already assigned). Decline **PASS** in isolated lifecycle |
| Radius expansion UI | **NOT TESTED** | Isolated expand API **PASS** (`search_radius_km=15`) |
| Accept / decline UI | **NOT TESTED** | Isolated accept API **PASS**. Decline: lifecycle **PASS** |
| Cancellation UI | **NOT TESTED** | Isolated cancel API **PASS** (`cancelled`) |
| Provider availability UI | **NOT TESTED** | Isolated PATCH `unavailable` then `available` **PASS** |
| Photo upload UI | **NOT TESTED** | Isolated JPEG POST `/workers/profile/photo/` **PASS**. A 1×1 synthetic PNG was rejected (`Upload a valid image`) — use a real JPEG/PNG/WebP ≤ 2 MB |
| Employer job close UI | **NOT TESTED** | Isolated PATCH `{status: closed}` **PASS** only after `PhoneVerification` for purpose `account`. Unverified employer: `400` “Verify your mobile number before posting work.” |
| Equipment booking UI | **NOT TESTED** | Isolated signed-in renter POST booking **PASS** (`201`, `requested`). Guest booking OTP was not used (isolated SMS off) |
| 390px mobile layouts | **NOT TESTED** | Viewport pass was not completed after the browser tab was lost |

### Manual steps (signed-in, isolated only)

Do **not** point these at live `8000` / `backend/db.sqlite3`.

1. Start isolated API: `KAAMDO_ISOLATED_SQLITE` = copy path, `DJANGO_SETTINGS_MODULE=config.isolated_copy_settings`, `manage.py runserver 127.0.0.1:8001`.
2. Serve `frontend` on `8768`. Set `window.KAAMDO_API_BASE = 'http://127.0.0.1:8001/api/v1'` **before** `config.js` loads. Do **not** commit a `8001` default.
3. Log in with isolated seed phones `9000004301` (customer), `9000004302` (provider), `9000004303` (employer; needs account phone verification to close), `9000004305` (renter). Password exists only on the copy.
4. Customer page: confirm offering/assigned/cancelled copy, Expand, Cancel.
5. Provider page: availability switch, photo (real image), Accept / Decline.
6. Employer page: Close on a published post.
7. Equipment details: signed-in booking dates.
8. Repeat at 1280px and 390px.
9. Stop `8001`. Do not send OTP.

---

## 7. SMS safety

| Criterion | Result | Evidence |
| --- | --- | --- |
| Effective local OTP (live process) | **BLOCKED** (live-capable) | `OTP_DELIVERY=smsmobileapi`, `SMS_KEY_PRESENT=True`, `SMS_CONFIGURED=True`, `VISIT_PAYMENT=unconfigured`, `DEBUG=True`. Guest options on live `8000` earlier: phone `{available:true, mode:sms}` |
| Isolated process | **PASS** (disabled) | Forced `unconfigured`. Guest options on `8001`: email and phone `unavailable` |
| Real SMS sent this pass | **PASS** (none sent) | No send calls. Isolated key wiped |
| Secrets printed | **PASS** (not printed) | Only redacted flags |
| Acceptance vs delivery in logs | **FAIL** (not supported) | Adapter POSTs `https://api.smsmobileapi.com/sendsms/`. `result.error` in `{0,'0'}` is **acceptance**. User copy: “The SMS provider accepted the request. Enter the code when it arrives.” No sent-log / delivery-status URL is implemented. Tests assert there is no `STATUS_URL` |

Keep real SMS off unless you authorize a named handset test.

---

## 8. Final checks

| Command | Result | Exit |
| --- | --- | --- |
| `manage.py test` | **221** tests, **299.810s**, OK (prior this day; not re-run this wrap-up) | **0** |
| Frontend `node tests\*.js` | Prior matching pass: **25** files, all passed, exit **0**. This wrap-up glob is **27** files: matching/`config` tests **PASS**; **2 FAIL** in parallel Karnataka work (`formI18n.test.js` expects `#manual-location-fields`; `maps.test.js` nominatim/`enabled` assertion). Those files were not changed here | **1** this wrap-up; **0** on the earlier 25-file matching suite |
| `manage.py check` | 0 issues | **0** |
| `manage.py check --deploy` | 0 errors, 6 warnings (`kaamdo.W001`, `security.W004`, `W008`, `W012`, `W016`, `W018`) | **0** |
| `makemigrations --check --dry-run` | No changes detected | **0** |
| Isolated empty migrate through `0008` | Applied, including `workers.0008` | **0** |
| Live `migrate` | **not run** | — |
| Payments enabled | **not enabled** | — |
| Public deploy | **not done** | — |

Timeouts were not treated as passes. Assertions were not weakened.

---

## 9. Remaining blockers and your actions

1. Treat local SMS as live-capable. If this machine is reachable, set `KAAMDO_OTP_DELIVERY=unconfigured`.
2. Do not reset `backend/db.sqlite3`. `0008` is already recorded on that file; this pass did not apply it.
3. Schedule `python manage.py process_daily_matching` (Task Scheduler, every 1 minute is a reasonable start) or watch `run_matching_loop`. `runserver` will not expire offers by itself.
4. PostgreSQL is required before claiming two providers can accept at the same instant.
5. Sign in yourself for the UI flows in section 6. Employer close needs a verified account phone. Photo needs a real image file. Create `backend/media` before live photo uploads.
6. Customer status pages do not auto-refresh; tell people to look up again after a few minutes.
7. Keep payments unconfigured. Do not deploy publicly.

---

## 10. Verdicts

| Target | Verdict |
| --- | --- |
| Local development (127.0.0.1) | **PASS** — matching engine, isolated lifecycle, suites, and isolated signed-in APIs work. SMS is live-capable. Signed-in **browser** matching is **NOT TESTED**. Schedule the expiry command if you want timeouts without a decline. |
| Controlled staging | **FAIL** — no PostgreSQL concurrency proof, LocMem OTP limits (`W001`), `DEBUG`/HTTPS/HSTS unset, signed-in UI unverified, SMS acceptance ≠ delivery |
| Public production | **FAIL** — no real payment, SMS not delivery-confirmed, HTTPS unset, SQLite not suitable, browser matching untested. 221 passing tests are not a launch certificate |
