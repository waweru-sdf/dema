"""Admin pages for the public website: doctors, conditions, reviews, blog posts and settings.

All pages share one generic form (templates/admin/content_form.html) driven by the field lists below,
so adding a field to a page means adding one line here and one column in content_models.py.
"""
import io
import re
from datetime import date, datetime
from pathlib import Path

from flask import abort, current_app, flash, redirect, render_template, request, url_for
from PIL import Image, ImageOps

from .admin import admin, login_required
from .clinic_data import BRANCHES
from .content_models import (SETTING_DEFAULTS, Condition, Doctor, Review, Setting, get_settings,
                             split_lines, unique_slug)
from .models import BlogPost, db, utcnow
from .site_api import privacy_flags

# ---------------------------------------------------------------- shared helpers


def process_photo(file_storage, max_w=900, max_h=1125):
    """Resize an uploaded picture to a web-friendly JPEG. Raises ValueError for non-images."""
    try:
        img = Image.open(file_storage.stream)
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise ValueError("That file is not a picture. Please upload a JPG or PNG.") from exc
    img.thumbnail((max_w, max_h))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85, optimize=True)
    return buf.getvalue(), "image/jpeg"


def image_choices():
    """Pictures already on the website that can be used as a cover."""
    root = Path(current_app.config["FRONTEND_DIR"]) / "assets" / "img"
    out = []
    for p in sorted(root.rglob("*.jpg")) if root.exists() else []:
        rel = p.relative_to(root).as_posix()
        if not rel.startswith("doctors/"):
            out.append((rel, rel))
    return [("", "No picture")] + out


def branch_choices():
    return [("", "Not set")] + [(b["slug"], b["name"]) for b in BRANCHES]


def doctor_choices(blank="Not set"):
    return [("", blank)] + [(str(d.id), d.name) for d in Doctor.query.order_by(Doctor.sort_order, Doctor.name)]


def condition_choices(blank="General"):
    return [("", blank)] + [(str(c.id), c.name) for c in Condition.query.order_by(Condition.sort_order, Condition.name)]


# ---------------------------------------------------------------- field definitions
# type: text | textarea | number | checkbox | select | date | photo | links
F = dict


def doctor_fields():
    return [
        F(group="Who they are"),
        F(name="name", label="Full name", type="text", required=True, max=120),
        F(name="title", label="Professional title", type="text", max=160, help="Shown under the name, for example Dermatologist and dermatologic surgeon."),
        F(name="branch", label="Branch", type="select", choices=branch_choices()),
        F(name="years_experience", label="Years of experience", type="number", help="Leave empty if unknown. Nothing is shown until you fill it in."),
        F(name="photo", label="Profile photo", type="photo", help="JPG or PNG, a portrait works best. It is resized automatically."),
        F(name="bio", label="Biography", type="textarea", rows=5, help="A few sentences in plain language."),
        F(group="Credentials (shown as visible text and in structured data for search engines and AI assistants)"),
        F(name="qualifications", label="Qualifications and certifications", type="textarea", rows=6,
          help="One per line, as  Title | Details.  Example:  Board certification | Dermatology, Ethiopian Medical Association, 2016"),
        F(name="registration_no", label="Registration number", type="text", max=60),
        F(name="languages", label="Languages", type="text", help="Separate with commas, for example English, Amharic, Afaan Oromo."),
        F(name="subspecialties", label="Subspecialties", type="text", help="Separate with commas."),
        F(name="procedures", label="Procedures", type="text", help="Separate with commas."),
        F(name="conditions", label="Conditions treated (each links to its condition page)", type="links",
          choices=lambda: [(str(c.id), c.name) for c in Condition.query.order_by(Condition.sort_order)]),
        F(group="Visibility"),
        F(name="accepts_telemedicine", label="Accepts telemedicine bookings", type="checkbox"),
        F(name="published", label="Show on the public website", type="checkbox"),
        F(name="show_on_home", label="Show on the home page", type="checkbox"),
        F(name="sort_order", label="Order (smaller numbers first)", type="number"),
    ]


