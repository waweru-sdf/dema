"""Tests for the public website API, search-engine output and the content admin."""
import io
import json
import re

import pytest
from PIL import Image

from app import create_app
from app.config import TestConfig
from app.content_models import Condition, Doctor, Review
from app.models import AdminUser, db
from app.services import limiter

INDEX = ("<!doctype html><html><head><title>x</title><!--SEO_HEAD--></head>"
         "<body><div id='root'><!--SEO_BODY--></div></body></html>")


@pytest.fixture()
def app(tmp_path):
    (tmp_path / "index.html").write_text(INDEX)
    (tmp_path / "404.html").write_text("missing")
    (tmp_path / "assets" / "img" / "doctors").mkdir(parents=True)
    (tmp_path / "assets" / "img" / "doctors" / "feysel-alo.jpg").write_bytes(b"x")

    class Cfg(TestConfig):
        FRONTEND_DIR = str(tmp_path)

    limiter._hits.clear()
    app = create_app(Cfg)
    with app.app_context():
        u = AdminUser(username="staff")
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client):
    """Logs in as staff and returns the form token for the new session."""
    client.get("/admin/login")
    with client.session_transaction() as s:
        token = s["_csrf"]
    client.post("/admin/login", data={"username": "staff", "password": "password123", "_csrf": token})
    client.get("/admin/")
    with client.session_transaction() as s:
        return s["_csrf"]


def ld(html):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


# ---------------------------------------------------------------- public API

def test_starter_content_has_real_doctors_without_invented_credentials(client):
    docs = client.get("/api/site/doctors").get_json()["doctors"]
    assert len(docs) == 7 and docs[0]["name"] == "Dr. Feysel Alo"
    assert docs[0]["photo"] == "/assets/img/doctors/feysel-alo.jpg"
    detail = client.get("/api/site/doctors/feysel-alo").get_json()["doctor"]
    assert detail["qualifications"] == [] and detail["years_experience"] is None and detail["languages"] == []


def test_unknown_or_hidden_items_are_404(client, app):
    assert client.get("/api/site/doctors/nobody").status_code == 404
    with app.app_context():
        Doctor.query.filter_by(slug="zina-ahmed").one().published = False
        db.session.commit()
    assert client.get("/api/site/doctors/zina-ahmed").status_code == 404
    assert len(client.get("/api/site/doctors").get_json()["doctors"]) == 6


def test_condition_without_linked_doctors_shows_whole_team(client):
    cond = client.get("/api/site/conditions/acne").get_json()["condition"]
    assert len(cond["doctors"]) == 7
    assert cond["reviewed_by"] is None  # nobody is named as reviewer until staff choose one


def test_search_finds_conditions_and_doctors(client):
    r = client.get("/api/site/search?q=acne").get_json()
    assert any(c["slug"] == "acne" for c in r["conditions"])
    assert client.get("/api/site/search?q=feysel").get_json()["doctors"][0]["slug"] == "feysel-alo"
    assert client.get("/api/site/search?q=a").get_json()["conditions"] == []


# ---------------------------------------------------------------- reviews

def review(**kw):
    data = {"rating": 5, "body": "The doctor explained everything clearly and my skin is much better.", "age_group": "30s",
            "gender": "Woman", "consent": True, "condition": "acne", "doctor": "zina-ahmed"}
    data.update(kw)
    return data


def test_review_needs_consent_and_no_personal_details(client):
    r = client.post("/api/site/reviews", json=review(consent=False))
    assert r.status_code == 400 and "consent" in r.get_json()["errors"]
    r = client.post("/api/site/reviews", json=review(body="Call me on 0911 223 344 about how good it was."))
    assert r.status_code == 400 and "body" in r.get_json()["errors"]
    r = client.post("/api/site/reviews", json=review(body="Great care. Email me at abebe@example.com please."))
    assert r.status_code == 400
    assert client.post("/api/site/reviews", json=review(rating=9)).status_code == 400


def test_review_is_hidden_until_approved_and_shows_no_name(client, app):
    assert client.post("/api/site/reviews", json=review()).status_code == 201
    before = client.get("/api/site/reviews").get_json()["total"]
    tok = login(client)
    with app.app_context():
        rid = Review.query.filter_by(status="pending").one().id
        assert db.session.get(Review, rid).reviewer_label == "Woman, 30s"
    assert client.post(f"/admin/reviews/{rid}/approve", data={"_csrf": tok}).status_code == 302
    after = client.get("/api/site/reviews").get_json()
    assert after["total"] == before + 1
    assert after["reviews"][0]["reviewer"] == "Woman, 30s"


