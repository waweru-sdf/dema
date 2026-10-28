"""Search-engine and AI-assistant friendly output.

The website is a React app, but every public page is also delivered with:
  * a proper <title>, description, canonical address and social tags,
  * schema.org JSON-LD (clinic, physicians, conditions, articles, breadcrumbs),
  * the page's real content as plain HTML inside <div id="root"> (React replaces it once it loads),
so crawlers and AI assistants that do not run JavaScript still read doctors, credentials and conditions as text.

Also served here: /sitemap.xml, /robots.txt, /llms.txt and uploaded photos at /media/....
"""
import json
import re
from functools import lru_cache
from html import escape
from pathlib import Path

from flask import Blueprint, Response, abort, current_app, request

from .clinic_data import BRANCHES
from .models import BlogPost as Post
from .content_models import (Condition, Doctor, Review, get_settings, split_commas, split_lines)
from .site_api import published_doctors, review_summary
from .site_services import SERVICE_GROUPS

seo = Blueprint("seo", __name__)

CLINIC = "Dr. Feysel Dermatology Specialized Clinic"
TAGLINE = "Look good, feel good."
BRANCH_ADDRESS = {
    "bole": "Bole, near Bole Medhanialem, Addis Ababa",
    "zenebework": "Zenebework, across from Alert Hospital, Addis Ababa",
}

# ---------------------------------------------------------------- helpers


def base_url():
    configured = (get_settings().get("site_url") or "").strip().rstrip("/")
    return configured or request.url_root.rstrip("/")


def absolute(path):
    if not path:
        return None
    return path if path.startswith("http") else base_url() + path


def e(x):
    return escape(str(x or ""), quote=True)


def jsonld(*items):
    return "".join('<script type="application/ld+json">' + json.dumps(i, ensure_ascii=False).replace("</", "<\\/") + "</script>"
                   for i in items if i)


def breadcrumbs(*crumbs):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": absolute(p)} for i, (n, p) in enumerate(crumbs)]}


def clinic_ld():
    s = get_settings()
    return {
        "@context": "https://schema.org", "@type": ["MedicalClinic", "LocalBusiness"], "@id": absolute("/#clinic"),
        "name": CLINIC, "url": absolute("/"), "logo": absolute("/assets/img/logo.png"), "image": absolute("/assets/img/hero-poster.jpg"),
        "slogan": TAGLINE, "email": s["email"], "telephone": split_commas(s["phones"])[:1] or None,
        "medicalSpecialty": "Dermatologic", "areaServed": "Addis Ababa, Ethiopia",
        "availableService": [{"@type": "MedicalProcedure", "name": i} for g in SERVICE_GROUPS for i in g["items"]],
        "department": [{"@type": "MedicalClinic", "name": b["name"], "telephone": b["phone"],
                        "address": {"@type": "PostalAddress", "streetAddress": BRANCH_ADDRESS.get(b["slug"], ""),
                                    "addressLocality": "Addis Ababa", "addressCountry": "ET"}} for b in BRANCHES],
    }


def physician_ld(d):
    data = d.to_dict(full=True)
    out = {
        "@context": "https://schema.org", "@type": "Physician", "@id": absolute(f"/doctors/{d.slug}#physician"),
        "name": d.name, "url": absolute(f"/doctors/{d.slug}"), "image": absolute(d.photo_url),
        "jobTitle": d.title, "medicalSpecialty": "Dermatologic", "description": d.bio or None,
        "knowsLanguage": data["languages"] or None, "knowsAbout": ([c["name"] for c in data["conditions"]] + data["subspecialties"]) or None,
        "availableService": [{"@type": "MedicalProcedure", "name": p} for p in data["procedures"]] or None,
        "worksFor": {"@type": "MedicalClinic", "name": CLINIC, "url": absolute("/")},
        "hasCredential": [{"@type": "EducationalOccupationalCredential", "name": q["label"], "description": q["detail"] or None}
                          for q in data["qualifications"]] or None,
        "identifier": d.registration_no or None,
    }
    return {k: v for k, v in out.items() if v}


