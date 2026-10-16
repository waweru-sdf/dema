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


# ---------------------------------------------------------------- blog

def write_post(staff, **kw):
    data = {"title": "Sun care tips", "category": "Skin care", "excerpt": "", "body": "Wear sunscreen.\n\n## Why\n\nUV harms skin.",
            "published": "on"}
    data.update(kw)
    data = {k: v for k, v in data.items() if v is not None}
    return post(staff, "/admin/blog/new", **data)


def test_blog_needs_login_and_is_empty_at_first(app):
    c = app.test_client()
    assert c.get("/admin/blog").status_code == 302
    assert c.get("/api/posts").get_json() == {"posts": [], "categories": []}
    assert c.get("/api/posts/nope").status_code == 404


def test_publish_post_shows_in_api(app, staff):
    r = write_post(staff, photo=(png(), "cover.png"))
    assert b"Post saved and live" in r.data
    data = app.test_client().get("/api/posts").get_json()
    assert data["categories"] == ["Skin care"]
    p = data["posts"][0]
    assert p["slug"] == "sun-care-tips" and p["published_at"] and p["cover"].startswith("/media/")
    assert p["excerpt"].startswith("Wear sunscreen.") and "body" not in p
    full = app.test_client().get("/api/posts/sun-care-tips").get_json()["post"]
    assert "## Why" in full["body"]


def test_draft_is_hidden_until_published(app, staff):
    write_post(staff, published=None)
    c = app.test_client()
    assert c.get("/api/posts").get_json()["posts"] == []
    assert c.get("/api/posts/sun-care-tips").status_code == 404
    with app.app_context():
        from app.models import BlogPost
        pid = BlogPost.query.one().id
    post(staff, f"/admin/blog/{pid}", title="Sun care tips", category="Skin care", body="Text", published="on")
    assert len(c.get("/api/posts").get_json()["posts"]) == 1
    post(staff, f"/admin/blog/{pid}", title="Sun care tips", category="Skin care", body="Text")  # unpublish
    assert c.get("/api/posts").get_json()["posts"] == []


def test_category_filter_limit_and_unique_slugs(app, staff):
    write_post(staff, title="One", category="Hair")
    write_post(staff, title="One", category="Cosmetic")
    write_post(staff, title="Three", category="Hair")
    c = app.test_client()
    assert sorted(c.get("/api/posts").get_json()["categories"]) == ["Cosmetic", "Hair"]
    assert len(c.get("/api/posts?category=Hair").get_json()["posts"]) == 2
    assert len(c.get("/api/posts?limit=1").get_json()["posts"]) == 1
    assert sorted(p["slug"] for p in c.get("/api/posts").get_json()["posts"]) == ["one", "one-2", "three"]


def test_post_validation_and_edit_keeps_slug(app, staff):
    assert b"needs a title" in write_post(staff, title="", body="x").data
    write_post(staff)
    with app.app_context():
        from app.models import BlogPost
        pid = BlogPost.query.one().id
    post(staff, f"/admin/blog/{pid}", title="Totally new title", category="News", body="Changed", published="on")
    got = app.test_client().get("/api/posts/sun-care-tips").get_json()["post"]
    assert got["title"] == "Totally new title" and got["body"] == "Changed", "link must stay the same after editing"


def test_remove_cover_and_delete_clean_up_pictures(app, staff):
    write_post(staff, photo=(png(), "c.png"))
    with app.app_context():
        from app.models import BlogPost
        pid = BlogPost.query.one().id
        assert MediaFile.query.count() == 1
    post(staff, f"/admin/blog/{pid}", title="Sun care tips", category="Skin care", body="x", published="on", remove_cover="on")
    with app.app_context():
        assert MediaFile.query.count() == 0
    post(staff, f"/admin/blog/{pid}", title="Sun care tips", category="Skin care", body="x", published="on", photo=(png(), "c.png"))
    post(staff, f"/admin/blog/{pid}/delete")
    with app.app_context():
        assert BlogPost.query.count() == 0 and MediaFile.query.count() == 0


