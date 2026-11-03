# KaamDo completion status

Updated 3 November 2026 — deployment-ready first phase pushed to GitHub. Living notes: `docs/KAAMDO_PROJECT_CONTEXT.md`.

## Verdict

| Target | Status |
| --- | --- |
| Local development (127.0.0.1) | **PASS** |
| GitHub backup / source | **PASS** (pushed to `origin/main`) |
| Controlled staging (Render / host) | **READY TO START** — create host + env yourself |
| Public production | **NOT LIVE** until host env is set with `DEBUG=False` |

## First-phase product (this push)

- **Book**: mobile verify → pay inspection fee → workers offered
- **Track (account)**: My requests = existing status only (or “No request”)
- **Track (guest)**: same verified mobile + OTP → all requests for that number
- **Roles**: customer shows nothing; providers show section tags (e.g. Daily services · Electrician)
- **Copy**: deployment-style OTP / pay / accept-decline messages (no TEST MODE / practice banners in UI)
- **Brand / photos**: logo + real JPEGs; Bidar soft testing notice; districts open

## Production safety (already in code)

- `DEBUG=False` forces `KAAMDO_VISIT_PAYMENT=unconfigured` and OTP delivery unconfigured unless you set SMS
- `.env` is gitignored — only `.env.example` is tracked
- Public frontend uses same-origin `/api/v1` unless `window.KAAMDO_API_BASE` is set

## What you must set on the host (not in git)

1. `DEBUG=False`
2. Long unique `SECRET_KEY` (50+ chars; not `django-insecure-*`)
3. `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`
4. PostgreSQL (`DB_ENGINE=postgresql` + credentials)
5. `KAAMDO_VISIT_PAYMENT=unconfigured`
6. SMS only if you intentionally enable SMSMobileAPI for live OTP
7. Run migrations + seed locations; schedule `process_daily_matching` (paid cron on Render)

See `docs/DEPLOYMENT_GUIDE.md` and `deploy/render.example.yaml`.

## Remaining product gaps (not blockers for staging)

1. Real money payments (Razorpay live) not wired — mock/local only while DEBUG
2. Reviews app still pending
3. Free Render cannot run a reliable matching cron — use paid cron or external scheduler

## Start locally (Windows)

```powershell
cd "D:\project  kaam-do\Kaamdo.1"
.\venv\Scripts\Activate.ps1
cd backend
python manage.py runserver
```

Serve `frontend/` with Live Server. Keep local `.env` with `DEBUG=True` and optional `KAAMDO_VISIT_PAYMENT=mock_demo`.
