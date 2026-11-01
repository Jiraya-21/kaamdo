# KaamDo public-pilot readiness

Prepared 27 October 2026. This is **not** a production launch certificate. No public deploy, cloud account, live SMS, or real payment was performed.

Statuses: **PASS** verified here · **FAIL** still incomplete · **BLOCKED** needs you or a paid/external service · **NOT TESTED**.

Sibling acceptance scorecards stay in `docs/PRE_RELEASE_CHECKLIST.md`, `docs/FINAL_PROJECT_AUDIT.md`, and `docs/COMPLETION_STATUS.md`. This file does not rewrite them.

## Verdict

| Target | Status |
| --- | --- |
| Local development (127.0.0.1, DEBUG=True, SQLite) | **PASS** for this prep (code and automated tests). Signed-in browser matching remains the sibling leftover. |
| Controlled staging | **FAIL** |
| Public production | **FAIL** |

## Implemented in this pass (code and docs)

- Production settings fail closed: `DEBUG=False` requires a real `SECRET_KEY`, explicit `ALLOWED_HOSTS`, real CORS/CSRF origins (no localhost), PostgreSQL, unconfigured payments, secure cookies. HTTPS redirect is not forced.
- `PORT`, `STATIC_*`, `MEDIA_ROOT` are environment-aware. `/healthz` stays public and empty of secrets.
- Frontend API uses localhost only on loopback. A public host uses same-origin `/api/v1` or `window.KAAMDO_API_BASE`. Port **8001 is not hardcoded**.
- Karnataka 31-district catalog, official taluks, seed command, forms/filters/cards, no village list, no raw lat/lon to visitors.
- Map config default `none`. Nominatim autocomplete refused. No invented centroids as pins.
- Matching scheduler documented for a real host. Render **free** plan cannot run it.
- Photo upload already exists (worker profile, isolated migration `workers.0006`). Not claimed missing.
- Payments remain unconfigured. SMS stays unconfigured unless you authorize it.

## User actions (not done here)

- Create hosting, DNS, TLS, PostgreSQL, Redis, or Render accounts.
- Put a real `SECRET_KEY` in `.env`.
- Apply `locations.0001` or `workers.0008` to the live `backend/db.sqlite3` file.
- Schedule matching on a paid cron or Windows Task Scheduler.
- Authorize live SMS or any payment provider.
- Create `backend/media` if it is missing.

## Isolated PostgreSQL migrations

**BLOCKED.** `psycopg` is optional and not installed by default. No local Postgres server was created. Isolated SQLite migrate remains the safe path.

## Matching scheduler on Render

**BLOCKED** on the free plan. Render docs: free web services spin down; cron jobs and background workers have no free instance. See `docs/DEPLOYMENT_GUIDE.md`.

## Security / privacy review (this pass)

| Item | Severity | Status | Notes |
| --- | --- | --- | --- |
| Placeholder secret with `DEBUG=False` | High | PASS | Refused at startup |
| Wildcard / missing hosts | High | PASS | Refused |
| Localhost CORS/CSRF in production | High | PASS | Refused |
| SQLite as default production DB | High | PASS | Refused unless emergency hatch |
| Mock payment in production | High | PASS | Refused |
| Public worker lat/lon | Medium | PASS | Public serializer omits coordinates |
| Guest tracking key in URL | Medium | PASS | Unchanged; sibling verified |
| Live SMS | High | BLOCKED | Unconfigured unless you authorize |
| Real payments | High | FAIL | Impossible in production by design |
| LocMem OTP limits / multi-worker | Medium | FAIL (staging) | Needs Redis for more than one worker |
| HTTPS / HSTS | High | BLOCKED | Reverse proxy after a certificate you control |
| Dependency advisory scan | Medium | NOT TESTED | No pip-audit this pass |

Published worker photos are public. Do not store identity documents in `MEDIA_ROOT`.

## Live database

This pass did **not** write or migrate `backend/db.sqlite3`. Hash and size are recorded in the handoff.

## Tests actually run

Recorded in the handoff after the commands finish. Isolated tests apply `locations.0001` on Django's temporary database only.

## Exact next user action

Keep the API on loopback and decide whether local SMS stays off. Do not deploy publicly. If you want persisted location tables, apply `locations.0001` on a **copy** of the database, not by resetting the current file.
