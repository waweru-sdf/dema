# Dema: Dr. Feysel Dermatology website

| Folder | What it is |
|---|---|
| `frontend/` | The website: plain HTML, CSS and JS |
| `backend/` | Flask app. It serves `frontend/` and runs bookings, the contact form and the `/admin` dashboard |
| `render.yaml` | One-click deployment settings for Render |

## How the live site works

```
GitHub (waweru-sdf/dema) ──push──> Render web service (free) ──> https://dema-xxxx.onrender.com
                                         │
                                         └── stores data in ──> Neon Postgres (free, permanent)
```

Every `git push` to `main` makes Render rebuild and redeploy the site on its own.

## Run it on your computer

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # set SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD
python wsgi.py              # http://127.0.0.1:5000  and  /admin
```

When `DATABASE_URL` is empty, the app saves data in a local SQLite file.

## Deploying

1. Neon: create a free project and copy its connection string.
2. Render: choose New > Blueprint and select this repo. Render reads `render.yaml`.
3. Fill in `DATABASE_URL`, `ADMIN_USERNAME` and `ADMIN_PASSWORD`, then deploy.

The deployment guide in the chat has the full click-by-click steps.

## Free plan limits

- **Sleeping:** Render's free service sleeps after 15 minutes with no visitors. The next visit takes about a minute to load. Upgrade the service to the Starter plan to keep it awake.
- **Email:** Render's free plan blocks SMTP. To send booking emails, set `BREVO_API_KEY` (Brevo's free plan works over HTTPS).
