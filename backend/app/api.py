"""Public JSON API used by the website forms."""
from flask import Blueprint, current_app, jsonify, request

from . import emails
from .clinic_data import ACTIVE_STATUSES, BRANCHES, SERVICES
from .models import Appointment, BlogPost, ContactMessage, Doctor, GalleryImage, db
from .services import (SlotTakenError, ValidationError, availability, limiter, parse_date,
                       validate_appointment, validate_contact)

api = Blueprint("api", __name__, url_prefix="/api")


def client_ip():
    # Behind a reverse proxy, enable ProxyFix (see wsgi.py) so this is the real visitor IP.
    return request.remote_addr or "unknown"


def payload():
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    return data or {}


def rate_limited(bucket):
    limit = current_app.config["RATE_LIMIT_PER_HOUR"]
    if not limiter.allow(f"{bucket}:{client_ip()}", limit):
        return jsonify(ok=False, message="Too many requests. Please try again later or call us."), 429
    return None


@api.get("/health")
def health():
    db.session.execute(db.text("SELECT 1"))
    return jsonify(ok=True)


def active_doctors():
    return Doctor.query.filter_by(active=True).order_by(Doctor.sort_order, Doctor.id).all()


@api.get("/site")
def site_content():
    """Doctors and gallery shown on the public pages (edited in /admin)."""
    gallery = GalleryImage.query.order_by(GalleryImage.sort_order, GalleryImage.id).all()
    resp = jsonify(doctors=[d.to_dict() for d in active_doctors()], gallery=[g.to_dict() for g in gallery])
    resp.cache_control.no_cache = True
    return resp


@api.get("/posts")
def list_posts():
    """Published blog posts, newest first. ?category=Skin care filters, ?limit=3 caps the list."""
    q = BlogPost.query.filter_by(published=True)
    category = (request.args.get("category") or "").strip()
    if category:
        q = q.filter_by(category=category)
    limit = request.args.get("limit", type=int)
    q = q.order_by(BlogPost.published_at.desc(), BlogPost.id.desc())
    if limit:
        q = q.limit(max(1, min(limit, 50)))
    categories = [c for (c,) in db.session.query(BlogPost.category).filter_by(published=True)
                  .distinct().order_by(BlogPost.category).all()]
    resp = jsonify(posts=[p.to_dict() for p in q.all()], categories=categories)
    resp.cache_control.no_cache = True
    return resp


@api.get("/posts/<slug>")
def get_post(slug):
    post = BlogPost.query.filter_by(slug=slug, published=True).first()
    if not post:
        return jsonify(ok=False, message="Post not found"), 404
    resp = jsonify(post=post.to_dict(full=True))
    resp.cache_control.no_cache = True
    return resp


@api.get("/meta")
def meta():
    return jsonify(
        doctors=[d.to_dict() for d in active_doctors()],
        services=SERVICES,
        branches=[{"slug": b["slug"], "name": b["name"]} for b in BRANCHES],
        slots=current_app.config["APPOINTMENT_SLOTS"],
        open_weekdays=current_app.config["OPEN_WEEKDAYS"],
    )


@api.get("/availability")
def get_availability():
    day = parse_date(request.args.get("date"))
    if not day:
        return jsonify(ok=False, message="Use ?date=YYYY-MM-DD"), 400
    result = availability(day, request.args.get("branch", ""), request.args.get("doctor", ""))
    return jsonify(ok=True, date=day.isoformat(), **result)


@api.post("/appointments")
def create_appointment():
    body = payload()
    if body.get("website"):  # honeypot field filled by bots
        return jsonify(ok=True, reference="FD-RECEIVED"), 201
    limited = rate_limited("appointment")
    if limited:
        return limited

    try:
        data = validate_appointment(body)
    except ValidationError as e:
        return jsonify(ok=False, message=e.message, errors=e.errors), 400
    except SlotTakenError:
        return jsonify(ok=False, message="Sorry, that time was just booked. Please choose another time.",
                       errors={"time": "This time is no longer available."}), 409

    appt = Appointment(**data, ip_address=client_ip())
    db.session.add(appt)
    db.session.flush()

    # Guard against two people booking the same doctor and slot at the same moment.
    if appt.doctor:
        clash = Appointment.query.filter(
            Appointment.doctor == appt.doctor, Appointment.date == appt.date, Appointment.time == appt.time,
            Appointment.status.in_(ACTIVE_STATUSES), Appointment.id != appt.id,
        ).count()
        if clash:
            db.session.rollback()
            return jsonify(ok=False, message="Sorry, that time was just booked. Please choose another time.",
                           errors={"time": "This time is no longer available."}), 409

    db.session.commit()
    emails.notify_new_appointment(appt)
    return jsonify(ok=True, reference=appt.reference, appointment=appt.to_dict()), 201


@api.get("/appointments/<reference>")
def lookup_appointment(reference):
    """Lets a patient check the status of a request with their reference and email."""
    email = (request.args.get("email") or "").strip().lower()
    appt = Appointment.query.filter_by(reference=reference.upper()).first()
    if not appt or appt.email != email:
        return jsonify(ok=False, message="No appointment found with that reference and email."), 404
    return jsonify(ok=True, appointment={k: v for k, v in appt.to_dict().items()
                                         if k in {"reference", "date", "time", "branch", "doctor", "service", "status"}})


@api.post("/contact")
def create_contact():
    body = payload()
    if body.get("website"):
        return jsonify(ok=True), 201
    limited = rate_limited("contact")
    if limited:
        return limited
    try:
        data = validate_contact(body)
    except ValidationError as e:
        return jsonify(ok=False, message=e.message, errors=e.errors), 400

    msg = ContactMessage(**data, ip_address=client_ip())
    db.session.add(msg)
    db.session.commit()
    emails.notify_contact(msg)
    return jsonify(ok=True), 201


@api.errorhandler(404)
def api_not_found(_e):
    return jsonify(ok=False, message="Not found"), 404


@api.errorhandler(405)
def api_method(_e):
    return jsonify(ok=False, message="Method not allowed"), 405
