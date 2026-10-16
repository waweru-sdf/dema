import secrets
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

from .clinic_data import label

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_reference():
    # Short, human friendly reference such as FD-7K2M9Q (no 0/O/1/I to avoid confusion)
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "FD-" + "".join(secrets.choice(alphabet) for _ in range(6))


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(12), unique=True, nullable=False, default=new_reference, index=True)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service = db.Column(db.String(40), nullable=False)
    branch = db.Column(db.String(40), nullable=False)
    doctor = db.Column(db.String(40), nullable=True)  # empty = any available doctor
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.String(5), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    staff_notes = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def doctor_name(self):
        if not self.doctor:
            return "Any available doctor"
        d = Doctor.query.filter_by(slug=self.doctor).first()  # includes hidden doctors, so old bookings still show a name
        return d.name if d else self.doctor

    @property
    def service_name(self):
        return label("service", self.service)

    @property
    def branch_name(self):
        return label("branch", self.branch)

    def to_dict(self):
        return {
            "reference": self.reference,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "service": self.service,
            "branch": self.branch,
            "doctor": self.doctor,
            "date": self.date.isoformat(),
            "time": self.time,
            "notes": self.notes,
            "status": self.status,
            "created_at": self.created_at.isoformat() + "Z",
        }


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ---------------------------------------------------------------- editable website content

class MediaFile(db.Model):
    """An uploaded picture, stored in the database so it survives Render's reset-on-deploy disk."""
    __tablename__ = "media_files"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.LargeBinary, nullable=False)
    mime = db.Column(db.String(40), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class ImageOverride(db.Model):
    """Replaces a built-in picture such as assets/img/about.jpg without editing any HTML."""
    __tablename__ = "image_overrides"

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(200), unique=True, nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey("media_files.id"), nullable=False)
    media = db.relationship("MediaFile")
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(80), nullable=False, default="Dermatology team")
    photo_id = db.Column(db.Integer, db.ForeignKey("media_files.id"), nullable=True)
    photo_path = db.Column(db.String(200), nullable=True)  # built-in picture used until one is uploaded
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    @property
    def photo_url(self):
        if self.photo_id:
            return f"/media/{self.photo_id}"
        return self.photo_path or "assets/img/logo.png"

    def to_dict(self):
        return {"slug": self.slug, "name": self.name, "role": self.role, "photo": self.photo_url}


class GalleryImage(db.Model):
    __tablename__ = "gallery_images"

    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(db.Integer, db.ForeignKey("media_files.id"), nullable=True)
    photo_path = db.Column(db.String(200), nullable=True)
    caption = db.Column(db.String(150), nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    @property
    def url(self):
        return f"/media/{self.media_id}" if self.media_id else self.photo_path

    def to_dict(self):
        return {"id": self.id, "url": self.url, "caption": self.caption}
