"""Business logic: validation, availability and rate limiting."""
import re
import threading
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from flask import current_app
from sqlalchemy import func

from .clinic_data import ACTIVE_STATUSES, BRANCH_BY_SLUG, DOCTOR_BY_SLUG, SERVICE_BY_SLUG
from .models import Appointment

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\+?[0-9\s-]{9,15}$")
NAME_RE = re.compile(r"^[^<>{}\[\]\\/]{1,}$")


class ValidationError(Exception):
    def __init__(self, errors, message="Please check the highlighted fields."):
        super().__init__(message)
        self.errors = errors
        self.message = message


class SlotTakenError(Exception):
    pass


# ---------------------------------------------------------------- helpers

def clinic_now():
    return datetime.now(ZoneInfo(current_app.config["CLINIC_TIMEZONE"]))


def _clean(payload, key, max_len):
    value = payload.get(key)
    if value is None:
        return ""
    return str(value).strip()[:max_len]


def is_open_day(d: date):
    return d.weekday() in current_app.config["OPEN_WEEKDAYS"]


# ---------------------------------------------------------------- availability

def availability(day: date, branch: str = "", doctor: str = ""):
    """Return the slot list for a day with an "available" flag per slot."""
    cfg = current_app.config
    if not is_open_day(day):
        return {"closed": True, "message": "The clinic is closed on this day. Please choose another date.", "slots": []}

    now = clinic_now()
    q = Appointment.query.filter(Appointment.date == day, Appointment.status.in_(ACTIVE_STATUSES))

    taken_by_doctor = set()
    if doctor:
        taken_by_doctor = {a.time for a in q.filter(Appointment.doctor == doctor).all()}

    branch_counts = {}
    if branch:
        rows = (q.filter(Appointment.branch == branch)
                .with_entities(Appointment.time, func.count(Appointment.id))
                .group_by(Appointment.time).all())
        branch_counts = dict(rows)

    slots = []
    for t in cfg["APPOINTMENT_SLOTS"]:
        available = True
        if day == now.date() and t <= now.strftime("%H:%M"):
            available = False
        if t in taken_by_doctor:
            available = False
        if branch and not doctor and branch_counts.get(t, 0) >= cfg["BRANCH_SLOT_CAPACITY"]:
            available = False
        slots.append({"time": t, "available": available})
    return {"closed": False, "slots": slots}


# ---------------------------------------------------------------- validation

def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _site_doctor_exists(slug):
    from .content_models import Doctor
    return Doctor.query.filter_by(slug=slug, published=True).first() is not None


def validate_appointment(payload):
    cfg = current_app.config
    errors = {}
    data = {
        "first_name": _clean(payload, "first_name", 60),
        "last_name": _clean(payload, "last_name", 60),
        "email": _clean(payload, "email", 120).lower(),
        "phone": _clean(payload, "phone", 20),
        "service": _clean(payload, "service", 40),
        "branch": _clean(payload, "branch", 40),
        "doctor": _clean(payload, "doctor", 40) or None,
        "time": _clean(payload, "time", 5),
        "notes": _clean(payload, "notes", 1000) or None,
    }

    for key in ("first_name", "last_name"):
        if not data[key]:
            errors[key] = "This field is required."
        elif not NAME_RE.match(data[key]):
            errors[key] = "Please remove special characters."
    if not EMAIL_RE.match(data["email"]):
        errors["email"] = "Enter a valid email address."
    if not PHONE_RE.match(data["phone"]):
        errors["phone"] = "Enter a valid phone number."
    if data["service"] not in SERVICE_BY_SLUG:
        errors["service"] = "Please choose a service."
    if data["branch"] not in BRANCH_BY_SLUG:
        errors["branch"] = "Please choose a branch."
    if data["doctor"] and data["doctor"] not in DOCTOR_BY_SLUG and not _site_doctor_exists(data["doctor"]):
        errors["doctor"] = "Please choose a doctor from the list."

    day = parse_date(payload.get("date"))
    today = clinic_now().date()
    if not day:
        errors["date"] = "Please choose a date."
    elif day < today:
        errors["date"] = "Please choose a date in the future."
    elif day > today + timedelta(days=cfg["MAX_DAYS_AHEAD"]):
        errors["date"] = f"Bookings open up to {cfg['MAX_DAYS_AHEAD']} days ahead."
    elif not is_open_day(day):
        errors["date"] = "The clinic is closed on this day."
    data["date"] = day

    if data["time"] not in cfg["APPOINTMENT_SLOTS"]:
        errors["time"] = "Please choose an appointment time."

    if errors:
        raise ValidationError(errors)

    slot = next(s for s in availability(day, data["branch"], data["doctor"] or "")["slots"] if s["time"] == data["time"])
    if not slot["available"]:
        raise SlotTakenError()
    return data


def validate_contact(payload):
    errors = {}
    data = {
        "name": _clean(payload, "name", 120),
        "email": _clean(payload, "email", 120).lower(),
        "subject": _clean(payload, "subject", 150),
        "message": _clean(payload, "message", 3000),
    }
    if not data["name"]:
        errors["name"] = "This field is required."
    if not EMAIL_RE.match(data["email"]):
        errors["email"] = "Enter a valid email address."
    if not data["subject"]:
        errors["subject"] = "This field is required."
    if len(data["message"]) < 5:
        errors["message"] = "Please write a short message."
    if errors:
        raise ValidationError(errors)
    return data


# ---------------------------------------------------------------- rate limiting

class RateLimiter:
    """In-memory sliding window limiter. Good for a single server process.
    For several workers or servers, swap for Flask-Limiter with Redis."""

    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key, limit, window=3600):
        now = time.time()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True


limiter = RateLimiter()
