from functools import wraps
from flask import session, jsonify


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Authentication required."}), 401
        return fn(*args, **kwargs)
    return wrapper
