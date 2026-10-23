import secrets
from functools import wraps
from flask import abort, jsonify, request, session
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def ensure_csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def require_csrf():
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        from flask import make_response
        response = make_response(
            jsonify(success=False, message="CSRF validation failed.", error="Invalid or missing CSRF token."),
            400,
        )
        raise HTTPException(response=response)


def current_user_id():
    return session.get("user_id")


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user_id():
            if request.path.startswith("/api/"):
                return jsonify(success=False, message="Authentication required.", error="Login required."), 401
            from flask import redirect, url_for
            target = "pages.admin_login_page" if request.path.startswith("/admin/") else "pages.login_page"
            return redirect(url_for(target))
        return view(*args, **kwargs)
    return wrapped


def require_role(*roles):
    def decorator(view):
        @wraps(view)
        @require_login
        def wrapped(*args, **kwargs):
            from app.models.user import User
            user = User.query.get(current_user_id())
            if not user or user.role not in roles:
                if request.path.startswith("/api/"):
                    return jsonify(success=False, message="Access denied.", error="Insufficient privileges."), 403
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator
