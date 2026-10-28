"""Public-website content: doctors, conditions, reviews, blog posts and site settings.

Everything the React site shows (besides static images) lives here and is edited in /admin.
Multi-value fields are stored as plain text so staff can edit them in simple form boxes:
  * comma lists   -> languages, subspecialties, procedures
  * "A | B" lines -> qualifications, key facts, treatment steps, FAQs
"""
import re
from datetime import date

from flask import current_app
from pathlib import Path

from .models import db, utcnow

# ---------------------------------------------------------------- text helpers


def split_commas(text):
    return [p.strip() for p in (text or "").split(",") if p.strip()]


def split_lines(text):
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip()]


def split_pairs(text):
    """'Label | Detail' per line -> [{"label":..., "detail":...}]. A line without '|' becomes a label only."""
    out = []
    for ln in split_lines(text):
        label, _, detail = ln.partition("|")
        out.append({"label": label.strip(), "detail": detail.strip()})
    return out


def slugify(text):
    text = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return text[:80] or "item"


def unique_slug(model, base, exclude_id=None):
    slug, n = slugify(base), 2
    while True:
        q = model.query.filter_by(slug=slug)
        if exclude_id:
            q = q.filter(model.id != exclude_id)
        if not q.first():
            return slug
        slug = f"{slugify(base)}-{n}"
        n += 1


def static_image_exists(rel):
    root = Path(current_app.config["FRONTEND_DIR"])
    return (root / rel).is_file()


# ---------------------------------------------------------------- tables

doctor_conditions = db.Table(
    "site_doctor_conditions",
    db.Column("doctor_id", db.Integer, db.ForeignKey("site_doctors.id", ondelete="CASCADE"), primary_key=True),
    db.Column("condition_id", db.Integer, db.ForeignKey("conditions.id", ondelete="CASCADE"), primary_key=True),
)


class Doctor(db.Model):
    __tablename__ = "site_doctors"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(160), nullable=False, default="Dermatologist")
    branch = db.Column(db.String(40), nullable=True)          # slug from clinic_data.BRANCHES
    years_experience = db.Column(db.Integer, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    languages = db.Column(db.Text, nullable=True)             # comma list
    subspecialties = db.Column(db.Text, nullable=True)        # comma list
    procedures = db.Column(db.Text, nullable=True)            # comma list
    qualifications = db.Column(db.Text, nullable=True)        # "Degree | Institution, year" per line
    registration_no = db.Column(db.String(60), nullable=True)
    accepts_telemedicine = db.Column(db.Boolean, nullable=False, default=True)
    published = db.Column(db.Boolean, nullable=False, default=True, index=True)
    show_on_home = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=100)
    photo_data = db.Column(db.LargeBinary, nullable=True)
    photo_mime = db.Column(db.String(40), nullable=True)
    photo_updated = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    conditions = db.relationship("Condition", secondary=doctor_conditions, back_populates="doctors",
                                 order_by="Condition.sort_order")

    @property
    def photo_url(self):
        if self.photo_data:
            return f"/media/doctors/{self.id}?v={int(self.photo_updated.timestamp()) if self.photo_updated else 0}"
        rel = f"assets/img/doctors/{self.slug}.jpg"
        return "/" + rel if static_image_exists(rel) else None

    @property
    def completeness(self):
        """Checklist the admin shows so staff know what is still missing on a profile."""
        checks = {
            "Photo": bool(self.photo_url),
            "Biography": bool(self.bio),
            "Qualifications": bool(split_lines(self.qualifications)),
            "Languages": bool(split_commas(self.languages)),
            "Subspecialties": bool(split_commas(self.subspecialties)),
            "Conditions linked": bool(self.conditions),
            "Branch": bool(self.branch),
            "Years of experience": self.years_experience is not None,
        }
        return checks

    def to_dict(self, full=False):
        from .clinic_data import BRANCH_BY_SLUG
        d = {
            "slug": self.slug, "name": self.name, "title": self.title,
            "branch": self.branch, "branch_name": BRANCH_BY_SLUG.get(self.branch or "", {}).get("name"),
            "years_experience": self.years_experience, "photo": self.photo_url,
            "accepts_telemedicine": self.accepts_telemedicine,
            "languages": split_commas(self.languages), "subspecialties": split_commas(self.subspecialties),
            "conditions": [{"slug": c.slug, "name": c.name} for c in self.conditions if c.published],
        }
        if full:
            d.update(bio=self.bio or "", procedures=split_commas(self.procedures),
                     qualifications=split_pairs(self.qualifications), registration_no=self.registration_no or "",
                     updated_at=(self.updated_at or utcnow()).date().isoformat())
        return d


