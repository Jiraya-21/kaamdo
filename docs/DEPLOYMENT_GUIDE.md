# KaamDo deployment guide (not a launch certificate)

This is a later-staging checklist for a beginner on Windows PowerShell. It does **not** create cloud accounts, DNS, certificates, SMS, or payments. It does **not** mean KaamDo is production-ready.

Acceptance leftovers stay in `docs/PRE_RELEASE_CHECKLIST.md`. Do not migrate the existing `backend/db.sqlite3` file from this pass.

## What you can do locally now

```powershell
.\venv\Scripts\Activate.ps1
cd backend
python manage.py check
python manage.py runserver
```

The API is `http://127.0.0.1:8000/`. Health: `http://127.0.0.1:8000/healthz`.

Serve the frontend with Live Server or any static file server. Keep `window.KAAMDO_API_BASE` unset on localhost so the browser calls `http://127.0.0.1:8000/api/v1`.

## What a later public host must have (you create these)

1. A unique `SECRET_KEY` (50+ characters). Generate it yourself. Do not paste it into chat.
2. `DEBUG=False`.
3. `ALLOWED_HOSTS` = the API hostname.
4. `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` = the real frontend origin only.
5. PostgreSQL (`DB_ENGINE=postgresql`). Install `psycopg[binary]` first.
6. A process manager that binds `0.0.0.0:$PORT` (Render sets `PORT`). Example:

```text
gunicorn config.wsgi:application --bind 0.0.0.0:%PORT%
```

7. Reverse proxy HTTPS. Application settings do not force HTTPS redirect.
8. Static and media served by the proxy or object storage. Django serves media only when `DEBUG=True`.
9. `backend/media` created before photo uploads.
10. Matching scheduler (see below).

## Render free plan cannot run the matching scheduler

Verified from [Render free instances](https://render.com/docs/free) and [cron jobs](https://render.com/docs/cronjobs):

- Free web services spin down after 15 minutes idle and have no persistent disk.
- Cron jobs have no free instance type (minimum about $1/month per cron service).
- Background workers have no free instance type.

**Status: BLOCKED on a Render free web service.** `run_matching_loop` inside a free web process will sleep and lose local files. Do not create a Render account from this document.

If you later pay for a cron job, the command is:

```text
python manage.py process_daily_matching
```

A one-minute schedule is a reasonable start. This pass does not create that service.

## Local matching (you run this)

```powershell
cd backend
..\venv\Scripts\python.exe manage.py process_daily_matching
```

Or watch it:

```powershell
..\venv\Scripts\python.exe manage.py run_matching_loop --interval 15
```

Windows Task Scheduler can call `process_daily_matching` every minute. Stop the loop when you leave the machine.

## Isolated migrations (safe)

Django tests use a temporary database. To apply migrations on a **copy**:

```powershell
cd backend
..\venv\Scripts\python.exe config\tests\isolated_migrate_runner.py
```

Do not point `KAAMDO_ISOLATED_SQLITE` at `backend\db.sqlite3`.

PostgreSQL migrate is **BLOCKED** until you install Postgres and `psycopg` yourself. This pass does not create a database.

## After an isolated migrate

```powershell
..\venv\Scripts\python.exe manage.py seed_karnataka_locations
```

## Frontend on a public host

Set `window.KAAMDO_API_BASE` to the public API `/api/v1` **before** `config.js` loads, or serve the frontend from the same origin as `/api/v1`. The browser must not call the visitor's localhost.

## Payments and SMS

Leave `KAAMDO_VISIT_PAYMENT=unconfigured`. Payments remain impossible in production.

Leave SMS unconfigured unless you authorize a live test.

## Example host file

`deploy/render.example.yaml` is documentation only. It does not create a Render service.