def condition_ld(c):
    data = c.to_dict(full=True)
    page = {
        "@context": "https://schema.org", "@type": "MedicalWebPage", "name": f"{c.name}: symptoms, causes and treatment",
        "url": absolute(f"/conditions/{c.slug}"), "description": c.summary, "lastReviewed": data["reviewed_on"],
        "dateModified": data["updated_at"], "about": {
            "@type": "MedicalCondition", "name": c.name, "description": c.summary,
            "signOrSymptom": [{"@type": "MedicalSymptom", "name": s} for s in data["symptoms"]],
            "possibleTreatment": [{"@type": "MedicalTherapy", "name": s["label"], "description": s["detail"]} for s in data["steps"]],
        },
        "mainContentOfPage": None,
        "reviewedBy": ({"@type": "Physician", "name": c.reviewed_by.name, "url": absolute(f"/doctors/{c.reviewed_by.slug}")}
                       if c.reviewed_by and c.reviewed_on else None),
    }
    faq = None
    if data["faqs"]:
        faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["label"], "acceptedAnswer": {"@type": "Answer", "text": f["detail"]}} for f in data["faqs"]]}
    return [{k: v for k, v in page.items() if v}, faq]


def post_ld(p):
    return {"@context": "https://schema.org", "@type": "BlogPosting", "headline": p.title, "description": p.excerpt,
            "image": absolute(p.cover_url) if p.cover_url else None,
            "datePublished": (p.published_at or p.created_at).date().isoformat(),
            "dateModified": (p.updated_at or p.published_at or p.created_at).date().isoformat(), "url": absolute(f"/blog/{p.slug}"),
            "author": {"@type": "MedicalClinic", "name": CLINIC},
            "publisher": {"@type": "MedicalClinic", "name": CLINIC}}


def reviews_ld():
    summ = review_summary()
    real = Review.query.filter_by(status="approved", is_sample=False).count()
    if not real or not summ["average"]:
        return None  # never publish ratings markup for sample content
    return {"@context": "https://schema.org", "@type": "MedicalClinic", "name": CLINIC, "url": absolute("/"),
            "aggregateRating": {"@type": "AggregateRating", "ratingValue": summ["average"], "reviewCount": summ["count"]}}


# ---------------------------------------------------------------- plain-HTML bodies (for crawlers without JavaScript)

