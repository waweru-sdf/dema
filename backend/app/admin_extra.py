"""Admin pages for pictures and the blog: site pictures, gallery and the article editor.

Pictures are stored in the database (MediaFile) so they survive Render's reset-on-deploy disk.
"""
import re
from pathlib import Path

from flask import abort, current_app, flash, jsonify, redirect, render_template, request, url_for

from .admin import admin, login_required
from .media import UploadError, delete_media, save_upload
from .models import BlogPost, GalleryImage, ImageOverride, db, utcnow

# ---------------------------------------------------------------- website pictures

SITE_IMAGE_LABELS = {
    "logo.png": "Logo (header and footer)",
    "hero-poster.jpg": "Home page banner picture (shown before the video plays)",
    "page-hero.jpg": "Banner behind page titles (About, Services, Contact...)",
    "about.jpg": "Home page: About section",
    "why-us.jpg": "Home page: Why choose us",
}


def site_images():
    """Every replaceable picture shipped with the website (doctors and gallery have their own pages)."""
    root = Path(current_app.config["FRONTEND_DIR"]) / "assets" / "img"
    overridden = {o.path: o for o in ImageOverride.query.all()}
    items = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        rel = f.relative_to(root).as_posix()
        if rel.startswith(("doctors/", "gallery/")):
            continue
        path = f"assets/img/{rel}"
        group = "Service pictures" if rel.startswith("services/") else "Page pictures"
        title = SITE_IMAGE_LABELS.get(rel) or rel.rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("-", " ").capitalize()
        items.append({"path": path, "title": title, "group": group,
                      "url": "/" + path, "changed": path in overridden})
    return items


@admin.app_errorhandler(413)
def too_large(_e):
    if request.path.startswith("/admin"):
        flash("That upload is too large (8 MB maximum).", "error")
        return redirect(request.referrer or url_for("admin.dashboard"))
    return "Request too large", 413


@admin.get("/images")
@login_required
def images():
    return render_template("admin/images.html", items=site_images())


@admin.post("/images/replace")
@login_required
def image_replace():
    path = request.form.get("path", "")
    if path not in {i["path"] for i in site_images()}:
        abort(404)
    try:
        media = save_upload(request.files.get("photo"))
    except UploadError as e:
        flash(str(e), "error")
        return redirect(url_for("admin.images"))
    row = ImageOverride.query.filter_by(path=path).first()
    if row:
        old = row.media_id
        row.media_id = media.id
        db.session.flush()
        delete_media(old)
    else:
        db.session.add(ImageOverride(path=path, media_id=media.id))
    db.session.commit()
    flash("Picture replaced. Visitors see it within a few minutes.", "success")
    return redirect(url_for("admin.images"))


@admin.post("/images/reset")
@login_required
def image_reset():
    row = ImageOverride.query.filter_by(path=request.form.get("path", "")).first_or_404()
    old = row.media_id
    db.session.delete(row)
    db.session.flush()
    delete_media(old)
    db.session.commit()
    flash("Original picture restored.", "success")
    return redirect(url_for("admin.images"))




def photo_from_form(doctor_or_item, attr="photo_id"):
    """Apply an uploaded photo to a Doctor/GalleryImage. Returns an error text or None."""
    file = request.files.get("photo")
    if not file or not file.filename:
        return None
    try:
        media = save_upload(file)
    except UploadError as e:
        return str(e)
    old = getattr(doctor_or_item, attr)
    setattr(doctor_or_item, attr, media.id)
    db.session.flush()
    delete_media(old)
    return None


# ---------------------------------------------------------------- gallery

@admin.get("/gallery")
@login_required
def gallery():
    rows = GalleryImage.query.order_by(GalleryImage.sort_order, GalleryImage.id).all()
    return render_template("admin/gallery.html", rows=rows)