def condition_fields():
    return [
        F(group="Page"),
        F(name="name", label="Name", type="text", required=True, max=120),
        F(name="summary", label="Short summary", type="textarea", rows=3, required=True, help="One or two sentences. Shown on cards and in search results."),
        F(name="image", label="Picture", type="select", choices=image_choices),
        F(group="Content"),
        F(name="facts", label="Key facts (up to four)", type="textarea", rows=4, help="One per line, as  Label | Detail.  Example:  Main sign | Pale or white patches"),
        F(name="symptoms", label="Symptoms", type="textarea", rows=5, help="One per line."),
        F(name="causes", label="Causes and risk factors", type="textarea", rows=5),
        F(name="steps", label="How we approach treatment", type="textarea", rows=5, help="One step per line, as  Title | Description."),
        F(name="faqs", label="Frequently asked questions", type="textarea", rows=6, help="One per line, as  Question | Answer."),
        F(group="Doctors and review"),
        F(name="doctors", label="Doctors who treat this condition", type="links",
          choices=lambda: [(str(d.id), d.name) for d in Doctor.query.order_by(Doctor.sort_order, Doctor.name)]),
        F(name="reviewed_by_id", label="Medically reviewed by", type="select", choices=lambda: doctor_choices("Nobody yet"),
          help="Only shown on the public page once a doctor and a date are both set. Have a doctor read this page before choosing."),
        F(name="reviewed_on", label="Review date", type="date"),
        F(group="Visibility"),
        F(name="published", label="Show on the public website", type="checkbox"),
        F(name="sort_order", label="Order (smaller numbers first)", type="number"),
    ]


def review_fields():
    return [
        F(name="body", label="Review text", type="textarea", rows=6, required=True,
          help="You may shorten or correct spelling. Remove names, phone numbers and private medical details."),
        F(name="rating", label="Stars (1 to 5)", type="number", required=True),
        F(name="reviewer_label", label="Shown as", type="text", max=60, help="For example Woman, 30s. Never a full name."),
        F(name="condition_id", label="Condition", type="select", choices=lambda: condition_choices("Not set")),
        F(name="symptom", label="Symptom", type="text", max=80),
        F(name="treatment", label="Treatment", type="text", max=80),
        F(name="doctor_id", label="Doctor", type="select", choices=lambda: doctor_choices("Not set")),
        F(name="status", label="Status", type="select", choices=[("pending", "Waiting for approval"), ("approved", "Approved (visible)"), ("rejected", "Rejected")]),
    ]


KINDS = {
    "doctors": dict(model=Doctor, fields=doctor_fields, title="Doctor", plural="Doctors", name_attr="name"),
    "conditions": dict(model=Condition, fields=condition_fields, title="Condition page", plural="Conditions", name_attr="name"),
    "reviews": dict(model=Review, fields=review_fields, title="Review", plural="Reviews", name_attr="reviewer_label"),
}


def resolve(choices):
    return choices() if callable(choices) else choices


