from datetime import timedelta

import pytest

from app import create_app
from app.config import TestConfig
from app.models import AdminUser, Appointment, ContactMessage, db
from app.services import clinic_now, limiter


@pytest.fixture()
def app(tmp_path):
    (tmp_path / "index.html").write_text("<h1>home</h1>")
    (tmp_path / "404.html").write_text("missing")
    (tmp_path / "about.html").write_text("about")

    class Cfg(TestConfig):
        FRONTEND_DIR = str(tmp_path)

    limiter._hits.clear()
    app = create_app(Cfg)
    with app.app_context():
        u = AdminUser(username="staff")
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def next_open_day(app, start_offset=1):
    with app.app_context():
        d = clinic_now().date() + timedelta(days=start_offset)
        while d.weekday() not in app.config["OPEN_WEEKDAYS"]:
            d += timedelta(days=1)
        return d


def booking(day, **kw):
    data = {
        "first_name": "Abebe", "last_name": "Kebede", "email": "abebe@example.com", "phone": "0911 223 344",
        "service": "general-dermatology", "branch": "bole", "doctor": "feysel-alo",
        "date": day.isoformat(), "time": "09:00", "notes": "Rash on arm",
    }
    data.update(kw)
    return data


# ---------------------------------------------------------------- frontend serving

def test_serves_frontend_and_clean_urls(client):
    assert b"home" in client.get("/").data
    assert client.get("/about").data == b"about"
    assert client.get("/derma.html").status_code == 301
    r = client.get("/does-not-exist")
    assert r.status_code == 404 and r.data == b"missing"


def test_path_traversal_blocked(client):
    assert client.get("/../config.py").status_code == 404


# ---------------------------------------------------------------- API

def test_meta(client):
    data = client.get("/api/meta").get_json()
    assert len(data["doctors"]) == 7 and data["services"] and data["branches"]


def test_book_and_slot_becomes_unavailable(app, client):
    day = next_open_day(app)
    r = client.post("/api/appointments", json=booking(day))
    assert r.status_code == 201, r.get_json()
    ref = r.get_json()["reference"]
    assert ref.startswith("FD-")

    slots = client.get(f"/api/availability?date={day}&doctor=feysel-alo&branch=bole").get_json()["slots"]
    assert {s["time"]: s["available"] for s in slots}["09:00"] is False

    # Same doctor, same slot -> conflict
    r2 = client.post("/api/appointments", json=booking(day, email="other@example.com"))
    assert r2.status_code == 409

    # Different doctor, same slot -> fine
    r3 = client.post("/api/appointments", json=booking(day, doctor="zina-ahmed"))
    assert r3.status_code == 201

    # Patient lookup
    look = client.get(f"/api/appointments/{ref}?email=abebe@example.com").get_json()
    assert look["appointment"]["status"] == "pending"
    assert client.get(f"/api/appointments/{ref}?email=wrong@example.com").status_code == 404


def test_branch_capacity_for_any_doctor(app, client):
    day = next_open_day(app)
    cap = app.config["BRANCH_SLOT_CAPACITY"]
    for i in range(cap):
        assert client.post("/api/appointments", json=booking(day, doctor="", time="10:00",
                                                             email=f"p{i}@example.com")).status_code == 201
    r = client.post("/api/appointments", json=booking(day, doctor="", time="10:00"))
    assert r.status_code == 409


def test_validation_errors(app, client):
    day = next_open_day(app)
    r = client.post("/api/appointments", json=booking(day, email="bad", phone="12", service="x", time="03:00"))
    assert r.status_code == 400
    errs = r.get_json()["errors"]
    assert {"email", "phone", "service", "time"} <= set(errs)


def test_past_and_closed_dates_rejected(app, client):
    with app.app_context():
        yesterday = clinic_now().date() - timedelta(days=1)
    assert "date" in client.post("/api/appointments", json=booking(yesterday)).get_json()["errors"]

    closed = next_open_day(app)
    while closed.weekday() in app.config["OPEN_WEEKDAYS"]:
        closed += timedelta(days=1)
    assert client.get(f"/api/availability?date={closed}").get_json()["closed"] is True


def test_honeypot(client, app):
    r = client.post("/api/appointments", json={"website": "spam"})
    assert r.status_code == 201
    with app.app_context():
        assert Appointment.query.count() == 0


def test_contact(client, app):
    assert client.post("/api/contact", json={"name": "A", "email": "a@b.co", "subject": "Hi",
                                              "message": "Hello there"}).status_code == 201
    assert client.post("/api/contact", json={"name": "", "email": "x"}).status_code == 400
    with app.app_context():
        assert ContactMessage.query.count() == 1


def test_rate_limit(app, client):
    app.config["RATE_LIMIT_PER_HOUR"] = 2
    for _ in range(2):
        client.post("/api/contact", json={"name": "A", "email": "a@b.co", "subject": "Hi", "message": "Hello there"})
    r = client.post("/api/contact", json={"name": "A", "email": "a@b.co", "subject": "Hi", "message": "Hello there"})
    assert r.status_code == 429


# ---------------------------------------------------------------- admin

def login(client):
    client.get("/admin/login")
    with client.session_transaction() as s:
        token = s["_csrf"]
    r = client.post("/admin/login", data={"username": "staff", "password": "password123", "_csrf": token})
    client.get("/admin/")  # login starts a fresh session, so fetch the new form token
    with client.session_transaction() as s:
        token = s["_csrf"]
    return r, token


def test_admin_requires_login(client):
    assert client.get("/admin/").status_code == 302


def test_admin_csrf_required(client):
    client.get("/admin/login")
    assert client.post("/admin/login", data={"username": "staff", "password": "password123"}).status_code == 400


def test_admin_flow(app, client):
    day = next_open_day(app)
    client.post("/api/appointments", json=booking(day))
    r, token = login(client)
    assert r.status_code == 302
    assert b"Pending requests" in client.get("/admin/").data
    assert b"Abebe" in client.get("/admin/appointments?status=pending").data

    with app.app_context():
        appt_id = Appointment.query.first().id
    r = client.post(f"/admin/appointments/{appt_id}", data={"status": "confirmed", "staff_notes": "Called",
                                                            "_csrf": token}, follow_redirects=True)
    assert b"Appointment updated" in r.data
    with app.app_context():
        assert db.session.get(Appointment, appt_id).status == "confirmed"

    csv_data = client.get("/admin/appointments/export.csv").data.decode()
    assert "Abebe" in csv_data and "confirmed" in csv_data


def test_admin_wrong_password(client):
    client.get("/admin/login")
    with client.session_transaction() as s:
        token = s["_csrf"]
    r = client.post("/admin/login", data={"username": "staff", "password": "nope", "_csrf": token})
    assert b"Wrong username or password" in r.data


def test_admin_created_from_env(tmp_path):
    class Cfg(TestConfig):
        FRONTEND_DIR = str(tmp_path)
        ADMIN_USERNAME = "boss"
        ADMIN_PASSWORD = "supersecret1"

    app = create_app(Cfg)
    with app.app_context():
        assert AdminUser.query.filter_by(username="boss").first().check_password("supersecret1")


def test_database_url_normalised(monkeypatch):
    from app import config
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host/db?sslmode=require")
    assert config._database_url() == "postgresql+psycopg://u:p@host/db?sslmode=require"
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
    assert config._database_url().startswith("postgresql+psycopg://")
