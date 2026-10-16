"""Staff dashboard at /admin: review and manage appointments and messages."""
import csv
import io
import re
import secrets
from pathlib import Path
from datetime import date, timedelta
from functools import wraps

from flask import (Blueprint, Response, abort, current_app, flash, jsonify, redirect, render_template,
                   request, session, url_for)

from . import emails
from .media import UploadError, delete_media, save_upload
from .clinic_data import APPOINTMENT_STATUSES, BRANCHES, SERVICES
from .models import (AdminUser, Appointment, BlogPost, ContactMessage, Doctor, GalleryImage, ImageOverride,
                     MediaFile, db, utcnow)
from .services import clinic_now, limiter, parse_date

admin = Blueprint("admin", __name__, url_prefix="/admin", template_folder="templates")


# ---------------------------------------------------------------- auth + CSRF

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


@admin.app_context_processor
def inject():
    return {"csrf_token": csrf_token, "STATUSES": APPOINTMENT_STATUSES}


@admin.before_request
def check_csrf():
    if request.method == "POST":
        token = request.form.get("_csrf", "")
        if not token or not secrets.compare_digest(token, session.get("_csrf", "")):
            abort(400, "Invalid form token. Please reload the page and try again.")


@admin.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not limiter.allow(f"login:{request.remote_addr}", 10, window=900):
            flash("Too many attempts. Try again in 15 minutes.", "error")
            return render_template("admin/login.html"), 429
        user = AdminUser.query.filter_by(username=request.form.get("username", "").strip()).first()
        if user and user.check_password(request.form.get("password", "")):
            session.clear()
            session.permanent = True
            session["admin_id"] = user.id
            session["admin_name"] = user.username
            user.last_login_at = utcnow()
            db.session.commit()
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/admin") else url_for("admin.dashboard"))
        flash("Wrong username or password.", "error")
    return render_template("admin/login.html")


@admin.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


# ---------------------------------------------------------------- dashboard

@admin.get("/")
@login_required
def dashboard():
    today = clinic_now().date()
    active = Appointment.status.in_(["pending", "confirmed"])
    stats = {
        "pending": Appointment.query.filter_by(status="pending").count(),
        "today": Appointment.query.filter(Appointment.date == today, active).count(),
        "week": Appointment.query.filter(Appointment.date.between(today, today + timedelta(days=6)), active).count(),
        "unread": ContactMessage.query.filter_by(is_read=False).count(),
    }
    upcoming = (Appointment.query.filter(Appointment.date >= today, active)
                .order_by(Appointment.date, Appointment.time).limit(10).all())
    return render_template("admin/dashboard.html", stats=stats, upcoming=upcoming, today=today)


def filtered_appointments():
    q = Appointment.query
    f = {k: request.args.get(k, "") for k in ("status", "branch", "doctor", "from", "to", "q")}
    if f["status"]:
        q = q.filter_by(status=f["status"])
    if f["branch"]:
        q = q.filter_by(branch=f["branch"])
    if f["doctor"]:
        q = q.filter_by(doctor=f["doctor"])
    if parse_date(f["from"]):
        q = q.filter(Appointment.date >= parse_date(f["from"]))
    if parse_date(f["to"]):
        q = q.filter(Appointment.date <= parse_date(f["to"]))
    if f["q"]:
        like = f"%{f['q']}%"
        q = q.filter(db.or_(Appointment.first_name.ilike(like), Appointment.last_name.ilike(like),
                            Appointment.phone.ilike(like), Appointment.email.ilike(like),
                            Appointment.reference.ilike(like)))
    return q.order_by(Appointment.date.desc(), Appointment.time.desc()), f


@admin.get("/appointments")
@login_required
def appointments():
    q, f = filtered_appointments()
    page = q.paginate(page=request.args.get("page", 1, type=int), per_page=25, error_out=False)
    return render_template("admin/appointments.html", page=page, f=f,
                           doctors=Doctor.query.order_by(Doctor.sort_order, Doctor.id).all(), branches=BRANCHES)


@admin.get("/appointments/export.csv")
@login_required
def export_csv():
    q, _ = filtered_appointments()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Reference", "Date", "Time", "Status", "First name", "Last name", "Phone", "Email",
                "Service", "Branch", "Doctor", "Notes", "Staff notes", "Created (UTC)"])
    for a in q.all():
        w.writerow([a.reference, a.date.isoformat(), a.time, a.status, a.first_name, a.last_name, a.phone,
                    a.email, a.service_name, a.branch_name, a.doctor_name, a.notes or "", a.staff_notes or "",
                    a.created_at.strftime("%Y-%m-%d %H:%M")])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=appointments-{date.today()}.csv"})