def test_review_filters_by_condition_treatment_and_doctor(client):
    r = client.get("/api/site/reviews?condition=vitiligo").get_json()
    assert r["total"] == 1 and r["reviews"][0]["condition"]["slug"] == "vitiligo"
    assert client.get("/api/site/reviews?treatment=PRP").get_json()["total"] == 1
    assert client.get("/api/site/reviews?doctor=zina-ahmed").get_json()["total"] == 2
    assert client.get("/api/site/reviews?condition=vitiligo&doctor=zina-ahmed").get_json()["total"] == 0


def test_admin_cannot_approve_review_with_phone_number(client, app):
    with app.app_context():
        r = Review(body="Wonderful, call 0911223344 for more.", rating=5, reviewer_label="Man, 20s", consent=True, status="pending")
        db.session.add(r)
        db.session.commit()
        rid = r.id
    tok = login(client)
    client.post(f"/admin/reviews/{rid}/approve", data={"_csrf": tok})
    with app.app_context():
        assert db.session.get(Review, rid).status == "pending"


def test_review_honeypot_and_rate_limit(client):
    assert client.post("/api/site/reviews", json=review(website="spam")).status_code == 201
    with client.application.app_context():
        assert Review.query.filter_by(status="pending").count() == 0
    for _ in range(5):
        client.post("/api/site/reviews", json=review())
    assert client.post("/api/site/reviews", json=review()).status_code == 429


# ---------------------------------------------------------------- search-engine output

def test_doctor_page_has_title_plain_html_and_physician_markup(client):
    html = client.get("/doctors/dagmawit-mitku").get_data(as_text=True)
    assert "<title>Dr. Dagmawit Mitku" in html and 'rel="canonical"' in html
    assert "<h1>Dr. Dagmawit Mitku</h1>" in html
    physician = [x for x in ld(html) if x["@type"] == "Physician"][0]
    assert physician["medicalSpecialty"] == "Dermatologic" and "hasCredential" not in physician  # nothing invented


def test_credentials_appear_as_visible_text_and_in_markup_once_entered(client, app):
    with app.app_context():
        d = Doctor.query.filter_by(slug="dagmawit-mitku").one()
        d.qualifications = "Board certification | Dermatology, 2016"
        d.languages = "English, Amharic"
        d.subspecialties = "Vitiligo"
        d.conditions = [Condition.query.filter_by(slug="vitiligo").one()]
        db.session.commit()
    html = client.get("/doctors/dagmawit-mitku").get_data(as_text=True)
    assert "Board certification: Dermatology, 2016" in html and "/conditions/vitiligo" in html
    p = [x for x in ld(html) if x["@type"] == "Physician"][0]
    assert p["hasCredential"][0]["name"] == "Board certification"
    assert p["knowsLanguage"] == ["English", "Amharic"] and "Vitiligo" in p["knowsAbout"]
    cond_html = client.get("/conditions/vitiligo").get_data(as_text=True)
    assert "/doctors/dagmawit-mitku" in cond_html


def test_condition_page_markup_and_reviewer_only_when_set(client, app):
    html = client.get("/conditions/vitiligo").get_data(as_text=True)
    types = [x["@type"] for x in ld(html)]
    assert "MedicalWebPage" in types and "FAQPage" in types and "BreadcrumbList" in types
    assert "Medically reviewed by" not in html
    with app.app_context():
        c = Condition.query.filter_by(slug="vitiligo").one()
        c.reviewed_by = Doctor.query.filter_by(slug="feysel-alo").one()
        from datetime import date
        c.reviewed_on = date(2026, 10, 1)
        db.session.commit()
    assert "Medically reviewed by Dr. Feysel Alo" in client.get("/conditions/vitiligo").get_data(as_text=True)


def test_no_rating_markup_while_only_sample_reviews_exist(client):
    html = client.get("/").get_data(as_text=True)
    assert "aggregateRating" not in html
    assert any(x["@type"] == ["MedicalClinic", "LocalBusiness"] for x in ld(html))


def test_unknown_page_is_a_real_404_and_old_pages_redirect(client):
    assert client.get("/doctors/nobody").status_code == 404
    assert client.get("/services.html").headers["Location"].endswith("/services")
    assert client.get("/about.html", follow_redirects=False).status_code == 301


def test_crawler_files(client):
    assert "Disallow: /admin" in client.get("/robots.txt").get_data(as_text=True)
    sm = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/doctors/feysel-alo" in sm and "/conditions/acne" in sm
    llms = client.get("/llms.txt").get_data(as_text=True)
    assert "Dr. Feysel Alo" in llms and "Tena Medicine" in llms


