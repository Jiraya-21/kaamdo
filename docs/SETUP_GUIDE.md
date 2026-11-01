# KaamDo Setup & Installation Guide

This guide walks you through setting up your local development environment for KaamDo.

---

## 1. Prerequisites

- **Python 3.14**, latest micro release (this project uses 3.14.8). Django 6.0 supports Python 3.12, 3.13, and 3.14. It does not support Python 3.15.
- Check the installed runtimes with `py -0p`. The project virtual environment must be created with `py -3.14`, even if `py` defaults to 3.15.
- **Visual Studio Code**, with the Python extension and Live Server if you want to serve the frontend.

The backend dependencies in `requirements.txt` are Django 6.0.9, Django REST Framework 3.18.3, django-cors-headers 4.9.0, and python-dotenv 1.2.4. Local development uses SQLite (`backend/db.sqlite3`). PostgreSQL is optional and is not installed with these requirements.

---

## 2. Setting Up the Backend

Open PowerShell in the project root (`Kaamdo.1`).

### Step 1: Activate the virtual environment

The project virtual environment is `venv` in the project root, created with Python 3.14.

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks the script, run this once in that window and try again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

To recreate `venv` from scratch:

```powershell
py -3.14 -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 2: Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### Step 3: Configure environment variables

```powershell
Copy-Item .env.example .env
```

Leave `DB_ENGINE=sqlite`. No PostgreSQL server or database driver is required for local development.

### Step 4: Check the Django configuration

```powershell
cd backend
python manage.py check
```

`python manage.py check` confirms the settings load. It does not apply migrations.

### Step 5: Start the Django development server

From the `backend` directory, with `venv` activated:

```powershell
python manage.py runserver
```

The development server listens at `http://127.0.0.1:8000/`. The admin site is `http://127.0.0.1:8000/admin/`.

`backend/db.sqlite3` already has the existing migrations applied, including `accounts.0001_initial`. This setup did not create an admin user and did not run `migrate`. Do not delete the database file.

---

## 3. Running the Frontend

The frontend is built with vanilla web technologies, requiring no Node.js or build steps.

### Option A: Using VS Code Live Server (Recommended)
1. In Visual Studio Code, right-click on `frontend/index.html`.
2. Select **"Open with Live Server"**.
3. Your browser will open the application at `http://127.0.0.1:5500/frontend/index.html`.

### Option B: Using Python's Built-in HTTP Server
From the project root:
```powershell
python -m http.server 5500
```
Then navigate in your browser to `http://localhost:5500/frontend/`.

---

## 4. Connecting Frontend to Backend

In `frontend/assets/js/config.js`, the default API base URL is set to:
```javascript
const CONFIG = {
  API_BASE_URL: 'http://127.0.0.1:8000/api/v1',
  DEFAULT_SEARCH_RADIUS_KM: 20
};
```
Django's `django-cors-headers` is pre-configured for local DEBUG origins including Live Server (`http://127.0.0.1:5500`) and Python's `http.server` from `frontend/` (`http://127.0.0.1:8768`). `DEBUG=False` still requires an explicit `CORS_ALLOWED_ORIGINS` value.
