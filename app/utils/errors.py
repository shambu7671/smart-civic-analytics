from flask import jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge


def register_error_handlers(app):
    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_):
        if request.path.startswith("/api/"):
            return jsonify(success=False, message="Uploaded file is too large.", error="Maximum upload size exceeded."), 413
        return "Uploaded file is too large.", 413

    @app.errorhandler(404)
    def not_found(_):
        if request.path.startswith("/api/"):
            return jsonify(success=False, message="Resource not found.", error="Not found."), 404
        return "Page not found.", 404

    @app.errorhandler(403)
    def forbidden(_):
        if request.path.startswith("/api/"):
            return jsonify(success=False, message="Access denied.", error="Forbidden."), 403
        return "Access denied.", 403

    @app.errorhandler(500)
    def server_error(_):
        if request.path.startswith("/api/"):
            return jsonify(success=False, message="Server error.", error="An unexpected server error occurred."), 500
        return "An unexpected server error occurred.", 500