# ---------------------------------------------------------------- admin

def test_content_admin_requires_login(client):
    for path in ("/admin/content/doctors", "/admin/reviews", "/admin/site-settings", "/admin/content/doctors/1"):
        assert client.get(path).status_code == 302


def photo():
    buf = io.BytesIO()
    Image.new("RGB", (1600, 2000), (120, 160, 90)).save(buf, "PNG")
    buf.seek(0)
    return buf


def test_admin_edits_doctor_uploads_photo_and_links_conditions(client, app):
    tok = login(client)
    with app.app_context():
        d = Doctor.query.filter_by(slug="meti-fekadu").one()
        did, cid = d.id, Condition.query.filter_by(slug="acne").one().id
    assert client.get(f"/admin/content/doctors/{did}").status_code == 200
    r = client.post(f"/admin/content/doctors/{did}", data={
        "_csrf": tok, "name": "Dr. Meti Fekadu", "title": "Dermatologist", "branch": "bole", "years_experience": "8",
        "bio": "Bio text.", "qualifications": "MD | Addis Ababa University", "languages": "English, Amharic",
        "conditions": [str(cid)], "published": "on", "accepts_telemedicine": "on", "sort_order": "5",
        "photo": (photo(), "me.png")}, content_type="multipart/form-data")
    assert r.status_code == 302
    d = client.get("/api/site/doctors/meti-fekadu").get_json()["doctor"]
    assert d["years_experience"] == 8 and d["branch_name"] == "Bole branch" and d["languages"] == ["English", "Amharic"]
    assert d["conditions"][0]["slug"] == "acne" and d["photo"].startswith("/media/doctors/")
    img = client.get(d["photo"])
    assert img.status_code == 200 and img.mimetype == "image/jpeg"
    assert Image.open(io.BytesIO(img.data)).size[1] <= 1125  # resized


def test_admin_rejects_non_image_and_bad_numbers(client, app):
    tok = login(client)
    with app.app_context():
        did = Doctor.query.filter_by(slug="meti-fekadu").one().id
    r = client.post(f"/admin/content/doctors/{did}", data={"_csrf": tok, "name": "Dr. Meti Fekadu", "years_experience": "abc",
                    "photo": (io.BytesIO(b"not an image"), "x.png")}, content_type="multipart/form-data")
    assert r.status_code == 400
    assert client.get("/api/site/doctors/meti-fekadu").get_json()["doctor"]["years_experience"] is None


def png_bytes():
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), "#2A7421").save(buf, "PNG")
    return buf.getvalue()


