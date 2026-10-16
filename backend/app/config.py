"""Application settings. Values come from environment variables (see .env.example)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _list(name, default=""):
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


def _database_url():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{BASE_DIR / 'instance' / 'clinic.db'}"
    # Hosts such as Neon/Render give "postgres://" or "postgresql://"; SQLAlchemy + psycopg 3 needs this prefix.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def _frontend_dir():
    if os.getenv("FRONTEND_DIR"):
        return os.getenv("FRONTEND_DIR")
    # Repo layout: dema/frontend next to dema/backend. Fall back to backend/frontend if present.
    inside = BASE_DIR / "frontend"
    return str(inside if inside.exists() else BASE_DIR.parent / "frontend")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

    # Database: SQLite by default, any SQLAlchemy URL works (e.g. PostgreSQL, MySQL).
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Cloud Postgres closes idle connections; check them before use.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Where the static frontend lives. Flask serves it at "/".
    FRONTEND_DIR = _frontend_dir()

    # CORS: only needed when the frontend is hosted on a different domain.
    CORS_ORIGINS = _list("CORS_ORIGINS")

    # Clinic schedule
    CLINIC_TIMEZONE = os.getenv("CLINIC_TIMEZONE", "Africa/Addis_Ababa")
    OPEN_WEEKDAYS = [int(d) for d in _list("OPEN_WEEKDAYS", "0,1,2,3,4,5")]  # Monday=0 ... Sunday=6
    APPOINTMENT_SLOTS = _list(
        "APPOINTMENT_SLOTS",
        "08:30,09:00,09:30,10:00,10:30,11:00,11:30,12:00,14:00,14:30,15:00,15:30,16:00,16:30",
    )
    # How many "any doctor" bookings a branch can take in the same slot.
    BRANCH_SLOT_CAPACITY = int(os.getenv("BRANCH_SLOT_CAPACITY", "3"))
    MAX_DAYS_AHEAD = int(os.getenv("MAX_DAYS_AHEAD", "90"))

    # First staff login, created automatically on start-up if it does not exist yet.
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

    # Email (optional). Use EITHER Brevo (HTTPS API, works on Render's free plan)
    # OR SMTP (MAIL_SERVER). Leave both empty to disable sending.
    BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = _bool("MAIL_USE_TLS", True)
    MAIL_USE_SSL = _bool("MAIL_USE_SSL", False)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_SENDER = os.getenv("MAIL_SENDER", "Dr. Feysel Dermatology <no-reply@drfeyseldermatology.com>")
    CLINIC_NOTIFY_EMAIL = os.getenv("CLINIC_NOTIFY_EMAIL", "Feyselclinic@gmail.com")
    SEND_PATIENT_CONFIRMATION = _bool("SEND_PATIENT_CONFIRMATION", True)

    # Simple rate limit for public form submissions (per IP).
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "10"))

    # Session cookie hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8 hours

    JSON_SORT_KEYS = False

    # Put three example articles in the blog the first time it is empty, so the section never looks bare.
    SEED_SAMPLE_POSTS = _bool("SEED_SAMPLE_POSTS", True)


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    MAIL_SERVER = ""
    BREVO_API_KEY = ""
    ADMIN_USERNAME = ""
    RATE_LIMIT_PER_HOUR = 1000
    SEED_SAMPLE_POSTS = False
