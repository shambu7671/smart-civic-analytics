import logging
import uuid
from flask import Blueprint, current_app, request, session
from sqlalchemy import func
from app import db
from app.models.user import User
from app.utils.api import success, error
from app.utils.security import ensure_csrf_token, require_csrf, current_user_id, hash_password, verify_password


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
logger = logging.getLogger(__name__)


@auth_bp.post("/register")
def register():
    require_csrf()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""
    if not name or not password:
        return error("Full name and password are required.")
    if len(name) > 120:
        return error("Full name must be 120 characters or fewer.")
    if len(password) < 8:
        return error("Password must contain at least 8 characters.")
    if User.query.filter(func.lower(User.name) == name.lower()).first():
        return error("That full name is already registered. Sign in with it or choose a distinct name.", status=409)
    user = User(
        name=name,
        email=f"local-{uuid.uuid4().hex}@smartcivic.invalid",
        mobile="",
        password_hash=hash_password(password),
        role="CITIZEN",
    )
    db.session.add(user)
    db.session.commit()
    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role
    session.permanent = True
    ensure_csrf_token()
    return success({"id": user.id, "name": user.name, "role": user.role}, "Registration successful.", 201)


@auth_bp.post("/login")
def login():
    require_csrf()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""
    if not name or not password:
        return error("Full name and password are required.")
    user = User.query.filter(func.lower(User.name) == name.lower()).first()
    if not user or not user.password_hash or not verify_password(user.password_hash, password):
        return error("Incorrect full name or password.", status=401)
    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role
    session.permanent = True
    ensure_csrf_token()
    return success({"id": user.id, "name": user.name, "role": user.role}, "Login successful.")


@auth_bp.post("/demo-login")
def demo_login():
    """Create a local read-only citizen demo session."""
    return _demo_login("CITIZEN")


@auth_bp.post("/admin-demo-login")
def admin_demo_login():
    """Create a local read-only administrator demo session."""
    return _demo_login("ADMIN")


def _demo_login(role):
    require_csrf()
    if not current_app.config.get("LOCAL_DEMO_LOGIN_ENABLED"):
        return error("Local demo sign-in is disabled.", status=403)

    # The local seed script uses these identities, allowing demos to show seeded records.
    email = "aarav@example.com" if role == "CITIZEN" else "admin@smartcivic.local"
    name = "Aarav Patil (Demo)" if role == "CITIZEN" else "System Administrator (Demo)"
    try:
        user = User.query.filter_by(email=email).first()
        if user and user.role != role:
            return error(f"The local demo identity must have the {role} role.", status=403)
        if not user:
            user = User(name=name, email=email, mobile="", password_hash=None, role=role)
            db.session.add(user)
            db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Local %s demo sign-in failed", role)
        return error("Local demo sign-in is temporarily unavailable.", status=500)

    session.clear()
    session["user_id"] = user.id
    session["role"] = role
    session["demo_login"] = True
    session["demo_role"] = role
    session.permanent = True
    ensure_csrf_token()
    return success({"id": user.id, "name": user.name, "email": user.email, "role": user.role, "demo": True}, f"{role.title()} demo sign-in successful.")


@auth_bp.post("/logout")
def logout():
    require_csrf()
    session.clear()
    return success(message="Logged out successfully.")


@auth_bp.get("/me")
def me():
    uid = current_user_id()
    if not uid:
        return error("Not authenticated.", status=401)
    user = User.query.get(uid)
    return success({"id": user.id, "name": user.name, "role": user.role, "demo": bool(session.get("demo_login"))})