def test_admin_creates_draft_then_publishes_with_cover(client):
    import io
    tok = login(client)
    data = {"_csrf": tok, "title": "Sun care in Addis", "category": "Skin care", "excerpt": "Short.",
            "body": "Para with **bold** and [a link](https://example.com).\n\n- one\n- two\n\n> quote\n\n1. first\n2. second"}
    assert client.post("/admin/blog/new", data=data).status_code == 302
    assert client.get("/api/site/posts/sun-care-in-addis").status_code == 404  # draft
    with client.application.app_context():
        from app.models import BlogPost
        pid = BlogPost.query.filter_by(slug="sun-care-in-addis").one().id
    r = client.post(f"/admin/blog/{pid}", data={**data, "published": "on", "photo": (io.BytesIO(png_bytes()), "c.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 302
    api = client.get("/api/site/posts/sun-care-in-addis").get_json()["post"]
    assert api["cover"].startswith("/media/") and client.get(api["cover"]).status_code == 200
    html = client.get("/blog/sun-care-in-addis").get_data(as_text=True)
    assert "<strong>bold</strong>" in html and '<a href="https://example.com">a link</a>' in html
    assert "<ol>" in html and "<blockquote>" in html and api["cover"] in html


def test_blog_body_is_escaped(client):
    tok = login(client)
    client.post("/admin/blog/new", data={"_csrf": tok, "title": "X", "excerpt": "e", "body": "<script>alert(1)</script>\n\n[x](javascript:alert(1))", "published": "on"})
    html = client.get("/blog/x").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html and 'href="javascript' not in html


def test_gallery_and_site_picture_override(client):
    import io
    tok = login(client)
    r = client.post("/admin/gallery/new", data={"_csrf": tok, "caption": "Reception", "photo": (io.BytesIO(png_bytes()), "g.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 302
    g = client.get("/api/site/gallery").get_json()["gallery"]
    assert g[0]["caption"] == "Reception" and client.get(g[0]["url"]).status_code == 200
    from pathlib import Path
    (Path(client.application.config["FRONTEND_DIR"]) / "assets" / "img" / "about.jpg").write_bytes(b"orig")
    r = client.post("/admin/images/replace", data={"_csrf": tok, "path": "assets/img/about.jpg", "photo": (io.BytesIO(png_bytes()), "a.png")},
                    content_type="multipart/form-data")
    assert r.status_code == 302
    got = client.get("/assets/img/about.jpg")
    assert got.status_code == 200 and got.mimetype in ("image/png", "image/jpeg") and len(got.data) < 5000


def test_legacy_doctor_rows_are_imported_once(app):
    from sqlalchemy import text
    from app.content_models import Doctor, Setting
    from app.content_seed import import_legacy_doctors
    from app.models import MediaFile, db
    with app.app_context():
        db.session.execute(text("CREATE TABLE doctors (slug TEXT, name TEXT, role TEXT, photo_id INT, active BOOL, sort_order INT)"))
        m = MediaFile(data=png_bytes(), mime="image/png", width=40, height=30)
        db.session.add(m)
        db.session.flush()
        db.session.execute(text("INSERT INTO doctors VALUES ('zina-ahmed','Dr. Zina Ahmed','Dermatologist',:p,1,1), ('new-doc','Dr. New Doc','Dermatology team',NULL,1,9)"), {"p": m.id})
        db.session.execute(text("DELETE FROM site_settings WHERE key='legacy_doctors_imported'"))
        db.session.commit()
        import_legacy_doctors()
        z = Doctor.query.filter_by(slug="zina-ahmed").one()
        assert z.photo_data and z.title == "Dermatologist"
        assert Doctor.query.filter_by(slug="new-doc").count() == 1
        import_legacy_doctors()
        assert Doctor.query.filter_by(slug="new-doc").count() == 1


def test_deleting_a_doctor_keeps_reviews_and_pages_working(client, app):
    tok = login(client)
    with app.app_context():
        did = Doctor.query.filter_by(slug="zina-ahmed").one().id
    assert client.post(f"/admin/content/doctors/{did}/delete", data={"_csrf": tok}).status_code == 302
    assert client.get("/api/site/reviews").get_json()["total"] == 6
    assert client.get("/").status_code == 200


def test_settings_validation_and_public_effect(client):
    tok = login(client)
    base = {"_csrf": tok, "telemedicine_url": "https://tena.example.com", "in_person_url": "/appointment", "price_chat": "900",
            "price_video_chat": "1800", "chat_days": "30", "email": "a@b.com", "phones": "0911 000 000", "site_url": ""}
    assert client.post("/admin/site-settings", data={**base, "price_chat": "free"}).status_code == 200
    assert client.get("/api/site/settings").get_json()["prices"]["chat"] == "800"
    client.post("/admin/site-settings", data={**base, "telemedicine_url": "javascript:alert(1)"})
    assert client.get("/api/site/settings").get_json()["telemedicine_url"] == "https://tena.marhiwotmch.com"
    client.post("/admin/site-settings", data=base)
    s = client.get("/api/site/settings").get_json()
    assert s["prices"] == {"chat": "900", "video_chat": "1800"} and s["telemedicine_url"] == "https://tena.example.com"
    assert "900 birr" in client.get("/telemedicine").get_data(as_text=True)


def test_site_url_setting_controls_canonical_and_sitemap(client):
    tok = login(client)
    client.post("/admin/site-settings", data={"_csrf": tok, "telemedicine_url": "https://t.example", "in_person_url": "/appointment",
                "price_chat": "800", "price_video_chat": "1500", "chat_days": "30", "email": "a@b.com", "phones": "1", "site_url": "https://www.clinic.example"})
    assert 'href="https://www.clinic.example/doctors/feysel-alo"' in client.get("/doctors/feysel-alo").get_data(as_text=True)
    assert "https://www.clinic.example/conditions/acne" in client.get("/sitemap.xml").get_data(as_text=True)


def test_staff_can_add_phone_appointment_once(client):
    from datetime import timedelta
    from app.services import clinic_now
    tok = login(client)
    with client.application.app_context():
        day = clinic_now().date() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    data = {"_csrf": tok, "first_name": "Abebe", "last_name": "Kebede", "phone": "0911223344", "service": "general-dermatology",
            "branch": "bole", "doctor": "zina-ahmed", "date": day.isoformat(), "time": "09:00", "status": "confirmed"}
    r = client.post("/admin/appointments/new", data=data)
    assert r.status_code == 302 and "/admin/appointments/" in r.headers["Location"]
    again = client.post("/admin/appointments/new", data=data)
    assert again.status_code == 200 and b"already taken" in again.data
    assert client.get("/admin/appointments/new").status_code == 200
