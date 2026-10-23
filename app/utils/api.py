from flask import jsonify


def success(data=None, message="Success", status=200, **meta):
    payload = {"success": True, "message": message, "data": data}
    if meta:
        payload["meta"] = meta
    return jsonify(payload), status


def error(message, error=None, status=400):
    return jsonify({"success": False, "message": message, "error": error or message}), status