@admin.post("/gallery/new")
@login_required
def gallery_new():
    try:
        media = save_upload(request.files.get("photo"))
    except UploadError as e:
        flash(str(e), "error")
        return redirect(url_for("admin.gallery"))
    last = db.session.query(db.func.max(GalleryImage.sort_order)).scalar() or 0
    db.session.add(GalleryImage(media_id=media.id, sort_order=last + 1,
                                caption=(request.form.get("caption") or "").strip()[:150] or "Clinic photo"))
    db.session.commit()
    flash("Picture added to the gallery.", "success")
    return redirect(url_for("admin.gallery"))


@admin.post("/gallery/<int:image_id>")
@login_required
def gallery_update(image_id):
    g = db.get_or_404(GalleryImage, image_id)
    g.caption = (request.form.get("caption") or "").strip()[:150] or "Clinic photo"
    g.sort_order = request.form.get("sort_order", type=int) or 0
    error = photo_from_form(g, "media_id")
    if error:
        db.session.rollback()
        flash(error, "error")
    else:
        db.session.commit()
        flash("Gallery picture saved.", "success")
    return redirect(url_for("admin.gallery"))


@admin.post("/gallery/<int:image_id>/delete")
@login_required
def gallery_delete(image_id):
    g = db.get_or_404(GalleryImage, image_id)
    old = g.media_id
    db.session.delete(g)
    db.session.flush()
    delete_media(old)
    db.session.commit()
    flash("Picture removed from the gallery.", "success")
    return redirect(url_for("admin.gallery"))


# ---------------------------------------------------------------- blog

def post_slug(title, ignore_id=None):
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:70] or "post"
    slug, n = base, 2
    while True:
        hit = BlogPost.query.filter_by(slug=slug).first()
        if not hit or hit.id == ignore_id:
            return slug
        slug, n = f"{base}-{n}", n + 1


MEDIA_REF = re.compile(r"/media/(\d+)")


def plain_excerpt(body, n=200):
    """First words of an article without the formatting marks."""
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)|@\[\w+\]\([^)]*\)", " ", body)       # pictures and videos
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)                             # links keep their text
    t = re.sub(r"^(#{1,3} |[-*] |\d+[.)] |> ?|---+$)", "", t, flags=re.M)
    t = re.sub(r"[*_]{1,2}", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:n].rstrip() + ("..." if len(t) > n else "")


def media_in_use(media_id):
    """True if any gallery picture, replaced site picture or article still uses this upload."""
    if (GalleryImage.query.filter_by(media_id=media_id).first()
            or ImageOverride.query.filter_by(media_id=media_id).first()
            or BlogPost.query.filter_by(cover_id=media_id).first()):
        return True
    needle = f"/media/{media_id}"
    return any(re.search(re.escape(needle) + r"(?!\d)", b) for (b,) in db.session.query(BlogPost.body).all())


def drop_unused_media(ids):
    for i in set(ids):
        if not media_in_use(i):
            delete_media(i)


def body_media_ids(body):
    return {int(i) for i in MEDIA_REF.findall(body or "")}


@admin.post("/blog/image")
@login_required
def blog_image():
    """Editor button: upload a picture and get back the text to paste into the article."""
    try:
        media = save_upload(request.files.get("photo"))
    except UploadError as e:
        return jsonify(ok=False, message=str(e)), 400
    db.session.commit()
    return jsonify(ok=True, url=f"/media/{media.id}")


def blog_categories():
    return [c for (c,) in db.session.query(BlogPost.category).distinct().order_by(BlogPost.category).all()]


@admin.get("/blog")
@login_required
def blog():
    rows = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template("admin/blog.html", rows=rows)