@admin.route("/appointments/<int:appt_id>", methods=["GET", "POST"])
@login_required
def appointment_detail(appt_id):
    a = db.get_or_404(Appointment, appt_id)
    if request.method == "POST":
        status = request.form.get("status")
        changed = status in APPOINTMENT_STATUSES and status != a.status
        if changed:
            a.status = status
        a.staff_notes = (request.form.get("staff_notes") or "").strip()[:2000] or None
        db.session.commit()
        if changed and request.form.get("notify") == "on":
            emails.notify_status_change(a)
        flash("Appointment updated.", "success")
        return redirect(url_for("admin.appointment_detail", appt_id=a.id))
    return render_template("admin/appointment_detail.html", a=a, services=SERVICES)


# ---------------------------------------------------------------- messages

@admin.get("/messages")
@login_required
def messages():
    only_unread = request.args.get("unread") == "1"
    q = ContactMessage.query
    if only_unread:
        q = q.filter_by(is_read=False)
    page = q.order_by(ContactMessage.created_at.desc()).paginate(
        page=request.args.get("page", 1, type=int), per_page=25, error_out=False)
    return render_template("admin/messages.html", page=page, only_unread=only_unread)


@admin.post("/messages/<int:msg_id>/toggle")
@login_required
def toggle_message(msg_id):
    m = db.get_or_404(ContactMessage, msg_id)
    m.is_read = not m.is_read
    db.session.commit()
    return redirect(request.referrer or url_for("admin.messages"))


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


# ---------------------------------------------------------------- doctors

def unique_slug(name, ignore_id=None):
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "doctor"
    slug, n = base, 2
    while True:
        hit = Doctor.query.filter_by(slug=slug).first()
        if not hit or hit.id == ignore_id:
            return slug
        slug, n = f"{base}-{n}", n + 1


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


@admin.get("/doctors")
@login_required
def doctors():
    rows = Doctor.query.order_by(Doctor.sort_order, Doctor.id).all()
    booked = dict(db.session.query(Appointment.doctor, db.func.count(Appointment.id)).group_by(Appointment.doctor).all())
    return render_template("admin/doctors.html", doctors=rows, booked=booked)


@admin.post("/doctors/new")
@login_required
def doctor_new():
    name = (request.form.get("name") or "").strip()[:80]
    if not name:
        flash("Enter the doctor's name.", "error")
        return redirect(url_for("admin.doctors"))
    last = db.session.query(db.func.max(Doctor.sort_order)).scalar() or 0
    d = Doctor(slug=unique_slug(name), name=name, role=(request.form.get("role") or "").strip()[:80] or "Dermatology team",
               sort_order=last + 1)
    db.session.add(d)
    error = photo_from_form(d)
    if error:
        db.session.rollback()
        flash(error, "error")
        return redirect(url_for("admin.doctors"))
    db.session.commit()
    flash(f"{d.name} added. They now appear on the website and in the booking form.", "success")
    return redirect(url_for("admin.doctors"))


@admin.post("/doctors/<int:doctor_id>")
@login_required
def doctor_update(doctor_id):
    d = db.get_or_404(Doctor, doctor_id)
    name = (request.form.get("name") or "").strip()[:80]
    if not name:
        flash("The name cannot be empty.", "error")
        return redirect(url_for("admin.doctors"))
    d.name = name
    d.role = (request.form.get("role") or "").strip()[:80] or "Dermatology team"
    d.active = request.form.get("active") == "on"
    d.sort_order = request.form.get("sort_order", type=int) or 0
    error = photo_from_form(d)
    if error:
        db.session.rollback()
        flash(error, "error")
        return redirect(url_for("admin.doctors"))
    db.session.commit()
    flash(f"{d.name} saved.", "success")
    return redirect(url_for("admin.doctors"))


@admin.post("/doctors/<int:doctor_id>/delete")
@login_required
def doctor_delete(doctor_id):
    d = db.get_or_404(Doctor, doctor_id)
    if Appointment.query.filter_by(doctor=d.slug).count():
        flash("This doctor has appointments on record. Untick 'Show on website' instead of deleting.", "error")
        return redirect(url_for("admin.doctors"))
    old = d.photo_id
    db.session.delete(d)
    db.session.flush()
    delete_media(old)
    db.session.commit()
    flash("Doctor deleted.", "success")
    return redirect(url_for("admin.doctors"))


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
    """True if any doctor, gallery picture, replaced site picture or article still uses this upload."""
    if (Doctor.query.filter_by(photo_id=media_id).first() or GalleryImage.query.filter_by(media_id=media_id).first()
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