def ul(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else ""


def link(path, text):
    return f'<a href="{e(path)}">{e(text)}</a>'


def nav_html():
    return ("<nav>" + " ".join(link(p, t) for p, t in [("/", "Home"), ("/doctors", "Doctors"), ("/conditions", "Conditions"),
            ("/services", "Services"), ("/telemedicine", "Telemedicine"), ("/reviews", "Reviews"), ("/blog", "Blog"),
            ("/contact", "Contact")]) + "</nav>")


def footer_html():
    s = get_settings()
    return (f"<footer><p>{e(CLINIC)}. {e(TAGLINE)}</p><p>Email: {e(s['email'])}. Phone: {e(s['phones'])}.</p>"
            + "".join(f"<p>{e(b['name'])}: {e(BRANCH_ADDRESS.get(b['slug'], ''))}. Phone {e(b['phone'])}.</p>" for b in BRANCHES)
            + "<p>Telemedicine is provided with Tena Medicine. It does not replace emergency care.</p></footer>")


def page(h1, intro, *sections):
    return f"{nav_html()}<main><h1>{e(h1)}</h1><p>{e(intro)}</p>{''.join(sections)}</main>{footer_html()}"


def doctor_list_html(docs):
    return ul([f'{link("/doctors/" + d.slug, d.name)}: {e(d.title)}' for d in docs])


def render_home():
    docs = published_doctors().all()
    conds = Condition.query.filter_by(published=True).order_by(Condition.sort_order).all()
    body = page(f"{CLINIC}, Addis Ababa", "Care for skin, hair and nails in Addis Ababa, in the clinic or online through telemedicine.",
                "<h2>Conditions we treat</h2>", ul([link("/conditions/" + c.slug, c.name) for c in conds]),
                "<h2>Our doctors</h2>", doctor_list_html(docs),
                "<h2>Services</h2>", ul([f"{e(g['title'])}: {e(', '.join(g['items']))}" for g in SERVICE_GROUPS]),
                "<h2>Telemedicine</h2><p>Chat with a doctor or have a video consultation. Online visits are booked and paid on Tena Medicine. "
                "In-person visits are booked separately.</p>")
    return ("Dr. Feysel Dermatology Specialized Clinic | Skin, hair and nail care in Addis Ababa",
            "Board-certified dermatologists in Addis Ababa at Bole and Zenebework. Meet our doctors, learn about skin conditions and book a telemedicine consultation.",
            body, [clinic_ld(), reviews_ld()], "/")


def render_doctors():
    docs = published_doctors().all()
    return ("Our dermatologists | " + CLINIC, f"Meet the {len(docs)} dermatologists at {CLINIC}: qualifications, languages, subspecialties and conditions treated.",
            page("Our dermatologists", "Profiles of our doctors with qualifications, languages and the conditions they treat.", doctor_list_html(docs)),
            [breadcrumbs(("Home", "/"), ("Doctors", "/doctors")), {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": absolute(f"/doctors/{d.slug}"), "name": d.name} for i, d in enumerate(docs)]}],
            "/doctors")


def render_doctor(slug):
    d = Doctor.query.filter_by(slug=slug, published=True).first()
    if not d:
        return None
    data = d.to_dict(full=True)
    rows = []
    if data["branch_name"]:
        rows.append(f"Branch: {e(data['branch_name'])}")
    if d.years_experience is not None:
        rows.append(f"Experience: {d.years_experience} years")
    if data["languages"]:
        rows.append("Languages: " + e(", ".join(data["languages"])))
    if data["registration_no"]:
        rows.append("Registration number: " + e(data["registration_no"]))
    secs = [ul(rows)]
    if d.bio:
        secs.append(f"<h2>About</h2><p>{e(d.bio)}</p>")
    if data["qualifications"]:
        secs.append("<h2>Qualifications and certifications</h2>" + ul([f"{e(q['label'])}: {e(q['detail'])}" for q in data["qualifications"]]))
    if data["subspecialties"]:
        secs.append("<h2>Subspecialties</h2>" + ul([e(s) for s in data["subspecialties"]]))
    if data["conditions"]:
        secs.append("<h2>Conditions treated</h2>" + ul([link("/conditions/" + c["slug"], c["name"]) for c in data["conditions"]]))
    if data["procedures"]:
        secs.append("<h2>Procedures</h2>" + ul([e(p) for p in data["procedures"]]))
    desc = d.bio[:155] if d.bio else f"{d.name}, {d.title} at {CLINIC}."
    return (f"{d.name}, {d.title} | {CLINIC}", desc, page(d.name, d.title, *secs),
            [physician_ld(d), breadcrumbs(("Home", "/"), ("Doctors", "/doctors"), (d.name, f"/doctors/{d.slug}"))], f"/doctors/{d.slug}", d.photo_url)


def render_conditions():
    conds = Condition.query.filter_by(published=True).order_by(Condition.sort_order).all()
    return ("Skin, hair and nail conditions | " + CLINIC, "Patient guides to acne, vitiligo, psoriasis, skin cancer screening, hair loss and eczema, with the doctors who treat them.",
            page("Conditions we treat", "Plain-language guides, each linked to the doctors who treat the condition.",
                 ul([f'{link("/conditions/" + c.slug, c.name)}: {e(c.summary)}' for c in conds])),
            [breadcrumbs(("Home", "/"), ("Conditions", "/conditions"))], "/conditions")


def render_condition(slug):
    c = Condition.query.filter_by(slug=slug, published=True).first()
    if not c:
        return None
    data = c.to_dict(full=True)
    secs = []
    if data["facts"]:
        secs.append(ul([f"{e(f['label'])}: {e(f['detail'])}" for f in data["facts"]]))
    if data["symptoms"]:
        secs.append("<h2>Symptoms</h2>" + ul([e(s) for s in data["symptoms"]]))
    if data["causes"]:
        secs.append(f"<h2>Causes and risk factors</h2><p>{e(data['causes'])}</p>")
    if data["steps"]:
        secs.append("<h2>How we approach treatment</h2>" + ul([f"<strong>{e(s['label'])}</strong>: {e(s['detail'])}" for s in data["steps"]]))
    docs = data["doctors"]
    secs.append(f"<h2>Doctors who treat {e(c.name.lower())}</h2>" + ul([link("/doctors/" + d["slug"], d["name"]) for d in docs]))
    if data["faqs"]:
        secs.append("<h2>Frequently asked questions</h2>" + "".join(f"<h3>{e(f['label'])}</h3><p>{e(f['detail'])}</p>" for f in data["faqs"]))
    if c.reviewed_by and c.reviewed_on:
        secs.append(f"<p>Medically reviewed by {e(c.reviewed_by.name)} on {c.reviewed_on.isoformat()}.</p>")
    return (f"{c.name}: symptoms, causes and treatment | {CLINIC}", c.summary[:158], page(c.name, c.summary, *secs),
            [*condition_ld(c), breadcrumbs(("Home", "/"), ("Conditions", "/conditions"), (c.name, f"/conditions/{c.slug}"))],
            f"/conditions/{c.slug}", ("/assets/img/" + c.image) if c.image else None)


def render_services():
    return ("Services | " + CLINIC, "Hair and scalp, aesthetic dermatology, dermatosurgery, laser treatments and PRP at our Bole and Zenebework branches.",
            page("Services", "Treatments and procedures offered at the clinic.",
                 *[f"<h2>{e(g['title'])}</h2>" + ul([e(i) for i in g["items"]]) for g in SERVICE_GROUPS]),
            [breadcrumbs(("Home", "/"), ("Services", "/services"))], "/services")


def render_telemedicine():
    s = get_settings()
    return ("Book a telemedicine consultation | " + CLINIC, "See a dermatologist online. Choose chat or video consultation, pay securely and get confirmation by SMS and email.",
            page("Telemedicine", "See one of our dermatologists online.",
                 "<h2>Plans</h2>" + ul([f"Chat with a doctor: {e(s['price_chat'])} birr. Messages and photos for {e(s['chat_days'])} days.",
                                       f"Video consultation + chat: {e(s['price_video_chat'])} birr. A video visit, then {e(s['chat_days'])} days of chat."]),
                 "<h2>How it works</h2>" + ul(["Choose a doctor and a plan.", "Pay securely online.",
                                              "You receive confirmation by SMS and email, and chat opens straight away.",
                                              "For a video visit, the room opens shortly before your appointment."]),
                 "<p>Online visits are booked and paid on Tena Medicine. For an in-person visit, use the in-person booking link.</p>"),
            [breadcrumbs(("Home", "/"), ("Telemedicine", "/telemedicine"))], "/telemedicine")


def render_reviews():
    rv = Review.query.filter_by(status="approved").order_by(Review.created_at.desc()).limit(24).all()
    lines = [f"{'Sample review: ' if r.is_sample else ''}{'★' * r.rating} {e(r.body)} ({e(r.reviewer_label)})" for r in rv]
    return ("Patient reviews | " + CLINIC, "Patient reviews you can browse by condition, symptom and treatment. Published with consent, without full names.",
            page("Patient reviews", "Reviews are published with patient consent and never include full names or private medical details.", ul(lines)),
            [breadcrumbs(("Home", "/"), ("Reviews", "/reviews")), reviews_ld()], "/reviews")


def render_blog():
    ps = Post.query.filter_by(published=True).order_by(Post.published_at.desc(), Post.id.desc()).all()
    return ("Blog | " + CLINIC, "Skin, hair and nail care explained plainly by our dermatologists.",
            page("Blog", "Skin, hair and nail care explained by our dermatologists.",
                 ul([f'{link("/blog/" + p.slug, p.title)}: {e(p.excerpt)}' for p in ps])),
            [breadcrumbs(("Home", "/"), ("Blog", "/blog"))], "/blog")


SAFE_URL = re.compile(r"^(https?://|/(?!/)|#|mailto:|tel:)", re.I)
INLINE_RE = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*|\[([^\]]+)\]\(([^)\s]+)\)")


def inline_html(text):
    out, last = [], 0
    for m in INLINE_RE.finditer(text):
        out.append(e(text[last:m.start()]))
        if m.group(1) is not None:
            out.append(f"<strong>{e(m.group(1))}</strong>")
        elif m.group(2) is not None:
            out.append(f"<em>{e(m.group(2))}</em>")
        elif SAFE_URL.match(m.group(4)):
            out.append(f'<a href="{e(m.group(4))}">{e(m.group(3))}</a>')
        else:
            out.append(e(m.group(3)))
        last = m.end()
    out.append(e(text[last:]))
    return "".join(out)


def body_to_html(text):
    """Article text (see the writing guide in /admin/blog) as plain, escaped HTML for crawlers without JavaScript."""
    out = []
    for raw in re.split(r"\n{2,}", (text or "").replace("\r\n", "\n").strip()):
        rows = [r.strip() for r in raw.strip().split("\n") if r.strip()]
        if not rows:
            continue
        first = rows[0]
        m = None
        if len(rows) == 1 and re.fullmatch(r"---+", first):
            out.append("<hr>")
        elif len(rows) == 1 and (m := re.fullmatch(r"(#{2,3}) (.+)", first)):
            out.append(f"<h{len(m.group(1))}>{inline_html(m.group(2))}</h{len(m.group(1))}>")
        elif len(rows) == 1 and (m := re.fullmatch(r"!\[([^\]]*)\]\(([^)\s]+)\)", first)):
            if SAFE_URL.match(m.group(2)):
                out.append(f'<figure><img src="{e(m.group(2))}" alt="{e(m.group(1))}"><figcaption>{e(m.group(1))}</figcaption></figure>')
        elif len(rows) == 1 and first.startswith("@[youtube]"):
            continue
        elif all(re.match(r"[-*] ", r) for r in rows):
            out.append(ul([inline_html(r[2:]) for r in rows]))
        elif all(re.match(r"\d+[.)] ", r) for r in rows):
            out.append("<ol>" + "".join(f"<li>{inline_html(re.sub(r'^\d+[.)] ', '', r))}</li>" for r in rows) + "</ol>")
        elif all(r.startswith(">") for r in rows):
            out.append("<blockquote>" + "<br>".join(inline_html(r.lstrip("> ")) for r in rows) + "</blockquote>")
        else:
            out.append("<p>" + "<br>".join(inline_html(r) for r in rows) + "</p>")
    return "".join(out)


def render_post(slug):
    p = Post.query.filter_by(slug=slug, published=True).first()
    if not p:
        return None
    return (f"{p.title} | {CLINIC}", p.excerpt[:158], page(p.title, p.excerpt, body_to_html(p.body)),
            [post_ld(p), breadcrumbs(("Home", "/"), ("Blog", "/blog"), (p.title, f"/blog/{p.slug}"))], f"/blog/{p.slug}",
            p.cover_url)


def render_contact():
    return ("Contact and locations | " + CLINIC, "Phone numbers, email and addresses of our Bole and Zenebework branches in Addis Ababa.",
            page("Contact us", "Call, write or visit us."), [breadcrumbs(("Home", "/"), ("Contact", "/contact"))], "/contact")


def render_about():
    return ("About us | " + CLINIC, "Patient-centred dermatology in Addis Ababa: mission, vision, values and our team of dermatologists.",
            page("About us", "Medical, surgical and cosmetic dermatology under one roof at our Bole and Zenebework branches.",
                 "<p>Our mission is to provide up-to-date, affordable and state-of-the-art health care, delivered in a personable and compassionate manner. "
                 "Our vision is to become a leader in innovative, high-quality dermatologic services in East Africa.</p>"),
            [breadcrumbs(("Home", "/"), ("About us", "/about"))], "/about")


def render_appointment():
    return ("Book an in-person visit | " + CLINIC, "Book an in-person appointment at our Bole or Zenebework branch in Addis Ababa.",
            page("Book an in-person visit", "Choose a branch, a doctor and a time. Online visits are booked on Tena Medicine.", ""),
            [breadcrumbs(("Home", "/"), ("In-person visit", "/appointment"))], "/appointment")


STATIC_ROUTES = {"about": render_about, "appointment": render_appointment, "": render_home, "doctors": render_doctors, "conditions": render_conditions, "services": render_services,
                 "telemedicine": render_telemedicine, "reviews": render_reviews, "blog": render_blog, "contact": render_contact,
                 "search": lambda: ("Search | " + CLINIC, "Search conditions, doctors and articles.", page("Search", "Search the website."),
                                    [], "/search")}
DYNAMIC_ROUTES = {"doctors": render_doctor, "conditions": render_condition, "blog": render_post}


def shell_for(path):
    """Returns (html, status) for a public page, or None if the path is not a website page."""
    parts = [p for p in path.strip("/").split("/") if p]
    result = None
    if len(parts) == 0 or (len(parts) == 1 and parts[0] in STATIC_ROUTES):
        result = STATIC_ROUTES[parts[0] if parts else ""]()
    elif len(parts) == 2 and parts[0] in DYNAMIC_ROUTES:
        result = DYNAMIC_ROUTES[parts[0]](parts[1])
        if result is None:
            return None
    else:
        return None
    title, desc, body, ld, canon, *rest = result
    image = absolute(rest[0]) if rest and rest[0] else absolute("/assets/img/hero-poster.jpg")
    head = (f"<title>{e(title)}</title><meta name=\"description\" content=\"{e(desc)}\">"
            f"<link rel=\"canonical\" href=\"{e(absolute(canon))}\">"
            f"<meta property=\"og:type\" content=\"website\"><meta property=\"og:site_name\" content=\"{e(CLINIC)}\">"
            f"<meta property=\"og:title\" content=\"{e(title)}\"><meta property=\"og:description\" content=\"{e(desc)}\">"
            f"<meta property=\"og:url\" content=\"{e(absolute(canon))}\"><meta property=\"og:image\" content=\"{e(image)}\">"
            f"<meta name=\"twitter:card\" content=\"summary_large_image\">" + jsonld(*ld))
    return head, body


@lru_cache(maxsize=4)
def _template(path, mtime):
    return Path(path).read_text(encoding="utf-8")


def render_shell(path):
    """Full HTML document for a website page (or None when `path` is not one)."""
    found = shell_for(path)
    if not found:
        return None
    index = Path(current_app.config["FRONTEND_DIR"]) / "index.html"
    if not index.exists():
        return "<h1>Website not built yet</h1><p>Run <code>npm run build</code> in the frontend folder.</p>"
    html = _template(str(index), index.stat().st_mtime)
    head, body = found
    html = re.sub(r"<title>.*?</title>", "", html, count=1, flags=re.S)
    return html.replace("<!--SEO_HEAD-->", head).replace("<!--SEO_BODY-->", body)


# ---------------------------------------------------------------- crawler files

@seo.get("/robots.txt")
def robots():
    lines = ["User-agent: *", "Allow: /", "Disallow: /admin", "Disallow: /api/", "",
             "# AI assistants are welcome to read the public pages.",
             "User-agent: GPTBot", "Allow: /", "User-agent: ClaudeBot", "Allow: /", "User-agent: PerplexityBot", "Allow: /",
             "User-agent: Google-Extended", "Allow: /", "", f"Sitemap: {base_url()}/sitemap.xml", ""]
    return Response("\n".join(lines), mimetype="text/plain")


@seo.get("/sitemap.xml")
def sitemap():
    urls = [("/", None)] + [(f"/{p}", None) for p in ("about", "doctors", "conditions", "services", "telemedicine", "reviews", "blog", "appointment", "contact")]
    urls += [(f"/doctors/{d.slug}", d.updated_at) for d in published_doctors()]
    urls += [(f"/conditions/{c.slug}", c.updated_at) for c in Condition.query.filter_by(published=True)]
    urls += [(f"/blog/{p.slug}", p.updated_at or p.created_at) for p in Post.query.filter_by(published=True)]
    body = "".join(f"<url><loc>{e(base_url() + path)}</loc>" + (f"<lastmod>{m.date().isoformat()}</lastmod>" if m else "") + "</url>"
                   for path, m in urls)
    return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + body + "</urlset>",
                    mimetype="application/xml")