@admin.route("/blog/new", methods=["GET", "POST"])
@admin.route("/blog/<int:post_id>", methods=["GET", "POST"])
@login_required
def blog_edit(post_id=None):
    post = db.get_or_404(BlogPost, post_id) if post_id else None
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()[:150]
        body = (request.form.get("body") or "").replace("\r\n", "\n").strip()
        form = {"title": title, "category": (request.form.get("category") or "").strip()[:60] or "General",
                "excerpt": (request.form.get("excerpt") or "").strip()[:300], "body": body,
                "published": request.form.get("published") == "on"}
        if not title or not body:
            flash("A post needs a title and some text.", "error")
            return render_template("admin/blog_edit.html", post=post, form=form, categories=blog_categories()), 400
        new = post is None
        old_ids = set() if new else body_media_ids(post.body)
        if new:
            post = BlogPost(slug=post_slug(title))
            db.session.add(post)
        post.title, post.category, post.excerpt, post.body = title, form["category"], form["excerpt"], body
        if not post.excerpt:  # fall back to the first words of the text
            post.excerpt = plain_excerpt(body)
        if form["published"] and not post.published_at:
            post.published_at = utcnow()
        post.published = form["published"]
        error = photo_from_form(post, "cover_id")
        if error:
            db.session.rollback()
            flash(error, "error")
            return render_template("admin/blog_edit.html", post=None if new else post, form=form,
                                   categories=blog_categories()), 400
        if request.form.get("remove_cover") == "on" and not request.files.get("photo", None):
            old, post.cover_id = post.cover_id, None
            db.session.flush()
            delete_media(old)
        db.session.flush()
        drop_unused_media(old_ids - body_media_ids(body))  # pictures taken out of the text
        db.session.commit()
        flash("Post saved and live." if post.published else "Draft saved. It is not on the website yet.", "success")
        return redirect(url_for("admin.blog"))
    form = None
    if post:
        form = {"title": post.title, "category": post.category, "excerpt": post.excerpt, "body": post.body,
                "published": post.published}
    return render_template("admin/blog_edit.html", post=post, form=form, categories=blog_categories())


@admin.post("/blog/<int:post_id>/delete")
@login_required
def blog_delete(post_id):
    post = db.get_or_404(BlogPost, post_id)
    old_cover, inline = post.cover_id, body_media_ids(post.body)
    db.session.delete(post)
    db.session.flush()
    delete_media(old_cover)
    drop_unused_media(inline)
    db.session.commit()
    flash("Post deleted.", "success")
    return redirect(url_for("admin.blog"))


# ---------------------------------------------------------------- staff-entered appointments (phone calls and walk-ins)

@admin.route("/appointments/new", methods=["GET", "POST"])
@login_required
def appointment_new():
    from .clinic_data import APPOINTMENT_STATUSES, BRANCHES, SERVICES
    from .content_models import Doctor
    from .models import Appointment
    from .services import SlotTakenError, ValidationError, validate_appointment
    doctors = [(d.slug, d.name) for d in Doctor.query.filter_by(published=True).order_by(Doctor.sort_order, Doctor.name)]
    form, errors = {}, {}
    if request.method == "POST":
        form = {k: (request.form.get(k) or "").strip() for k in
                ("first_name", "last_name", "email", "phone", "service", "branch", "doctor", "date", "time", "notes", "status")}
        if not form["email"]:  # phone and walk-in patients often have no email; keep the record valid
            form["email"] = "no-email@clinic.local"
        try:
            data = validate_appointment(form)
            appt = Appointment(**data, ip_address="staff", status=form["status"] if form["status"] in APPOINTMENT_STATUSES else "confirmed",
                               staff_notes="Entered by staff")
            db.session.add(appt)
            db.session.commit()
            flash(f"Appointment {appt.reference} added.", "success")
            return redirect(url_for("admin.appointment_detail", appt_id=appt.id))
        except ValidationError as e:
            errors = e.errors
            flash(e.message, "error")
        except SlotTakenError:
            errors = {"time": "This time is already taken."}
            flash("That time is already taken for this doctor or branch.", "error")
        if form.get("email") == "no-email@clinic.local":
            form["email"] = ""
    slots = current_app.config["APPOINTMENT_SLOTS"]
    return render_template("admin/appointment_new.html", form=form, errors=errors, doctors=doctors, services=SERVICES,
                           branches=BRANCHES, slots=slots, statuses=APPOINTMENT_STATUSES)