def test_blog_urls_serve_pages(app, tmp_path):
    (tmp_path / "x").mkdir(exist_ok=True)
    site = app.config["FRONTEND_DIR"]
    from pathlib import Path
    Path(site, "post.html").write_text("ARTICLE PAGE")
    Path(site, "blog.html").write_text("BLOG LIST")
    c = app.test_client()
    assert c.get("/blog/anything-here").data == b"ARTICLE PAGE"
    assert c.get("/blog").data == b"BLOG LIST"


# ---------------------------------------------------------------- flexible blog

def seeded_app(tmp_path, with_covers):
    site = tmp_path / "seedsite"
    (site / "assets" / "img" / "services").mkdir(parents=True)
    (site / "index.html").write_text("home")
    if with_covers:
        for n in ("cancer-screening", "hair-nail", "hydrafacial"):
            Image.new("RGB", (60, 40), (10, 120, 60)).save(site / "assets" / "img" / "services" / f"{n}.jpg")

    class Cfg(TestConfig):
        FRONTEND_DIR = str(site)
        SEED_SAMPLE_POSTS = True

    limiter._hits.clear()
    return create_app(Cfg)


def test_blog_starts_with_three_sample_posts_with_covers(tmp_path):
    app = seeded_app(tmp_path, with_covers=True)
    data = app.test_client().get("/api/posts").get_json()
    assert len(data["posts"]) == 3
    assert sorted(data["categories"]) == ["Cosmetic", "Hair and nails", "Skin care"]
    assert all(p["cover"].startswith("/media/") and p["read_minutes"] >= 1 and p["published_at"] for p in data["posts"])
    assert data["posts"][0]["published_at"] > data["posts"][-1]["published_at"], "newest first"
    body = app.test_client().get("/api/posts/your-first-cosmetic-dermatology-visit").get_json()["post"]["body"]
    assert "![" in body and "1. " in body and "**" in body


def test_samples_survive_restart_without_duplicates_and_missing_covers_are_ok(tmp_path):
    app = seeded_app(tmp_path, with_covers=False)
    posts = app.test_client().get("/api/posts").get_json()["posts"]
    assert len(posts) == 3 and all(p["cover"] is None for p in posts)
    from app.blog_seed import seed_sample_posts
    with app.app_context():
        seed_sample_posts(app.config["FRONTEND_DIR"])
        from app.models import BlogPost
        assert BlogPost.query.count() == 3


def test_inline_picture_upload_and_cleanup(app, staff):
    with staff.session_transaction() as s:
        token = s["_csrf"]
    r = staff.post("/admin/blog/image", data={"photo": (png(), "in.png"), "_csrf": token}, content_type="multipart/form-data")
    url = r.get_json()["url"]
    assert r.get_json()["ok"] and url.startswith("/media/")
    bad = staff.post("/admin/blog/image", data={"photo": (io.BytesIO(b"x"), "x.png"), "_csrf": token}, content_type="multipart/form-data")
    assert bad.status_code == 400 and not bad.get_json()["ok"]

    write_post(staff, body=f"Intro\n\n![Caption]({url})")
    assert app.test_client().get(url).status_code == 200
    with app.app_context():
        from app.models import BlogPost
        pid = BlogPost.query.one().id
    post(staff, f"/admin/blog/{pid}", title="Sun care tips", category="Skin care", body="Text only now", published="on")
    assert app.test_client().get(url).status_code == 404, "picture removed from the text is deleted"


def test_deleting_a_post_never_deletes_pictures_used_elsewhere(app, staff):
    post(staff, "/admin/doctors/new", name="Dr. Pic", photo=(png(), "d.png"))
    with app.app_context():
        photo = Doctor.query.filter_by(slug="dr-pic").one().photo_url
    write_post(staff, body=f"Sneaky\n\n![x]({photo})")
    with app.app_context():
        from app.models import BlogPost
        pid = BlogPost.query.one().id
    post(staff, f"/admin/blog/{pid}/delete")
    assert app.test_client().get(photo).status_code == 200


def test_excerpt_drops_formatting_marks(app, staff):
    write_post(staff, body="## Title line\n\n![cap](/media/9)\n\nSome **bold** words and a [link](/appointment.html).\n\n- item")
    ex = app.test_client().get("/api/posts").get_json()["posts"][0]["excerpt"]
    assert ex == "Title line Some bold words and a link. item"
