"""
WSGI entry point for production servers (Gunicorn, uWSGI, etc.)

Usage:
    gunicorn --config gunicorn.conf.py wsgi:app
    waitress-serve --port=8000 wsgi:app   (Windows alternative)
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
