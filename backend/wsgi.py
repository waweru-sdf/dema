"""Entry point.

Development:  python wsgi.py           (or: flask --app wsgi run --debug)
Production:   gunicorn -w 1 --threads 4 -b 0.0.0.0:8000 wsgi:app   (Linux)
              waitress-serve --port=8000 wsgi:app                    (Windows)
"""
import os

from dotenv import load_dotenv

load_dotenv()

from werkzeug.middleware.proxy_fix import ProxyFix  # noqa: E402

from app import create_app  # noqa: E402

app = create_app()

# Behind Nginx/Apache or a hosting proxy, trust one hop of X-Forwarded-* headers.
if os.getenv("BEHIND_PROXY", "false").lower() in {"1", "true", "yes"}:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "1") == "1")
