"""Public JSON API for the React website: doctors, conditions, reviews, blog, search, settings."""
import re
from collections import Counter

from flask import Blueprint, abort, jsonify, request
from sqlalchemy import func

from .clinic_data import BRANCHES
from .content_models import (Condition, Doctor, Review, get_settings, split_commas)
from .models import BlogPost as Post, GalleryImage, db
from .services import limiter
from .site_services import SERVICE_GROUPS

site_api = Blueprint("site_api", __name__, url_prefix="/api/site")

AGE_GROUPS = ["Child (parent writing)", "Teen", "20s", "30s", "40s", "50s", "60s or over"]
GENDERS = ["Woman", "Man", "Prefer not to say"]
REVIEWS_PER_PAGE = 12

EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
LONG_NUMBER_RE = re.compile(r"(?:\+?\d[\s-]?){7,}")


def privacy_flags(text):
    """Returns reasons a review should not be published as written (used on submit and in the admin queue)."""
    flags = []
    if EMAIL_RE.search(text or ""):
        flags.append("contains an email address")
    if LONG_NUMBER_RE.search(text or ""):
        flags.append("contains a phone or ID number")
    return flags


def published_doctors():
    return Doctor.query.filter_by(published=True).order_by(Doctor.sort_order, Doctor.name)


def public_settings():
    s = get_settings()
    return {
        "telemedicine_url": s["telemedicine_url"], "in_person_url": s["in_person_url"],
        "prices": {"chat": s["price_chat"], "video_chat": s["price_video_chat"]},
        "chat_days": s["chat_days"], "email": s["email"],
        "phones": split_commas(s["phones"]),
        "branches": [{"slug": b["slug"], "name": b["name"], "phone": b["phone"]} for b in BRANCHES],
    }


def approved_reviews():
    return Review.query.filter_by(status="approved")


def review_summary():
    row = approved_reviews().with_entities(func.count(Review.id), func.avg(Review.rating)).one()
    count, avg = row[0] or 0, row[1]
    return {"count": count, "average": round(float(avg), 1) if avg else None}


@site_api.get("/settings")
def settings():
    return jsonify(public_settings())


@site_api.get("/home")
def home():
    doctors = published_doctors().filter_by(show_on_home=True).all()
    conditions = Condition.query.filter_by(published=True).order_by(Condition.sort_order).all()
    reviews = approved_reviews().order_by(Review.created_at.desc()).limit(6).all()
    posts = Post.query.filter_by(published=True).order_by(Post.published_at.desc(), Post.id.desc()).limit(3).all()
    return jsonify(
        doctors=[d.to_dict() for d in doctors], doctor_count=published_doctors().count(),
        conditions=[c.to_dict() for c in conditions], reviews=[r.to_dict() for r in reviews],
        review_summary=review_summary(), posts=[p.to_dict() for p in posts], settings=public_settings(),
    )


# ---------------------------------------------------------------- doctors

@site_api.get("/gallery")
def gallery():
    rows = GalleryImage.query.order_by(GalleryImage.sort_order, GalleryImage.id).all()
    resp = jsonify(gallery=[g.to_dict() for g in rows])
    resp.cache_control.no_cache = True
    return resp


@site_api.get("/services")
def services():
    return jsonify(services=SERVICE_GROUPS)


@site_api.get("/doctors")
def doctors():
    q = published_doctors()
    cond = request.args.get("condition")
    items = q.all()
    if cond:
        items = [d for d in items if any(c.slug == cond for c in d.conditions)]
    return jsonify(doctors=[d.to_dict() for d in items])


@site_api.get("/doctors/<slug>")
def doctor(slug):
    d = Doctor.query.filter_by(slug=slug, published=True).first() or abort(404)
    reviews = approved_reviews().filter_by(doctor_id=d.id).order_by(Review.created_at.desc()).limit(6).all()
    return jsonify(doctor=d.to_dict(full=True), reviews=[r.to_dict() for r in reviews], settings=public_settings())


# ---------------------------------------------------------------- conditions

@site_api.get("/conditions")
def conditions():
    items = Condition.query.filter_by(published=True).order_by(Condition.sort_order).all()
    return jsonify(conditions=[c.to_dict() for c in items])


@site_api.get("/conditions/<slug>")
def condition(slug):
    c = Condition.query.filter_by(slug=slug, published=True).first() or abort(404)
    doctors_ = c.to_dict(full=True)["doctors"]
    if not doctors_:  # no one linked yet: fall back to the whole team so the page is never a dead end
        doctors_ = [d.to_dict() for d in published_doctors().all()]
    data = c.to_dict(full=True)
    data["doctors"] = doctors_
    reviews = approved_reviews().filter_by(condition_id=c.id).order_by(Review.created_at.desc()).limit(3).all()
    return jsonify(condition=data, reviews=[r.to_dict() for r in reviews], settings=public_settings())


# ---------------------------------------------------------------- reviews

