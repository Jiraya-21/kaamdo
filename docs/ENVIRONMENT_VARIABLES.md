# KaamDo environment variables

This list is for local setup and later staging. It does not authorize a public launch. Do not paste real secrets, API keys, or phone numbers into chat.

Copy `.env.example` to `.env` in the project root. PowerShell:

```powershell
Copy-Item .env.example .env
```

`.env` is gitignored. Leave local values as shown unless you are changing a host you control.

## Required for local DEBUG=True

| Name | Local default | Notes |
| --- | --- | --- |
| `DEBUG` | `True` | Must be `False` before any public process. |
| `SECRET_KEY` | placeholder | Placeholder and `django-insecure-*` keys are refused when `DEBUG=False`. Need at least 50 unique characters. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | When `DEBUG=False`, set the real hostname. `*` is refused. |
| `DB_ENGINE` | `sqlite` | Local only. Staging/production needs `postgresql`. |
| `CORS_ALLOWED_ORIGINS` | local Live Server / loopback ports | When `DEBUG=False`, set the real frontend origin only. localhost is refused. |
| `KAAMDO_OTP_DELIVERY` | `unconfigured` | Leave this until SMS is authorized. |
| `KAAMDO_VISIT_PAYMENT` | `unconfigured` | Payments stay impossible in production. |

## Required when DEBUG=False

| Name | Why |
| --- | --- |
| `SECRET_KEY` | Unique, 50+ characters, not a placeholder. |
| `ALLOWED_HOSTS` | Public API hostname. |
| `CORS_ALLOWED_ORIGINS` | Real frontend origin with `https://` or `http://`. |
| `CSRF_TRUSTED_ORIGINS` | Usually the same origin. Reuses CORS if unset. |
| `DB_ENGINE=postgresql` | SQLite is local-only unless `KAAMDO_ALLOW_SQLITE=true` (emergency only). |
| `DB_NAME`, `DB_USER` | PostgreSQL name and user. Not a file path. |
| `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | From the database you already have. This pass does not create one. |

## Optional

| Name | Default | Notes |
| --- | --- | --- |
| `PORT` | `8000` | Render sets this. Django `runserver` ignores it. Bind `0.0.0.0:$PORT` in the process manager. |
| `STATIC_URL` / `STATIC_ROOT` | `static/` and `backend/staticfiles` | Collect static files for the reverse proxy. |
| `MEDIA_ROOT` | `backend/media` | Worker photos. Production must serve `/media/` itself. |
| `KAAMDO_TRUST_X_FORWARDED_PROTO` | unset | Set only after a reverse proxy you control overwrites `X-Forwarded-Proto`. |
| `KAAMDO_CACHE_BACKEND` | `locmem` | Use `redis` only with more than one worker and a Redis URL. |
| `KAAMDO_MAP_PROVIDER` | `none` | `osm` shows attribution only. Nominatim autocomplete is refused. |
| `KAAMDO_MAP_ATTRIBUTION` | OpenStreetMap credit | Shown only when the provider is `osm`. |
| `KAAMDO_ALLOW_SQLITE` | unset | Emergency local hatch. Not for a public site. |
| Matching `KAAMDO_MATCH_*` | see `.env.example` | Straight-line km only. |

## Must stay off unless authorized

- `SMSMOBILEAPI_API_KEY` and `KAAMDO_OTP_DELIVERY=smsmobileapi`
- `KAAMDO_VISIT_PAYMENT` anything other than `unconfigured`

A public process with `DEBUG=False` refuses the mock payment skip.

## Related docs

See `docs/DEPLOYMENT_GUIDE.md` and `docs/DEPLOYMENT_READINESS.md`. Acceptance scorecards stay in `docs/PRE_RELEASE_CHECKLIST.md`.
