"""Flask application factory for the Dr. Feysel Dermatology website."""
import logging
import os
from pathlib import Path

import click
from flask import Flask, Response, abort, jsonify, redirect, request, send_from_directory
from flask_cors import CORS

from .config import Config
from .models import AdminUser, ImageOverride, MediaFile, db

# Old page names from the previous site, redirected so existing links keep working.
LEGACY_REDIRECTS = {
    "index-2.html": "/",
    "index.php": "/",
    "index.html": "/",
    "appointment.html": "/appointment",
    "blog.html": "/blog",
    "post.html": "/blog",
    "about.html": "/about",
    "services.html": "/services",
    "contact.html": "/contact",
    "general.html": "/services",
    "general-dermatology.html": "/services",
    "derma.html": "/services",
    "dermatologic-surgery.html": "/services",
    "cosmetic.html": "/services",
    "cosmetic-dermatology.html": "/services",
}


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True, static_folder=None)  # the frontend folder is served by register_frontend()
    app.config.from_object(config_class)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if app.config["SECRET_KEY"] == "change-me-in-production" and not app.debug and not app.testing:
        app.logger.warning("SECRET_KEY is not set. Set it in .env before going live.")

    db.init_app(app)
    if app.config["CORS_ORIGINS"]:
        CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from .admin import admin
    from .api import api
    from . import admin_content, admin_extra  # noqa: F401  (add the content, blog and picture pages to the admin blueprint)
    from .content_models import Doctor  # noqa: F401  (registers the content tables)
    from .content_seed import seed_content
    from .seo import seo
    from .site_api import site_api
    app.register_blueprint(api)
    app.register_blueprint(site_api)
    app.register_blueprint(admin)
    app.register_blueprint(seo)

    with app.app_context():
        try:
            db.create_all()
        except Exception:  # two workers creating the tables at the same moment: the second one just retries
            db.session.rollback()
            db.create_all()
        ensure_admin(app)
        try:
            seed_content(app)
            from .content_seed import import_legacy_doctors
            import_legacy_doctors()
        except Exception:  # never stop the site from starting because of sample content
            db.session.rollback()
            app.logger.exception("Could not add starter content")
        if app.config.get("SEED_SAMPLE_POSTS"):
            try:
                from .blog_seed import seed_sample_posts
                seed_sample_posts(app.config["FRONTEND_DIR"])
            except Exception:
                db.session.rollback()
                app.logger.exception("Could not add sample articles")

    register_frontend(app)
    register_security_headers(app)
    register_cli(app)
    return app


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

    from .seo import render_shell

    @app.get("/")
    def home():
        html = render_shell("/")
        return html if html else send_from_directory(frontend, "index.html")

    @app.get("/media/<int:media_id>")
    def media(media_id):
        """Uploaded pictures (article covers, gallery). The id changes on every upload, so browsers may cache them."""
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
            return redirect(LEGACY_REDIRECTS[filename], code=301)
        if filename.startswith("assets/img/"):
            # A picture staff replaced in /admin/images wins over the file shipped with the site.
            over = ImageOverride.query.filter_by(path=filename).first()
            if over:
                resp = Response(over.media.data, mimetype=over.media.mime)
                resp.cache_control.public = True
                resp.cache_control.max_age = 300
                return resp
        page_html = render_shell("/" + filename)
        if page_html:
            return page_html
        target = (frontend / filename).resolve()
        if frontend not in target.parents and target != frontend:
            abort(404)
        if target.is_dir():
            filename = filename.rstrip("/") + "/index.html"
        elif not target.exists() and (frontend / f"{filename}.html").exists():
            filename = f"{filename}.html"  # allow clean URLs such as /about
        response = send_from_directory(frontend, filename)
        if filename.startswith(("assets/", "static/")):
            response.cache_control.public = True
            response.cache_control.max_age = 60 * 60 * 24 * 7
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
