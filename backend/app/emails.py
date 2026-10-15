"""Email notifications. Sending runs in a background thread so the visitor never waits on SMTP."""
import json
import logging
import re
import smtplib
import urllib.request
import ssl
import threading
from email.message import EmailMessage

from flask import current_app

log = logging.getLogger(__name__)


def _send(cfg, to, subject, body, reply_to=None):
    msg = EmailMessage()
    msg["From"] = cfg["MAIL_SENDER"]
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)
    try:
        if cfg["MAIL_USE_SSL"]:
            server = smtplib.SMTP_SSL(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], context=ssl.create_default_context(), timeout=20)
        else:
            server = smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], timeout=20)
            if cfg["MAIL_USE_TLS"]:
                server.starttls(context=ssl.create_default_context())
        with server:
            if cfg["MAIL_USERNAME"]:
                server.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            server.send_message(msg)
    except Exception:  # noqa: BLE001 - email must never break a booking
        log.exception("Failed to send email to %s", to)


def _parse_sender(sender):
    m = re.match(r"^\s*(.*?)\s*<([^>]+)>\s*$", sender or "")
    return (m.group(1), m.group(2)) if m else ("", sender)


def _send_brevo(cfg, to, subject, body, reply_to=None):
    name, email = _parse_sender(cfg["MAIL_SENDER"])
    payload = {"sender": {"name": name or "Clinic", "email": email}, "to": [{"email": to}],
               "subject": subject, "textContent": body}
    if reply_to:
        payload["replyTo"] = {"email": reply_to}
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email", data=json.dumps(payload).encode(), method="POST",
        headers={"api-key": cfg["BREVO_API_KEY"], "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
    except Exception:  # noqa: BLE001
        log.exception("Brevo email to %s failed", to)


def send_async(to, subject, body, reply_to=None):
    cfg = dict(current_app.config)
    if not to:
        return
    if cfg.get("BREVO_API_KEY"):
        target = _send_brevo
    elif cfg.get("MAIL_SERVER"):
        target = _send
    else:
        log.info("Email disabled. Would send to %s: %s", to, subject)
        return
    threading.Thread(target=target, args=(cfg, to, subject, body, reply_to), daemon=True).start()


def notify_new_appointment(a):
    cfg = current_app.config
    details = (
        f"Reference: {a.reference}\n"
        f"Patient:   {a.full_name}\n"
        f"Phone:     {a.phone}\n"
        f"Email:     {a.email}\n"
        f"Service:   {a.service_name}\n"
        f"Branch:    {a.branch_name}\n"
        f"Doctor:    {a.doctor_name}\n"
        f"Date/time: {a.date.strftime('%A %d %B %Y')} at {a.time}\n"
        f"Notes:     {a.notes or '-'}\n"
    )
    send_async(cfg["CLINIC_NOTIFY_EMAIL"], f"New appointment request {a.reference}", details, reply_to=a.email)
    if cfg["SEND_PATIENT_CONFIRMATION"]:
        send_async(
            a.email,
            f"We received your appointment request ({a.reference})",
            f"Dear {a.first_name},\n\n"
            "Thank you for choosing Dr. Feysel Dermatology Specialty Clinic. "
            "We have received your appointment request and will call you to confirm.\n\n"
            f"{details}\n"
            "Need to change something? Call 0920 201 929 (Bole) or 0919 237 070 (Zenebework).\n\n"
            "Dr. Feysel Dermatology Specialty Clinic\n",
        )


def notify_status_change(a):
    if a.status not in {"confirmed", "cancelled"}:
        return
    word = "confirmed" if a.status == "confirmed" else "cancelled"
    send_async(
        a.email,
        f"Your appointment {a.reference} is {word}",
        f"Dear {a.first_name},\n\n"
        f"Your appointment on {a.date.strftime('%A %d %B %Y')} at {a.time} "
        f"({a.branch_name}) has been {word}.\n\n"
        "Questions? Call 0920 201 929 (Bole) or 0919 237 070 (Zenebework).\n\n"
        "Dr. Feysel Dermatology Specialty Clinic\n",
    )


def notify_contact(m):
    send_async(
        current_app.config["CLINIC_NOTIFY_EMAIL"],
        f"Website message: {m.subject}",
        f"From: {m.name} <{m.email}>\n\n{m.message}\n",
        reply_to=m.email,
    )
