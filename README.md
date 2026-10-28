# Dr. Feysel Dermatology Specialized Clinic: website

| Folder | What it is |
|---|---|
| `frontend/` | The public website: React + Tailwind (source in `src/`, built site in `dist/`) |
| `backend/` | Flask app: website data API, search-engine output, `/admin`, in-person booking API, contact form |
| `render.yaml` | Deployment settings for Render |

## How the pieces fit

```
Visitor ──> Flask (one service) ──> serves frontend/dist  (React site)
                 │                  ├─ /api/site/*   doctors, conditions, reviews, blog, search, settings
                 │                  ├─ /api/*        in-person booking and contact form (unchanged)
                 │                  ├─ /admin        staff pages for content, reviews, appointments
                 │                  └─ /sitemap.xml  /robots.txt  /llms.txt  (search engines and AI assistants)
                 └─ database: SQLite locally, Neon Postgres on Render

"Book Telemedicine" buttons ──> Tena Medicine (separate product: payment, chat, video)
"In-person visit" links      ──> /appointment (this repo's existing booking page, or any address set in Site settings)
```

The website is a showcase: doctors, conditions, reviews and articles. Telemedicine is booked and paid on Tena Medicine.

## Run it on your computer

```bash
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # set SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD
python wsgi.py              # http://127.0.0.1:5000  and  /admin
python -m pytest            # 39 tests
```

Open `/admin`, then **Website content > Overview** for the launch checklist.

## What staff edit in /admin

- **Doctors:** photo, title, branch, years, biography, qualifications, languages, subspecialties, procedures, linked conditions, visibility. A checklist shows what is still missing.
- **Conditions:** summary, key facts, symptoms, causes, treatment steps, FAQs, doctors, and "medically reviewed by".
- **Reviews:** patients submit on the site. Nothing appears until staff approve it. Reviews with consent missing or a phone number or email are blocked.
- **Blog:** articles with cover picture, author and publish date.
- **Site settings:** telemedicine address, in-person booking address, displayed prices, phones, email, public website address.

## Search engines and AI assistants

Every page is delivered with its own title, description, canonical address, schema.org structured data (clinic, physicians with credentials, conditions, FAQs, articles, breadcrumbs) and the page text as plain HTML. `/sitemap.xml`, `/robots.txt` and `/llms.txt` are generated from the database.

## Deploying (Render)

Same as before: Neon for the database, Render blueprint from `render.yaml`. After changing the React site, run `npm run build` in `frontend/` and commit `frontend/dist`.


## Carried over from the live site (blog v2 + admin update)

* **Blog**: /admin/blog with the full editor (cover upload, bold/italic, links, headings, bullets, numbered lists, quotes, pictures with captions, YouTube, live preview). Table `blog_posts` is the same one the live site uses, so existing articles keep working.
* **Gallery** (/admin/gallery) shows on the About page. **Site pictures** (/admin/images) replace any built-in picture.
* **Doctors** edited in the old admin are imported once into the new profiles (name, role, photo).
* **In-person visit** is now a page of this site, `/appointment`, using the same booking API and admin Appointments list.
