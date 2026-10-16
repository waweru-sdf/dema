"""Flask application factory for the Dr. Feysel Dermatology website."""
import logging
import os
from pathlib import Path

import click
from flask import Flask, Response, abort, jsonify, redirect, request, send_from_directory
from flask_cors import CORS

from .clinic_data import DOCTORS
from .config import Config
from .media import MAX_UPLOAD_BYTES
from .models import AdminUser, Doctor, GalleryImage, ImageOverride, MediaFile, db

# Old page names from the previous site, redirected so existing links keep working.
LEGACY_REDIRECTS = {
    "index-2.html": "index.html",
    "index.php": "index.html",
    "general.html": "general-dermatology.html",
    "derma.html": "dermatologic-surgery.html",
    "cosmetic.html": "cosmetic-dermatology.html",
}


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    app.config.setdefault("MAX_CONTENT_LENGTH", MAX_UPLOAD_BYTES + 1024 * 1024)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if app.config["SECRET_KEY"] == "change-me-in-production" and not app.debug and not app.testing:
        app.logger.warning("SECRET_KEY is not set. Set it in .env before going live.")

    db.init_app(app)
    if app.config["CORS_ORIGINS"]:
        CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from .admin import admin
    from .api import api
    app.register_blueprint(api)
    app.register_blueprint(admin)

    with app.app_context():
        db.create_all()
        seed_content()
        ensure_admin(app)

    register_frontend(app)
    register_security_headers(app)
    register_cli(app)
    return app


def seed_content():
    """First start only: copy the built-in doctors and gallery into the database so staff can edit them."""
    if Doctor.query.count() == 0:
        for i, d in enumerate(DOCTORS):
            db.session.add(Doctor(slug=d["slug"], name=d["name"], role="Dermatology team", sort_order=i,
                                  photo_path=f"assets/img/doctors/{d['slug']}.jpg"))
    if GalleryImage.query.count() == 0:
        for i in range(1, 5):
            db.session.add(GalleryImage(photo_path=f"assets/img/gallery/{i}.jpg", sort_order=i,
                                        caption=f"Clinic gallery image {i}"))
    db.session.commit()


def ensure_admin(app):
    """Create the first staff account from ADMIN_USERNAME / ADMIN_PASSWORD (useful on hosts without a shell)."""
    username, password = app.config.get("ADMIN_USERNAME"), app.config.get("ADMIN_PASSWORD")
    if not username or not password:
        return
    if AdminUser.query.filter_by(username=username).first():
        return
    if len(password) < 8:
        app.logger.warning("ADMIN_PASSWORD must be at least 8 characters. Admin user not created.")
        return
    user = AdminUser(username=username)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
        app.logger.info("Created admin user '%s'", username)
    except Exception:  # another worker created it at the same moment
        db.session.rollback()


def register_frontend(app):
    frontend = Path(app.config["FRONTEND_DIR"]).resolve()

    @app.get("/")
    def home():
        return send_from_directory(frontend, "index.html")

    @app.get("/media/<int:media_id>")
    def media(media_id):
        """Uploaded pictures. The id changes on every upload, so browsers may cache them for good."""
        row = db.session.get(MediaFile, media_id)
        if not row:
            abort(404)
        resp = Response(row.data, mimetype=row.mime)
        resp.cache_control.public = True
        resp.cache_control.max_age = 60 * 60 * 24 * 365
        resp.cache_control.immutable = True
        return resp

    @app.get("/<path:filename>")
    def static_site(filename):
        if filename in LEGACY_REDIRECTS:
            return redirect("/" + LEGACY_REDIRECTS[filename], code=301)
        if filename.startswith("assets/img/"):
            # A picture staff replaced in /admin/images wins over the file shipped with the site.
            over = ImageOverride.query.filter_by(path=filename).first()
            if over:
                resp = Response(over.media.data, mimetype=over.media.mime)
                resp.cache_control.public = True
                resp.cache_control.max_age = 300
                return resp
        target = (frontend / filename).resolve()
        if frontend not in target.parents and target != frontend:
            abort(404)
        if target.is_dir():
            filename = filename.rstrip("/") + "/index.html"
        elif not target.exists() and (frontend / f"{filename}.html").exists():
            filename = f"{filename}.html"  # allow clean URLs such as /about
        response = send_from_directory(frontend, filename)
        if filename.startswith("assets/"):
            response.cache_control.public = True
            # Pictures can be replaced from /admin, so keep their cache short; code and fonts can stay a week.
            response.cache_control.max_age = 300 if filename.startswith("assets/img/") else 60 * 60 * 24 * 7
        return response

    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith("/api/"):
            return jsonify(ok=False, message="Not found"), 404
        page = frontend / "404.html"
        if page.exists():
            return send_from_directory(frontend, "404.html"), 404
        return "Not found", 404

    @app.errorhandler(500)
    def server_error(_e):
        if request.path.startswith("/api/"):
            return jsonify(ok=False, message="Something went wrong. Please call the clinic."), 500
        return "Something went wrong. Please call the clinic.", 500


def register_security_headers(app):
    @app.after_request
    def headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        if request.path.startswith("/admin"):
            resp.headers["Cache-Control"] = "no-store"
        return resp


def register_cli(app):
    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.password_option()
    def create_admin(username, password):
        """Create or reset a staff login for /admin."""
        if len(password) < 8:
            raise click.ClickException("Use at least 8 characters.")
        user = AdminUser.query.filter_by(username=username).first() or AdminUser(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin user '{username}' saved.")

    @app.cli.command("init-db")
    def init_db():
        """Create database tables."""
        db.create_all()
        click.echo("Database ready.")
