# Dr. Feysel Dermatology: Frontend

A cleaned-up, static version of the clinic website. It's plain HTML, CSS and JavaScript, with no build step.

## What changed from the original

- Removed the HTTrack mirror files, unused templates, placeholder text ("Lorem", "Mulching", "Hic solutasetp") and the dead Blog link.
- Rebuilt every page with the same shared header and footer, a working mobile menu, and a dropdown for the services.
- Cut the site from 98 MB to about 4 MB. Photos are resized and compressed, and the 19 MB hero video is now 1.2 MB.
- Dropped Bootstrap, AOS, Swiper and GLightbox. The site now uses one stylesheet (`assets/css/styles.css`) and one small script (`assets/js/main.js`).
- Improved accessibility and SEO with a skip link, alt text, labelled form fields, focus styles, reduced-motion support, meta descriptions and Open Graph tags.
- Rewrote the booking form. Visitors now pick a branch and doctor and see the free time slots for that day. They also get inline validation and a booking reference.
- Both forms now send JSON to the Flask backend instead of the old PHP scripts.
- Gave service pages clean names. The backend redirects the old URLs (`derma.html`, `general.html`, `cosmetic.html`) to the new ones.

## Pages

| File | Page |
|---|---|
| `index.html` | Home |
| `about.html` | About, mission/vision/values, doctors, clinic video |
| `services.html` | Services overview |
| `general-dermatology.html` | General Dermatology |
| `dermatologic-surgery.html` | Dermatologic Surgery |
| `cosmetic-dermatology.html` | Cosmetic Dermatology |
| `appointment.html` | Online booking (calls the API) |
| `contact.html` | Contact form (calls the API) and branch maps |
| `404.html` | Not found page |

## Folder layout

```
assets/
  css/styles.css        All styling. Brand colours are at the top in :root
  js/config.js          API_BASE setting (where the Flask backend lives)
  js/main.js            Menu, scroll effects, gallery lightbox, back-to-top
  js/forms.js           Contact + appointment forms, live time slots
  img/                  Optimised images (doctors/, services/, gallery/)
  video/hero.mp4        Compressed hero video
  icons/                Favicons and app icons
  vendor/bootstrap-icons
```

## Editing in VS Code

1. Open this folder in VS Code.
2. Install the Live Server extension.
3. Right-click `index.html` and choose "Open with Live Server".

The site's content works on its own. The booking and contact forms need the Flask backend running. Without it, the booking form still shows default time slots, and if a request fails it shows the clinic phone numbers.

## Connecting to the backend

- **Same server (recommended):** the Flask backend serves this folder directly. Leave `API_BASE` as `""`.
- **Separate hosting:** set `API_BASE` in `assets/js/config.js` to the backend URL, for example `https://api.drfeyseldermatology.com`. Then add the site's domain to `CORS_ORIGINS` in the backend `.env`.

## Common edits

- **Colours:** change `--green`, `--blue` and `--ink` at the top of `styles.css`.
- **Doctors:** edit the doctor cards in `index.html` and `about.html`, and put photos in `assets/img/doctors/`. Use portrait photos, cropped to 4:5.
- **Phone numbers:** these appear in the header, footer, contact and appointment pages. Use Find in Files (Ctrl+Shift+F) to change them everywhere.
