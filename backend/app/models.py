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
        return label("doctor", self.doctor)

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
