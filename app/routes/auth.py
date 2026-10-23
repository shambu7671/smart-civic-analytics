import logging
from flask import Blueprint, current_app, request, session
from app import db
from app.models.user import User
from app.utils.api import success, error
from app.utils.security import ensure_csrf_token, require_csrf, current_user_id


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
logger = logging.getLogger(__name__)


def _firebase_claims(data):
    token = (data.get("id_token") or "").strip()
    if not token:
        return None, error("Firebase sign-in is required.", status=401)
    try:
        from app.services.firebase_service import verify_firebase_id_token
        claims = verify_firebase_id_token(token)
        if claims.get("aud") != current_app.config.get("FIREBASE_PROJECT_ID"):
            return None, error("Invalid Firebase token.", status=401)
        if not claims.get("email"):
            return None, error("A verified email address is required.", status=401)
        if not claims.get("email_verified"):
            return None, error("Verify your email address before continuing.", status=401)
        return claims, None
    except Exception:
        logger.info("Firebase ID token verification failed", exc_info=True)
        return None, error("Firebase authentication failed.", status=401)


def _sync_user(claims, name="", mobile=""):
    uid = claims["uid"]
    email = claims["email"].strip().lower()
    user = User.query.filter_by(firebase_uid=uid).first()
    if not user:
        # Link a pre-existing app account by its verified Firebase email. This
        # preserves staff roles while transitioning existing users.
        user = User.query.filter_by(email=email).first()
    if not user:
        user = User(name=name or claims.get("name") or email.split("@", 1)[0],
                    email=email, mobile=mobile or "", password_hash=None,
                    firebase_uid=uid, role="CITIZEN")
        db.session.add(user)
    else:
        if user.firebase_uid and user.firebase_uid != uid:
            raise ValueError("This email is already linked to another Firebase account.")
        user.firebase_uid = uid
        user.email = email
        if name:
            user.name = name
        if mobile:
            user.mobile = mobile
    db.session.commit()
    return user


@auth_bp.get("/config")
def firebase_config():
    """Expose only Firebase's public web configuration to the sign-in page."""
    api_key = current_app.config.get("FIREBASE_WEB_API_KEY")
    project_id = current_app.config.get("FIREBASE_PROJECT_ID")
    if not api_key or not project_id:
        return error("Firebase Authentication is not configured.", status=503)
    return success({"api_key": api_key, "project_id": project_id})


@auth_bp.post("/register")
def register():
    require_csrf()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    mobile = (data.get("mobile") or "").strip()
    if not name or not email or not mobile:
        return error("All registration fields are required.")
    if "@" not in email:
        return error("Enter a valid email address.")
    claims, failure = _firebase_claims(data)
    if failure:
        return failure
    if claims["email"].strip().lower() != email:
        return error("Firebase account email does not match the registration email.", status=400)
    try:
        user = _sync_user(claims, name=name, mobile=mobile)
    except ValueError as exc:
        db.session.rollback()
        return error(str(exc), status=409)
    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role
    session.permanent = True
    ensure_csrf_token()
    return success({"id": user.id, "name": user.name, "email": user.email, "role": user.role}, "Registration successful.", 201)


@auth_bp.post("/login")
def login():
    require_csrf()
    data = request.get_json(silent=True) or {}
    claims, failure = _firebase_claims(data)
    if failure:
        return failure
    try:
        user = _sync_user(claims, mobile=(data.get("mobile") or "").strip())
    except ValueError as exc:
        db.session.rollback()
        return error(str(exc), status=409)
    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role
    session.permanent = True
    ensure_csrf_token()
    return success({"id": user.id, "name": user.name, "email": user.email, "role": user.role}, "Login successful.")


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
    return success({"id": user.id, "name": user.name, "email": user.email, "mobile": user.mobile, "role": user.role})
