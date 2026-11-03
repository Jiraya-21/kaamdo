#!/usr/bin/env bash
# Render start command for KaamDo (API + frontend from one web service).
set -euo pipefail
cd backend
python manage.py migrate --noinput
python manage.py seed_karnataka_locations
python manage.py seed_service_categories
python manage.py seed_first_area_demo
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
