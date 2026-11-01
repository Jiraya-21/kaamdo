# KaamDo - Local Work, Services & Agricultural Equipment Marketplace

KaamDo is a community-driven marketplace connecting local workers, customers, employers, farmers, and equipment owners. The platform empowers local communities by facilitating service discovery, flexible pricing agreements, and agricultural machinery rentals.

---

## 1. Project Overview & Architecture

KaamDo is structured with a decoupled, modular architecture designed for simplicity, maintainability, and scalability:

- **Frontend**: Lightweight, high-performance HTML5, CSS3, and Vanilla JavaScript (ES6). No frontend build frameworks or heavy toolchains required.
- **Backend**: Headless Python/Django application exposing clean RESTful APIs via Django REST Framework (DRF).
- **Database**: SQLite for local development (`backend/db.sqlite3`). Settings can point at PostgreSQL later; that driver is not installed by default.
- **API Communication**: Asynchronous `fetch` calls through a centralized frontend API client layer (`frontend/assets/js/api/apiClient.js`).

---

## 2. Core Modules

1. **Accounts & Authentication**: Multi-role user registration and login (Customer, Worker, Employer, Farmer, Equipment Owner).
2. **Worker Profiles**: Skills, rates (hourly/daily), experience, identity verification, location coordinates, and service radius.
3. **Worker Discovery**: Radius-based search (default 20 km radius, adjustable), skill filtering, and availability sorting.
4. **Jobs & Job Requests**: Direct hiring, public job postings, application submissions, and job lifecycle tracking.
5. **Price Agreement**: Initial price agreement, formal revision requests with reason tracking, and acceptance/rejection flow.
6. **Agricultural Equipment Rental**: Equipment inventory (tractors, harvesters, tillers, etc.), rental requests, and availability management.
7. **Ratings & Reviews**: Verified feedback system linked exclusively to completed jobs and rentals to prevent fraudulent reviews.
8. **Notifications**: In-app notifications with architectural foundation for SMS dispatch.
9. **Administration**: Moderation interface for equipment approvals, identity verification, and dispute resolution.

---

## 3. Directory Layout

```text
Kaamdo.1/
├── docs/                 # Architectural blueprints and guides
├── frontend/             # Client-side user interface (HTML/CSS/JS)
│   ├── assets/           # Stylesheets, JS modules, utilities, and images
│   ├── pages/            # Application views (auth, workers, jobs, equipment, dashboard)
│   └── index.html        # KaamDo homepage
├── backend/              # Server-side Django REST application
│   ├── config/           # Master Django configuration (settings, master urls)
│   ├── accounts/         # User accounts and roles
│   ├── workers/          # Worker profiles and geolocation discovery
│   ├── jobs/             # Job postings, requests, and price agreements
│   ├── equipment/        # Agricultural equipment listings and rentals
│   ├── reviews/          # Verified ratings and reviews
│   ├── notifications/    # In-app alerts and notifications
│   └── reliability/      # Reliability records
├── requirements.txt      # Python dependencies (Python 3.14)
├── .env.example          # Safe environment variable template
├── .gitignore
└── README.md             # This documentation
```

---

## 4. Backend environment (Windows PowerShell)

The virtual environment is `venv` in the project root and uses **Python 3.14.8**. Django 6.0 does not run on Python 3.15.

From the project root:

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd backend
python manage.py check
python manage.py runserver
```

The API is served at `http://127.0.0.1:8000/`. Full setup notes are in [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md).

---

## 5. Documentation Index

For detailed guidelines, see the files inside the `docs/` folder:
- [Architecture Blueprint](file:///docs/ARCHITECTURE.md)
- [REST API Specifications](file:///docs/API_DESIGN.md)
- [Database Schema Design](file:///docs/DATABASE_DESIGN.md)
- [Developer Setup Guide](file:///docs/SETUP_GUIDE.md)
- [Testing Strategy & Guide](file:///docs/TESTING_GUIDE.md)
- [Environment variables](docs/ENVIRONMENT_VARIABLES.md)
- [Deployment guide (not a launch)](docs/DEPLOYMENT_GUIDE.md)
- [Deployment readiness](docs/DEPLOYMENT_READINESS.md)
- [Karnataka locations](docs/KARNATAKA_LOCATIONS.md)
- [Pilot test plan](docs/PILOT_TEST_PLAN.md)
