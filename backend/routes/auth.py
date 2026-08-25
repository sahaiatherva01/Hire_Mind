from flask import Blueprint, request, jsonify, session

from services.supabase_client import supabase_service

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/signup")
def signup():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    full_name = (body.get("full_name") or "").strip()

    if not email or "@" not in email:
        return jsonify({"error": "A valid email is required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if not full_name:
        return jsonify({"error": "Full name is required."}), 400

    user, error = supabase_service.sign_up(email, password, full_name)
    if error:
        return jsonify({"error": error}), 409

    session["user_id"] = user["id"]
    session["email"] = user["email"]
    return jsonify({"user": {"id": user["id"], "email": user["email"], "full_name": full_name}}), 201


@auth_bp.post("/login")
def login():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    user, error = supabase_service.sign_in(email, password)
    if error:
        return jsonify({"error": error}), 401

    session["user_id"] = user["id"]
    session["email"] = user["email"]
    return jsonify({"user": {"id": user["id"], "email": user["email"], "full_name": user.get("full_name")}})


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@auth_bp.get("/me")
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"user": None}), 200
    user = supabase_service.get_user(user_id)
    if not user:
        session.clear()
        return jsonify({"user": None}), 200
    return jsonify({"user": {"id": user["id"], "email": user["email"], "full_name": user.get("full_name")}})