@seo.get("/llms.txt")
def llms():
    s = get_settings()
    b = base_url()
    out = [f"# {CLINIC}", "", f"> {TAGLINE} Dermatology care for skin, hair and nails in Addis Ababa, Ethiopia, in the clinic and online through telemedicine.", "",
           "## Doctors"]
    for d in published_doctors():
        data = d.to_dict(full=True)
        bits = [d.title]
        if data["subspecialties"]:
            bits.append("subspecialties: " + ", ".join(data["subspecialties"]))
        if data["languages"]:
            bits.append("languages: " + ", ".join(data["languages"]))
        out.append(f"- [{d.name}]({b}/doctors/{d.slug}): " + "; ".join(bits))
    out += ["", "## Conditions"] + [f"- [{c.name}]({b}/conditions/{c.slug}): {c.summary}" for c in Condition.query.filter_by(published=True).order_by(Condition.sort_order)]
    out += ["", "## Services"] + [f"- {g['title']}: {', '.join(g['items'])}" for g in SERVICE_GROUPS]
    out += ["", "## Booking", f"- Telemedicine (chat or video), booked and paid on Tena Medicine: {s['telemedicine_url']}",
            f"- In-person visits: {absolute(s['in_person_url'])}", "",
            "## Locations and contact"] + [f"- {x['name']}: {BRANCH_ADDRESS.get(x['slug'], '')}. Phone {x['phone']}" for x in BRANCHES]
    out += [f"- Email: {s['email']}", f"- Phones: {s['phones']}", "", "## Pages",
            f"- [Reviews]({b}/reviews)", f"- [Blog]({b}/blog)", f"- [Telemedicine]({b}/telemedicine)", f"- [Contact]({b}/contact)", ""]
    return Response("\n".join(out), mimetype="text/plain")


# ---------------------------------------------------------------- uploaded photos

@seo.get("/media/<kind>/<int:item_id>")
def media(kind, item_id):
    from .content_models import db
    model = {"doctors": Doctor}.get(kind) or abort(404)
    item = db.session.get(model, item_id) or abort(404)
    if not item.photo_data:
        abort(404)
    resp = Response(item.photo_data, mimetype=item.photo_mime or "image/jpeg")
    resp.cache_control.public = True
    resp.cache_control.max_age = 60 * 60 * 24 * 365
    return resp