def read_form(kind, obj, fields):
    """Copies the submitted form into `obj`. Returns a list of error messages."""
    errors = []
    for f in fields:
        if "group" in f:
            continue
        n, t = f["name"], f["type"]
        raw = request.form.get(n, "")
        if t in ("text", "textarea"):
            value = raw.strip()[: f.get("max", 12000)]
            if f.get("required") and not value:
                errors.append(f"{f['label']} is required.")
            setattr(obj, n, value or (None if n not in ("title", "name", "summary", "excerpt", "body", "category") else ""))
        elif t == "number":
            if raw.strip() == "":
                if f.get("required"):
                    errors.append(f"{f['label']} is required.")
                if n in ("sort_order",):
                    setattr(obj, n, 100)
                elif n != "rating":
                    setattr(obj, n, None)
            else:
                try:
                    setattr(obj, n, int(raw))
                except ValueError:
                    errors.append(f"{f['label']} must be a whole number.")
        elif t == "checkbox":
            setattr(obj, n, request.form.get(n) == "on")
        elif t == "select":
            allowed = {str(v) for v, _ in resolve(f["choices"])}
            if raw not in allowed:
                errors.append(f"Choose a valid option for {f['label']}.")
            elif n.endswith("_id"):
                setattr(obj, n, int(raw) if raw else None)
            else:
                setattr(obj, n, raw or None)
        elif t == "date":
            if raw.strip():
                try:
                    d = date.fromisoformat(raw)
                    setattr(obj, n, d)
                except ValueError:
                    errors.append(f"{f['label']} must be a date.")
            elif n == "published_at":
                setattr(obj, n, utcnow())
            else:
                setattr(obj, n, None)
        elif t == "photo":
            file = request.files.get(n)
            if request.form.get(n + "_remove") == "on":
                obj.photo_data = obj.photo_mime = obj.photo_updated = None
            elif file and file.filename:
                try:
                    obj.photo_data, obj.photo_mime = process_photo(file)
                    obj.photo_updated = utcnow()
                except ValueError as exc:
                    errors.append(str(exc))
        elif t == "links":
            ids = [int(x) for x in request.form.getlist(n) if x.isdigit()]
            other = Condition if n == "conditions" else Doctor
            setattr(obj, n, other.query.filter(other.id.in_(ids)).all() if ids else [])
    if kind == "reviews" and obj.rating and not 1 <= obj.rating <= 5:
        errors.append("Stars must be between 1 and 5.")
    return errors


def unlink_references(kind, obj):
    """Detach rows that point at `obj` so deleting never breaks other pages."""
    if kind == "doctors":
        for model, col in ((Review, "doctor_id"), (Condition, "reviewed_by_id")):
            model.query.filter(getattr(model, col) == obj.id).update({col: None})
        obj.conditions = []
    elif kind == "conditions":
        Review.query.filter_by(condition_id=obj.id).update({"condition_id": None})
        obj.doctors = []


@admin.app_context_processor
def content_nav():
    from flask import session
    pending = Review.query.filter_by(status="pending").count() if session.get("admin_id") else 0
    return {"pending_reviews": pending}


# ---------------------------------------------------------------- list / edit / delete

@admin.get("/site")
@login_required
def site_home():
    return render_template("admin/site_home.html", counts={
        "doctors": Doctor.query.count(), "conditions": Condition.query.count(), "posts": BlogPost.query.count(),
        "pending": Review.query.filter_by(status="pending").count(), "approved": Review.query.filter_by(status="approved").count(),
        "sample_reviews": Review.query.filter_by(is_sample=True).count(), "sample_posts": 0})


@admin.get("/content/<any(doctors,conditions):kind>")
@login_required
def content_list(kind):
    cfg = KINDS[kind]
    q = cfg["model"].query
    if kind == "doctors":
        q = q.order_by(Doctor.sort_order, Doctor.name)
    elif kind == "conditions":
        q = q.order_by(Condition.sort_order)
    else:
        q = q.order_by(Condition.sort_order)
    return render_template("admin/content_list.html", kind=kind, cfg=cfg, items=q.all())


@admin.route("/content/<any(doctors,conditions,reviews):kind>/<item_id>", methods=["GET", "POST"])
@login_required
def content_edit(kind, item_id):
    cfg = KINDS[kind]
    model = cfg["model"]
    creating = item_id == "new"
    if creating and kind == "reviews":
        abort(404)
    obj = model() if creating else (db.session.get(model, int(item_id)) if item_id.isdigit() else None)
    if obj is None:
        abort(404)
    fields = cfg["fields"]()
    if creating:  # sensible defaults for a new item
        defaults = {"published": True, "accepts_telemedicine": True, "show_on_home": True, "sort_order": 100}
        for k, v in defaults.items():
            if hasattr(model, k):
                setattr(obj, k, v)
    if request.method == "POST":
        errors = read_form(kind, obj, fields)
        if kind == "reviews":
            errors += [f"The text {r}." for r in privacy_flags(obj.body)]
        if errors:
            for msg in errors:
                flash(msg, "error")
            db.session.rollback()
            return render_template("admin/content_form.html", kind=kind, cfg=cfg, obj=obj, fields=fields, creating=creating, resolve=resolve), 400
        if creating:
            base = re.sub(r"^dr\.?\s+", "", str(getattr(obj, cfg["name_attr"])), flags=re.I)
            obj.slug = unique_slug(model, base)
            db.session.add(obj)
        if hasattr(obj, "is_sample") and obj.is_sample:
            obj.is_sample = False  # a person has now checked and saved it
        db.session.commit()
        flash("Saved.", "success")
        return redirect(url_for("admin.content_edit", kind=kind, item_id=obj.id) if request.form.get("stay") else
                        url_for("admin.reviews_queue") if kind == "reviews" else url_for("admin.content_list", kind=kind))
    return render_template("admin/content_form.html", kind=kind, cfg=cfg, obj=obj, fields=fields, creating=creating, resolve=resolve)


