# KaamDo pilot test plan (local and later staging)

This is a human checklist. It does not create accounts, send SMS, or take money. Stop when a step needs a secret or a cloud resource.

## Local (you can do these on 127.0.0.1)

1. Start the API: `cd backend` then `python manage.py runserver`.
2. Open `http://127.0.0.1:8000/healthz` — expect `{"status":"ok"}`.
3. Open the homepage and the four marketplace sections: Daily Services, Jobs, Equipment, Farm hiring.
4. Confirm district filters are official dropdowns (Bengaluru South is present; a 30-district Ramanagara-only list is not).
5. On the guest request page, choose district and taluk, type a locality, use **this phone location**. Confirm the review screen does not show raw map numbers.
6. Confirm cards show place names, not latitude/longitude.
7. If you already have a signed-in account, walk provider photo, job close, and matching. If you do not, stop. Do not invent a production admin here.
8. Run matching only on a copy, or with `process_daily_matching` while you watch it.

## Later staging (blocked until you create resources)

- `DEBUG=False` with a secret you generate yourself.
- PostgreSQL you provision.
- Frontend origin set in CORS/CSRF.
- Paid scheduler if the host is Render.
- One authorized SMS handset test, if you want SMS.
- Payments stay impossible.

## Do not test

- Live SMS from this document.
- Real cards or UPI.
- Migrating the existing `backend/db.sqlite3` unless you choose to.
- Public DNS or a Render create-service flow from this chat.

## Related

`docs/DEPLOYMENT_READINESS.md` and the sibling `docs/PRE_RELEASE_CHECKLIST.md`.