class Condition(db.Model):
    __tablename__ = "conditions"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    summary = db.Column(db.Text, nullable=False, default="")
    facts = db.Column(db.Text, nullable=True)       # "Main sign | Pale patches" (up to 4 lines)
    symptoms = db.Column(db.Text, nullable=True)    # one per line
    causes = db.Column(db.Text, nullable=True)
    steps = db.Column(db.Text, nullable=True)       # "Title | Detail" per line
    faqs = db.Column(db.Text, nullable=True)        # "Question | Answer" per line
    image = db.Column(db.String(120), nullable=True)  # path under assets/img, for example services/pigment.jpg
    published = db.Column(db.Boolean, nullable=False, default=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=100)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("site_doctors.id", ondelete="SET NULL"), nullable=True)
    reviewed_on = db.Column(db.Date, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    doctors = db.relationship("Doctor", secondary=doctor_conditions, back_populates="conditions")
    reviewed_by = db.relationship("Doctor", foreign_keys=[reviewed_by_id])

    def to_dict(self, full=False):
        d = {"slug": self.slug, "name": self.name, "summary": self.summary,
             "image": ("/assets/img/" + self.image) if self.image else None}
        if full:
            pub = [x for x in self.doctors if x.published]
            d.update(
                facts=split_pairs(self.facts), symptoms=split_lines(self.symptoms), causes=self.causes or "",
                steps=split_pairs(self.steps), faqs=split_pairs(self.faqs),
                doctors=[x.to_dict() for x in sorted(pub, key=lambda x: (x.sort_order, x.name))],
                reviewed_by=self.reviewed_by.to_dict() if self.reviewed_by and self.reviewed_by.published else None,
                reviewed_on=self.reviewed_on.isoformat() if self.reviewed_on else None,
                updated_at=(self.updated_at or utcnow()).date().isoformat(),
            )
        return d


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    condition_id = db.Column(db.Integer, db.ForeignKey("conditions.id", ondelete="SET NULL"), nullable=True)
    symptom = db.Column(db.String(80), nullable=True)
    treatment = db.Column(db.String(80), nullable=True)
    body = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5)
    reviewer_label = db.Column(db.String(60), nullable=False, default="Patient")   # "Woman, 30s": never a full name
    doctor_id = db.Column(db.Integer, db.ForeignKey("site_doctors.id", ondelete="SET NULL"), nullable=True)
    consent = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)  # pending/approved/rejected
    is_sample = db.Column(db.Boolean, nullable=False, default=False)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    condition = db.relationship("Condition")
    doctor = db.relationship("Doctor")

    def to_dict(self):
        return {
            "id": self.id, "rating": self.rating, "body": self.body, "reviewer": self.reviewer_label,
            "condition": {"slug": self.condition.slug, "name": self.condition.name} if self.condition else None,
            "symptom": self.symptom, "treatment": self.treatment,
            "doctor": {"slug": self.doctor.slug, "name": self.doctor.name} if self.doctor else None,
            "sample": self.is_sample, "date": self.created_at.date().isoformat(),
        }


class Setting(db.Model):
    __tablename__ = "site_settings"

    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="")


SETTING_DEFAULTS = {
    "telemedicine_url": ("https://tena.marhiwotmch.com", "Telemedicine service address (Tena Medicine). Every 'Book Telemedicine' button goes here."),
    "in_person_url": ("/appointment", "Address for in-person bookings. Leave /appointment to use this site's own booking page."),
    "price_chat": ("800", "Price shown for 'Chat with a doctor', in birr. Set the real price in Tena first; this is only the number shown here."),
    "price_video_chat": ("1500", "Price shown for 'Video consultation + chat', in birr."),
    "chat_days": ("30", "How many days the chat stays open after a paid visit."),
    "email": ("Feyselclinic@gmail.com", "Public clinic email."),
    "phones": ("0955 904 040, 0920 201 929, 0955 803 030, 0919 237 070, 0118 322 653", "Public phone numbers, separated by commas."),
    "site_url": ("", "Public address of this website for sitemaps and search engines, for example https://www.example.com. Leave empty to detect it automatically."),
}


def get_settings():
    rows = {s.key: s.value for s in Setting.query.all()}
    return {k: rows.get(k, v[0]) for k, v in SETTING_DEFAULTS.items()}
