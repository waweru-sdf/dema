"""Admin-editable website content: site pictures, doctors, gallery."""
import io

import pytest
from PIL import Image

from app import create_app
from app.config import TestConfig
from app.models import AdminUser, Appointment, Doctor, GalleryImage, ImageOverride, MediaFile, db
from app.services import limiter
from tests.test_app import booking, next_open_day


def png(size=(40, 30), color=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    buf.seek(0)
    return buf


@pytest.fixture()
def app(tmp_path):
    site = tmp_path / "site"
    (site / "assets" / "img" / "services").mkdir(parents=True)
    (site / "assets" / "img" / "doctors").mkdir()
    (site / "index.html").write_text("home")
    (site / "assets" / "img" / "about.jpg").write_bytes(b"ORIGINAL")
    (site / "assets" / "img" / "services" / "general.jpg").write_bytes(b"ORIGINAL")
    (site / "assets" / "img" / "doctors" / "feysel-alo.jpg").write_bytes(b"ORIGINAL")
    (site / "assets" / "img" / "notes.txt").write_text("not a picture")

    class Cfg(TestConfig):
        FRONTEND_DIR = str(site)

    limiter._hits.clear()
    app = create_app(Cfg)
    with app.app_context():
        u = AdminUser(username="staff")
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
    return app


@pytest.fixture()
def staff(app):
    c = app.test_client()
    c.get("/admin/login")
    with c.session_transaction() as s:
        token = s["_csrf"]
    c.post("/admin/login", data={"username": "staff", "password": "password123", "_csrf": token})
    c.get("/admin/")  # login starts a fresh session, so load a page to get the new form token
    return c


def post(client, url, **data):
    with client.session_transaction() as s:
        data["_csrf"] = s["_csrf"]
    return client.post(url, data=data, content_type="multipart/form-data", follow_redirects=True)


# ---------------------------------------------------------------- seeding + public API

def test_built_in_doctors_and_gallery_are_seeded(app):
    with app.app_context():
        assert Doctor.query.count() == 7
        assert GalleryImage.query.count() == 4
    data = app.test_client().get("/api/site").get_json()
    assert data["doctors"][0] == {"slug": "feysel-alo", "name": "Dr. Feysel Alo", "role": "Dermatology team",
                                  "photo": "assets/img/doctors/feysel-alo.jpg"}
    assert len(data["gallery"]) == 4


def test_restart_does_not_duplicate_seed(app):
    with app.app_context():
        from app import seed_content
        seed_content()
        assert Doctor.query.count() == 7


def test_content_pages_need_login(app):
    c = app.test_client()
    for url in ("/admin/images", "/admin/doctors", "/admin/gallery"):
        assert c.get(url).status_code == 302
    r = c.post("/admin/doctors/new", data={"name": "x"})
    assert r.status_code == 400  # CSRF check comes first


# ---------------------------------------------------------------- site pictures

def test_image_list_only_shows_replaceable_pictures(staff):
    html = staff.get("/admin/images").get_data(as_text=True)
    assert "assets/img/about.jpg" in html and "assets/img/services/general.jpg" in html
    assert "feysel-alo" not in html and "notes.txt" not in html


def test_replace_and_restore_picture(app, staff):
    assert app.test_client().get("/assets/img/about.jpg").data == b"ORIGINAL"
    r = post(staff, "/admin/images/replace", path="assets/img/about.jpg", photo=(png(), "new.png"))
    assert b"Picture replaced" in r.data
    served = app.test_client().get("/assets/img/about.jpg")
    assert served.mimetype in ("image/jpeg", "image/png") and served.data != b"ORIGINAL"
    assert Image.open(io.BytesIO(served.data)).size == (40, 30)

    post(staff, "/admin/images/replace", path="assets/img/about.jpg", photo=(png((10, 10)), "again.png"))
    with app.app_context():
        assert MediaFile.query.count() == 1, "old upload must be deleted when replaced"

    post(staff, "/admin/images/reset", path="assets/img/about.jpg")
    assert app.test_client().get("/assets/img/about.jpg").data == b"ORIGINAL"
    with app.app_context():
        assert ImageOverride.query.count() == 0 and MediaFile.query.count() == 0


def test_cannot_replace_arbitrary_paths(staff):
    r = post(staff, "/admin/images/replace", path="../../etc/passwd", photo=(png(), "x.png"))
    assert r.status_code == 404
    r = post(staff, "/admin/images/replace", path="assets/img/doctors/feysel-alo.jpg", photo=(png(), "x.png"))
    assert r.status_code == 404


def test_rejects_non_pictures_and_huge_pictures(app, staff):
    r = post(staff, "/admin/images/replace", path="assets/img/about.jpg", photo=(io.BytesIO(b"<script>alert(1)</script>"), "x.png"))
    assert b"not a picture" in r.data
    gif = io.BytesIO()
    Image.new("RGB", (5, 5)).save(gif, "GIF")
    gif.seek(0)
    r = post(staff, "/admin/images/replace", path="assets/img/about.jpg", photo=(gif, "x.gif"))
    assert b"JPG, PNG or WebP" in r.data
    r = post(staff, "/admin/images/replace", path="assets/img/about.jpg")
    assert b"Choose a picture" in r.data
    with app.app_context():
        assert MediaFile.query.count() == 0


def test_big_pictures_are_shrunk(app, staff):
    post(staff, "/admin/images/replace", path="assets/img/about.jpg", photo=(png((4000, 2000)), "big.png"))
    with app.app_context():
        m = MediaFile.query.one()
        assert max(m.width, m.height) == 1800


# ---------------------------------------------------------------- doctors

def test_add_doctor_appears_on_site_and_booking(app, staff):
    r = post(staff, "/admin/doctors/new", name="Dr. Sara Bekele", role="Pediatric dermatology", photo=(png(), "sara.png"))
    assert b"Sara Bekele added" in r.data
    data = app.test_client().get("/api/site").get_json()
    sara = data["doctors"][-1]
    assert sara["slug"] == "dr-sara-bekele" and sara["role"] == "Pediatric dermatology"
    assert sara["photo"].startswith("/media/")
    assert app.test_client().get(sara["photo"]).mimetype == "image/jpeg"
    meta = app.test_client().get("/api/meta").get_json()
    assert "dr-sara-bekele" in [d["slug"] for d in meta["doctors"]]

    day = next_open_day(app)
    r = app.test_client().post("/api/appointments", json=booking(day, doctor="dr-sara-bekele"))
    assert r.status_code == 201


def test_hidden_doctor_leaves_site_but_old_bookings_keep_the_name(app, staff):
    day = next_open_day(app)
    assert app.test_client().post("/api/appointments", json=booking(day)).status_code == 201
    with app.app_context():
        d = Doctor.query.filter_by(slug="feysel-alo").one()
        did = d.id
    post(staff, f"/admin/doctors/{did}", name="Dr. Feysel Alo", role="Dermatology team", sort_order="0")  # active unticked
    assert "feysel-alo" not in [d["slug"] for d in app.test_client().get("/api/site").get_json()["doctors"]]
    r = app.test_client().post("/api/appointments", json=booking(day, time="10:00"))
    assert r.status_code == 400 and "doctor" in r.get_json()["errors"]
    with app.app_context():
        assert Appointment.query.first().doctor_name == "Dr. Feysel Alo"


def test_edit_reorder_and_photo(app, staff):
    with app.app_context():
        did = Doctor.query.filter_by(slug="zina-ahmed").one().id
    post(staff, f"/admin/doctors/{did}", name="Dr. Zina A. Ahmed", role="Cosmetic lead", sort_order="-5",
         active="on", photo=(png(), "z.png"))
    first = app.test_client().get("/api/site").get_json()["doctors"][0]
    assert first["name"] == "Dr. Zina A. Ahmed" and first["role"] == "Cosmetic lead" and first["photo"].startswith("/media/")
    assert first["slug"] == "zina-ahmed", "slug must not change when renaming, bookings point at it"


def test_delete_doctor_only_without_appointments(app, staff):
    day = next_open_day(app)
    app.test_client().post("/api/appointments", json=booking(day))
    with app.app_context():
        used = Doctor.query.filter_by(slug="feysel-alo").one().id
        free = Doctor.query.filter_by(slug="meti-fekadu").one().id
    assert b"has appointments" in post(staff, f"/admin/doctors/{used}/delete").data
    assert b"Doctor deleted" in post(staff, f"/admin/doctors/{free}/delete").data
    with app.app_context():
        assert Doctor.query.count() == 6


def test_duplicate_names_get_unique_slugs(app, staff):
    post(staff, "/admin/doctors/new", name="Dr. Feysel Alo")
    with app.app_context():
        assert sorted(d.slug for d in Doctor.query.filter(Doctor.name == "Dr. Feysel Alo")) == ["dr-feysel-alo", "feysel-alo"]


# ---------------------------------------------------------------- gallery

def test_gallery_add_reorder_remove(app, staff):
    post(staff, "/admin/gallery/new", caption="Reception", photo=(png(), "r.png"))
    pics = app.test_client().get("/api/site").get_json()["gallery"]
    assert len(pics) == 5 and pics[-1]["caption"] == "Reception" and pics[-1]["url"].startswith("/media/")

    new_id = pics[-1]["id"]
    post(staff, f"/admin/gallery/{new_id}", caption="Waiting room", sort_order="0")
    assert app.test_client().get("/api/site").get_json()["gallery"][0]["caption"] == "Waiting room"

    post(staff, f"/admin/gallery/{new_id}/delete")
    assert len(app.test_client().get("/api/site").get_json()["gallery"]) == 4
    with app.app_context():
        assert MediaFile.query.count() == 0


def test_gallery_rejects_bad_upload(staff):
    r = post(staff, "/admin/gallery/new", photo=(io.BytesIO(b"nope"), "x.jpg"))
    assert b"not a picture" in r.data
