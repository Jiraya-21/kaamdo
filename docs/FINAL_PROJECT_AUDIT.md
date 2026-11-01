# KaamDo final project audit

Prepared 27 October 2026 (final acceptance). Evidence: `docs/PRE_RELEASE_CHECKLIST.md`. No public deploy. `migrate` was **not** run against `backend/db.sqlite3` in this pass.

## Executive summary

KaamDo remains Django 6.0.9 + DRF 3.18.3 with a vanilla HTML/CSS/JS frontend. Four marketplace sections: Daily Services, Jobs, Equipment, Farm hiring.

Daily Services matching ranks by straight-line kilometres, offers a batch (default 3), expires unanswered offers (default 180 seconds), and continues on decline or timeout. Radius stages default 8 → 15 → 20 km inside the consented cap. The trigger is `manage.py process_daily_matching`, not a page refresh.

This acceptance pass copied the live SQLite file, left that file’s hash unchanged, and ran matching, concurrency, scheduler, suites, and isolated signed-in APIs on the copy.

| Target | Verdict |
| --- | --- |
| Local development (loopback) | **PASS** |
| Controlled staging | **FAIL** |
| Public production | **FAIL** |

Tests: **221** backend (299.810s, exit 0, not re-run this wrap-up). Frontend: earlier matching suite **25** files exit 0; wrap-up re-run saw **27** files with **2 FAIL** in Karnataka location/map tests (`formI18n.test.js`, `maps.test.js`) owned by the parallel stream. `config.test.js` **PASS** after restoring local API default `8000` + `window.KAAMDO_API_BASE`. Live SHA256 `868a73bd2496bb9ed8660d653413d5d90583133cc0337b8647e755233f18e8e7`, size 536576, `mtime_ns` 1793067070425361000 unchanged after wrap-up. `workers.0008` is already `[X]` on the live file; this pass did not apply it. Leftover isolated `8001` / matching loops were stopped. Browser unlocked.

## Matching

- Eligibility, ranking, batch, expiry, decline continuation, one-winner assignment, honest `no_workers` / `no_acceptance` reasons: **PASS** (isolated lifecycle + automated tests).
- Guest/customer expand and cancel: **PASS** (automated + isolated signed-in expand/cancel APIs). Wrong access key **PASS** (404, earlier).
- Busy provider skipped: **PASS**.
- Late accept cannot override: **PASS** (`ValidationError`).
- No duplicate offers on retry: **PASS**. Matching does not emit notifications: **NOT APPLICABLE**.
- Concurrent accept: SQLite parallel **PASS** (one winner; loser `OperationalError`). PostgreSQL **BLOCKED**. Sequential tests are not simultaneous proof.
- Distance is **not** road distance.
- Live signed-in browser matching **NOT TESTED**.

## Scheduler

`process_daily_matching` and isolated `run_matching_loop --interval 15` **PASS**. Three loop ticks printed, then the process was stopped. While stopped, expiry does not run. On restart, one pulse runs immediately.

Backend expiry does not need a customer refresh. The track/account pages do not poll, so the **on-screen** status will not change until the customer looks up again. That UI auto-update is **NOT TESTED**.

## Other workflows (isolated API, not browser)

| Workflow | Isolated API | Browser UI |
| --- | --- | --- |
| Provider availability | **PASS** | **NOT TESTED** |
| Provider photo (JPEG) | **PASS** | **NOT TESTED** |
| Employer job close | **PASS** after account phone verification; **400** without it | **NOT TESTED** |
| Equipment booking (signed-in renter) | **PASS** (`201` requested) | **NOT TESTED** |

## Security / payments / SMS

Unchanged guarantees: purpose-bound OTP, guest consume-on-create, staff-only mock payment, tracking key not taken from the URL.

Live local process: SMSMobileAPI configured, key present, guest phone OTP available. Isolated process: unconfigured. No messages sent. Provider `error=0` is acceptance, not handset delivery. Delivery lookup is unimplemented (**FAIL** as a delivery-status feature).

## Migrations

Empty isolated database applied through `workers.0008`. Live file hash unchanged. Do not claim this pass upgraded the user’s database.

## Next actions

See `docs/PRE_RELEASE_CHECKLIST.md` section 9. This audit does not authorize a public launch.
