# Website (React + Tailwind)

Design: "Bento" (dark blue hero, tiles, floating navigation). Colours and fonts come from the clinic flyer and live in `tailwind.config.js`.

```
frontend/
  index.html              Page shell. The server fills the two <!--SEO_...--> markers per page.
  vite.config.js          Build settings (output: dist/) and the dev proxy to Flask
  tailwind.config.js      Colours, fonts, shadows
  src/
    main.jsx              Starts React and loads fonts
    App.jsx               Routes and page layout
    index.css             Tailwind plus a few shared classes (btn, pill, card, chip, input)
    lib/api.js            Every request to the backend
    lib/format.js         Dates, phone links, link to the telemedicine service
    context/SiteContext   Settings edited in /admin (telemedicine address, prices, phones)
    hooks/useFetch.js     Small data-loading hook
    components/           Nav, Footer, Hero, DoctorCard, ReviewCard, ReviewForm, ServiceTabs, ...
    pages/                One file per page: Home, Doctors, DoctorProfile, Conditions, ConditionPage,
                          Services, Telemedicine, Reviews, Blog, BlogPost, Contact, Search, NotFound
  public/                 Files copied as they are: logo, doctor and service photos, the in-person
                          booking page (appointment.html) and its styles
  dist/                   The built site. Flask serves this folder.
```

## Work on it

```bash
cd frontend
npm install
# terminal 1:  cd ../backend && python wsgi.py        (API on http://127.0.0.1:5000)
# terminal 2:  npm run dev                             (site on http://localhost:5173)
```

## Publish a change

```bash
npm run build          # rewrites dist/
git add frontend && git commit -m "Update website" && git push
```

Render deploys on every push. The build output is committed on purpose, so the server does not need Node.
