# KaamDo optional Docker PostgreSQL

This is a **local staging practice** database. It is not a public deployment. It does not start Django, send SMS, collect payments, or change DNS.

`backend/db.sqlite3` is the existing local development file. Docker does **not** mount or replace that file. Data for Postgres lives in the named volume `kaamdo_pgdata`.

## 1. Install Docker Desktop (required for the container)

On this machine, `docker` was **not** on PATH and Docker Desktop was **not** found under `C:\Program Files\Docker`. Until it is installed, `docker compose` commands will fail.

1. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/).
2. Enable the WSL 2 backend if the installer asks.
3. Start Docker Desktop and wait until it is running.
4. Open a **new** PowerShell window and confirm:

```powershell
docker version
docker compose version
```

Both should print a version and exit 0.

## 2. Credentials (server-only `.env`)

`.env` is gitignored. `.env.example` is a template and must **not** hold real secrets.

```powershell
Copy-Item .env.example .env
```

Keep `DB_ENGINE=sqlite` in `.env` while you use the current local app.

To run the optional Postgres container, you may set these in `.env` (or accept the local-only compose defaults):

```
POSTGRES_DB=kaamdo_staging
POSTGRES_USER=kaamdo
POSTGRES_PASSWORD=kaamdo_dev_only_change_me
POSTGRES_PORT=5433
```

The compose default password is for **this machine only**. Put a unique password in `.env` if anyone else can reach the port. Do not paste that password into chat.

Django still uses SQLite until you also set `DB_ENGINE=postgresql` (section 4). Starting the container does not switch Django by itself.

## 3. Start, health, stop (data is kept)

From the project root `Kaamdo.1`:

```powershell
docker compose up -d postgres
docker compose ps
docker compose exec postgres pg_isready -U kaamdo -d kaamdo_staging
```

Healthy output includes `accepting connections`. The host port is **5433** by default so a local Postgres on 5432 is not required.

Stop containers and **keep** the volume:

```powershell
docker compose down
```

Start again later with `docker compose up -d postgres`. The `kaamdo_staging` database is still there.

Delete the volume only if you intend to wipe that staging database:

```powershell
docker compose down -v
```

Do not run `down -v` against a database you care about.

## 4. Point Django at Postgres (explicit)

Install the driver in the project venv (not done by default):

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install "psycopg[binary]"
```

In `.env` only, set:

```
DB_ENGINE=postgresql
DB_NAME=kaamdo_staging
DB_USER=kaamdo
DB_PASSWORD=kaamdo_dev_only_change_me
DB_HOST=127.0.0.1
DB_PORT=5433
```

`DB_NAME` must be a Postgres database name, never `backend/db.sqlite3`. Unknown `DB_ENGINE` values are refused. While `DB_ENGINE=sqlite`, `DB_NAME` is ignored.

Leave `DEBUG=True` for local practice. `DEBUG=False` still requires a unique `SECRET_KEY`, explicit `ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS`. Do not invent a public hostname here.

Keep:

```
KAAMDO_OTP_DELIVERY=unconfigured
KAAMDO_VISIT_PAYMENT=unconfigured
```

Check without migrating:

```powershell
cd backend
python manage.py check
```

Create tables on **this empty Docker database only** when you choose to (not automatic):

```powershell
python manage.py migrate
```

Do not run that command while `DB_ENGINE=sqlite` unless you intend to change `backend/db.sqlite3`.

Switch back to the existing local app by setting `DB_ENGINE=sqlite` and restarting `runserver`. The SQLite file is unchanged by the Docker volume.

## 5. Backup

Dump the Docker database (not SQLite):

```powershell
docker compose exec -T postgres pg_dump -U kaamdo kaamdo_staging > kaamdo_staging.dump.sql
```

Restore only into Postgres, never into `backend/db.sqlite3`:

```powershell
Get-Content kaamdo_staging.dump.sql | docker compose exec -T postgres psql -U kaamdo -d kaamdo_staging
```

## 6. Redis (optional, not started by default)

OTP IP limits default to LocMemCache (per process). Multi-worker OTP rate limiting needs a shared cache.

```powershell
docker compose --profile cache up -d
python -m pip install "redis>=5,<7"
```

In `.env`:

```
KAAMDO_CACHE_BACKEND=redis
KAAMDO_CACHE_URL=redis://127.0.0.1:6379/1
```

`docker compose up -d` without `--profile cache` does not start Redis.

## 7. What this setup does not do

- It does not deploy the site or change DNS.
- It does not enable SMSMobileAPI or payments.
- It does not migrate a production database.
- It does not copy rows from `backend/db.sqlite3` into Postgres.
- It does not wrap Django in a production container.
