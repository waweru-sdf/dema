# Dr. Feysel Dermatology: Flask Backend

A Flask app that serves the clinic website and runs the online booking system.

## Features

- Serves the website from `../frontend/` (the repo's frontend folder), with clean URLs (`/about`), a custom 404 page and 301 redirects from the old page names.
- Provides a JSON API for appointment requests, live slot availability and contact messages.
- Checks bookings for conflicts:
  - A doctor can't be double-booked.
  - "Any available doctor" bookings are capped per branch and time slot.
  - Past times, closed days and dates too far ahead are rejected.
- Gives every booking a reference (for example `FD-7K2M9Q`) that patients can use to check its status.
- Includes a staff dashboard at `/admin`:
  - Today, pending and upcoming appointments
  - Search and filters
  - Status updates with optional patient emails
  - Internal notes
  - CSV export
  - Contact message inbox
- Sends optional email notifications over SMTP (Gmail works) to the clinic and the patient.
- Includes basic security protections:
  - Hashed admin passwords
  - CSRF protection on admin forms
  - Login rate limiting
  - A honeypot field and per-IP limits on the public forms
  - Security headers
- Stores data in SQLite by default. Any database SQLAlchemy supports also works, for example PostgreSQL.
- Comes with a pytest test suite.

## Quick start (Windows, VS Code terminal)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then open .env and set SECRET_KEY
flask --app wsgi create-admin   # choose a staff username and password
python wsgi.py
```

Open http://127.0.0.1:5000 for the website and http://127.0.0.1:5000/admin for the dashboard.

On macOS or Linux, use `source .venv/bin/activate` and `cp .env.example .env`.

Run the tests:

```bash
python -m pytest
```

## Project layout

```
backend/
  wsgi.py                 Entry point (python wsgi.py, gunicorn, waitress)
  requirements.txt
  .env.example            All settings with comments
  app/
    __init__.py           App factory, website serving, redirects, CLI commands
    config.py             Settings read from environment variables
    clinic_data.py        Doctors, services, branches (edit here)
    models.py             Appointment, ContactMessage, AdminUser
    services.py           Validation, availability, rate limiter
    api.py                /api/* endpoints
    admin.py              /admin dashboard
    emails.py             Email notifications (sent in the background)
    templates/admin/      Dashboard pages
  tests/test_app.py
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/meta` | Doctors, services, branches, slot times |
| GET | `/api/availability?date=YYYY-MM-DD&branch=bole&doctor=zina-ahmed` | Time slots with `available` flags |
| POST | `/api/appointments` | Create an appointment request |
| GET | `/api/appointments/<reference>?email=...` | Patient checks their request status |
| POST | `/api/contact` | Send a contact message |

Example booking request:

```json
{
  "first_name": "Sara", "last_name": "Tesfaye", "email": "sara@example.com", "phone": "0911 234 567",
  "service": "cosmetic-dermatology", "branch": "bole", "doctor": "zina-ahmed",
  "date": "2026-10-20", "time": "10:00", "notes": "Acne scars"
}
```

The API returns these status codes:

- `201` when the request is created. The body includes the `reference`.
- `400` when validation fails. The body includes `errors` per field.
- `409` when the slot was just taken.
- `429` when the rate limit is hit.

## Configuration

All settings are in `.env`. See `.env.example` for the full list. These are the ones to review before going live:

- `SECRET_KEY`: a long random string.
- `OPEN_WEEKDAYS` and `APPOINTMENT_SLOTS`: set these to the clinic's real working days and hours. The defaults (Mon to Sat, 08:30 to 16:30) are placeholders.
- `BRANCH_SLOT_CAPACITY`: how many "any doctor" patients a branch can see in the same slot.
- `ADMIN_USERNAME` and `ADMIN_PASSWORD`: the first /admin login is created from these on start-up.
- `BREVO_API_KEY`: sends emails over HTTPS. Use this on Render's free plan, which blocks SMTP.
- `MAIL_*`: SMTP settings for local use or paid hosting. For Gmail, turn on 2-step verification, create an App Password, and use `smtp.gmail.com` on port 587.

To change doctors, services or branches, edit `app/clinic_data.py`. The booking form loads them from `/api/meta`, so it updates on its own. The doctor cards on the website are static HTML, so update `index.html` and `about.html` too.

## Updating the website

The website lives in the repo's `frontend/` folder. Flask serves it directly, so edit the files there and refresh the browser. You don't need to restart Flask.

## Deploying

- **Linux:** run `gunicorn -w 1 --threads 4 -b 0.0.0.0:8000 wsgi:app` behind Nginx. Set `BEHIND_PROXY=true`, `SESSION_COOKIE_SECURE=true` and `FLASK_DEBUG=0`.
- **Windows:** run `waitress-serve --port=8000 wsgi:app`.
- **Shared hosting with Python support (cPanel "Setup Python App"):** set the startup file to `wsgi.py` and the entry point to `app`.
- **Several workers or servers:** the built-in rate limiter only counts within one process. Switch to Flask-Limiter with Redis, and use PostgreSQL instead of SQLite.
- **Backups:** back up `instance/clinic.db`, or your database, regularly.
