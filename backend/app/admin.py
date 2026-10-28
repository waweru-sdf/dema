"""Staff dashboard at /admin: review and manage appointments and messages."""
import csv
import io
import secrets
from datetime import date, timedelta
from functools import wraps

from flask import (Blueprint, Response, abort, flash, redirect, render_template, request, session,
                   url_for)

from . import emails
from .clinic_data import APPOINTMENT_STATUSES, BRANCHES, DOCTORS, SERVICES
from .models import AdminUser, Appointment, ContactMessage, db, utcnow
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
    from .content_models import Doctor, Review
    from .models import BlogPost
    incomplete = sum(1 for d in Doctor.query.filter_by(published=True).all() if not all(d.completeness.values()))
    attention = [
        dict(count=stats["pending"], label="Appointment requests to confirm", icon="calendar2-week", url=url_for("admin.appointments", status="pending")),
        dict(count=stats["unread"], label="Unread messages", icon="envelope", url=url_for("admin.messages", unread=1)),
        dict(count=Review.query.filter_by(status="pending").count(), label="Reviews waiting for approval", icon="chat-quote", url=url_for("admin.reviews_queue")),
        dict(count=BlogPost.query.filter_by(published=False).count(), label="Article drafts", icon="journal-text", url=url_for("admin.blog")),
        dict(count=incomplete, label="Doctor profiles with missing details", icon="person-badge", url=url_for("admin.content_list", kind="doctors")),
        dict(count=Review.query.filter_by(is_sample=True).count(), label="Sample reviews still showing", icon="exclamation-triangle", url=url_for("admin.reviews_queue")),
    ]
    return render_template("admin/dashboard.html", stats=stats, upcoming=upcoming, today=today, attention=attention)


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
                           doctors=DOCTORS, branches=BRANCHES)


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