@site_api.get("/reviews")
def reviews():
    q = approved_reviews()
    f = {k: (request.args.get(k) or "").strip() for k in ("condition", "symptom", "treatment", "doctor")}
    if f["condition"]:
        q = q.join(Condition, Review.condition_id == Condition.id).filter(Condition.slug == f["condition"])
    if f["doctor"]:
        q = q.join(Doctor, Review.doctor_id == Doctor.id).filter(Doctor.slug == f["doctor"])
    if f["symptom"]:
        q = q.filter(Review.symptom == f["symptom"])
    if f["treatment"]:
        q = q.filter(Review.treatment == f["treatment"])
    page = max(1, request.args.get("page", 1, type=int))
    total = q.count()
    items = q.order_by(Review.created_at.desc()).offset((page - 1) * REVIEWS_PER_PAGE).limit(REVIEWS_PER_PAGE).all()

    allr = approved_reviews().all()
    cond = Counter((r.condition.slug, r.condition.name) for r in allr if r.condition)
    docs = Counter((r.doctor.slug, r.doctor.name) for r in allr if r.doctor)
    facets = {
        "conditions": [{"slug": s, "name": n, "count": c} for (s, n), c in sorted(cond.items(), key=lambda x: x[0][1])],
        "doctors": [{"slug": s, "name": n, "count": c} for (s, n), c in sorted(docs.items(), key=lambda x: x[0][1])],
        "symptoms": [{"name": n, "count": c} for n, c in sorted(Counter(r.symptom for r in allr if r.symptom).items())],
        "treatments": [{"name": n, "count": c} for n, c in sorted(Counter(r.treatment for r in allr if r.treatment).items())],
    }
    return jsonify(reviews=[r.to_dict() for r in items], total=total, page=page, per_page=REVIEWS_PER_PAGE,
                   facets=facets, summary=review_summary(), age_groups=AGE_GROUPS, genders=GENDERS,
                   form_conditions=[{"slug": c.slug, "name": c.name} for c in
                                    Condition.query.filter_by(published=True).order_by(Condition.sort_order)],
                   form_doctors=[{"slug": d.slug, "name": d.name} for d in published_doctors()])


@site_api.post("/reviews")
def submit_review():
    body = request.get_json(silent=True) or {}
    if body.get("website"):  # honeypot
        return jsonify(ok=True), 201
    if not limiter.allow(f"review:{request.remote_addr}", 5):
        return jsonify(ok=False, message="Too many submissions. Please try again later."), 429

    errors = {}
    text = str(body.get("body") or "").strip()
    if not 20 <= len(text) <= 1200:
        errors["body"] = "Please write between 20 and 1,200 characters."
    for reason in privacy_flags(text):
        errors["body"] = f"Please remove personal details: your review {reason}."
    try:
        rating = int(body.get("rating"))
    except (TypeError, ValueError):
        rating = 0
    if not 1 <= rating <= 5:
        errors["rating"] = "Choose 1 to 5 stars."
    age, gender = body.get("age_group"), body.get("gender")
    if age not in AGE_GROUPS:
        errors["age_group"] = "Choose an age group."
    if gender not in GENDERS:
        errors["gender"] = "Choose an option."
    if body.get("consent") is not True:
        errors["consent"] = "We can only publish your review with your permission."
    cond = Condition.query.filter_by(slug=body.get("condition"), published=True).first() if body.get("condition") else None
    doc = Doctor.query.filter_by(slug=body.get("doctor"), published=True).first() if body.get("doctor") else None
    if errors:
        return jsonify(ok=False, message="Please check the highlighted fields.", errors=errors), 400

    if age.startswith("Child"):
        label = "Child (parent writing)"
    elif gender == "Prefer not to say":
        label = f"Patient, {age}"
    else:
        label = f"{gender}, {age}"
    clean = lambda k: (str(body.get(k) or "").strip()[:80] or None)  # noqa: E731
    db.session.add(Review(condition=cond, doctor=doc, symptom=clean("symptom"), treatment=clean("treatment"), body=text,
                          rating=rating, reviewer_label=label, consent=True, status="pending",
                          ip_address=request.remote_addr))
    db.session.commit()
    return jsonify(ok=True, message="Thank you. Your review will appear after our team has checked it."), 201


# ---------------------------------------------------------------- blog

@site_api.get("/posts")
def posts():
    q = Post.query.filter_by(published=True)
    cat = request.args.get("category")
    if cat:
        q = q.filter_by(category=cat)
    items = q.order_by(Post.published_at.desc(), Post.id.desc()).all()
    cats = sorted({p.category for p in Post.query.filter_by(published=True).all()})
    return jsonify(posts=[p.to_dict() for p in items], categories=cats)


@site_api.get("/posts/<slug>")
def post(slug):
    p = Post.query.filter_by(slug=slug, published=True).first() or abort(404)
    more = (Post.query.filter(Post.published.is_(True), Post.id != p.id)
            .order_by(Post.published_at.desc(), Post.id.desc()).limit(3).all())
    return jsonify(post=p.to_dict(full=True), more=[m.to_dict() for m in more])


# ---------------------------------------------------------------- search

@site_api.get("/search")
def search():
    q = (request.args.get("q") or "").strip().lower()[:80]
    if len(q) < 2:
        return jsonify(q=q, conditions=[], doctors=[], posts=[])

    def hit(*fields):
        return any(q in (f or "").lower() for f in fields)

    conds = [c for c in Condition.query.filter_by(published=True).order_by(Condition.sort_order)
             if hit(c.name, c.summary, c.symptoms)]
    docs = [d for d in published_doctors()
            if hit(d.name, d.title, d.subspecialties, d.procedures, " ".join(c.name for c in d.conditions))]
    ps = [p for p in Post.query.filter_by(published=True).order_by(Post.published_at.desc(), Post.id.desc()) if hit(p.title, p.excerpt)]
    return jsonify(q=q, conditions=[c.to_dict() for c in conds], doctors=[d.to_dict() for d in docs],
                   posts=[p.to_dict() for p in ps])


@site_api.errorhandler(404)
def nf(_e):
    return jsonify(ok=False, message="Not found"), 404