@admin.post("/content/<any(doctors,conditions,reviews):kind>/<int:item_id>/delete")
@login_required
def content_delete(kind, item_id):
    obj = db.session.get(KINDS[kind]["model"], item_id) or abort(404)
    unlink_references(kind, obj)
    db.session.delete(obj)
    db.session.commit()
    flash("Deleted.", "success")
    return redirect(url_for("admin.reviews_queue") if kind == "reviews" else url_for("admin.content_list", kind=kind))


# ---------------------------------------------------------------- review moderation

@admin.get("/reviews")
@login_required
def reviews_queue():
    status = request.args.get("status", "pending")
    if status not in ("pending", "approved", "rejected"):
        status = "pending"
    items = Review.query.filter_by(status=status).order_by(Review.created_at.desc()).all()
    counts = {s: Review.query.filter_by(status=s).count() for s in ("pending", "approved", "rejected")}
    return render_template("admin/reviews.html", items=items, status=status, counts=counts, flags=privacy_flags)


@admin.post("/reviews/<int:review_id>/<any(approve,reject,pending):action>")
@login_required
def review_action(review_id, action):
    r = db.session.get(Review, review_id) or abort(404)
    if action == "approve":
        flags = privacy_flags(r.body)
        if flags or not r.consent:
            flash("Not approved: " + ("the patient did not give consent. " if not r.consent else "")
                  + ("The text " + ", and ".join(flags) + ". Edit it first." if flags else ""), "error")
            return redirect(request.referrer or url_for("admin.reviews_queue"))
        r.status = "approved"
    else:
        r.status = "rejected" if action == "reject" else "pending"
    db.session.commit()
    flash(f"Review {'approved' if action == 'approve' else 'rejected' if action == 'reject' else 'moved back to waiting'}.", "success")
    return redirect(request.referrer or url_for("admin.reviews_queue"))


# ---------------------------------------------------------------- settings

@admin.route("/site-settings", methods=["GET", "POST"])
@login_required
def site_settings():
    current = get_settings()
    if request.method == "POST":
        errors = []
        for key in SETTING_DEFAULTS:
            value = request.form.get(key, "").strip()[:500]
            if key in ("price_chat", "price_video_chat", "chat_days") and not (value.isdigit() and int(value) >= 1):
                errors.append(f"{key.replace('_', ' ').capitalize()} must be a whole number of 1 or more.")
                continue
            if key in ("telemedicine_url", "in_person_url") and not (value.startswith(("http://", "https://", "/"))):
                errors.append("Web addresses must start with https:// (or / for a page on this site).")
                continue
            if key == "site_url" and value and not value.startswith(("http://", "https://")):
                errors.append("The public website address must start with https://")
                continue
            row = db.session.get(Setting, key)
            if row:
                row.value = value
            else:
                db.session.add(Setting(key=key, value=value))
        if errors:
            for m in errors:
                flash(m, "error")
            db.session.rollback()
        else:
            db.session.commit()
            flash("Settings saved.", "success")
            return redirect(url_for("admin.site_settings"))
        current = {**current, **{k: request.form.get(k, "") for k in SETTING_DEFAULTS}}
    return render_template("admin/site_settings.html", values=current, defs=SETTING_DEFAULTS)
