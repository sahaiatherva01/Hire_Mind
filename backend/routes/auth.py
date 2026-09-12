"""
HireMind AI — Authentication Routes
"""
import uuid
from flask import Blueprint, request, jsonify, session
from services.supabase_client import supabase_service

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()
    role = data.get("role", "candidate")  # 'candidate' or 'recruiter'
    company_name = data.get("company_name", "TechCorp")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    db_data = supabase_service._read_local_db()
    for u in db_data.get("users", []):
        if u.get("email") == email:
            return jsonify({"error": "An account with this email already exists."}), 409

    user_id = f"u-{uuid.uuid4()}"
    company_id = f"comp-{uuid.uuid4()}" if role == "recruiter" else None

    new_user = {
        "id": user_id,
        "email": email,
        "password_hash": password,  # dev mock hash
        "full_name": full_name or email.split("@")[0].title(),
        "role": role,
        "company_id": company_id,
        "company_name": company_name if role == "recruiter" else None,
        "target_role": "Software Engineer",
        "preferred_track": "default"
    }

    db_data.setdefault("users", []).append(new_user)
    supabase_service._write_local_db(db_data)

    session["user_id"] = user_id
    session["user_email"] = email
    session["user_role"] = role
    session["company_id"] = company_id

    return jsonify({
        "message": "Account created successfully.",
        "user": {
            "id": user_id,
            "email": email,
            "full_name": new_user["full_name"],
            "role": role,
            "company_id": company_id,
            "company_name": new_user["company_name"]
        }
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    db_data = supabase_service._read_local_db()
    matched_user = None
    for u in db_data.get("users", []):
        if u.get("email") == email:
            matched_user = u
            break

    # If demo fallback login
    if not matched_user:
        if email.startswith("recruiter"):
            matched_user = {
                "id": "u-rec-001",
                "email": email,
                "full_name": "Demo Recruiter",
                "role": "recruiter",
                "company_id": "comp-techcorp-101",
                "company_name": "TechCorp Global"
            }
        else:
            matched_user = {
                "id": "u-dev-001",
                "email": email,
                "full_name": "Demo Candidate",
                "role": "candidate",
                "company_id": None,
                "target_role": "Software Engineer",
                "preferred_track": "default"
            }

    session["user_id"] = matched_user.get("id")
    session["user_email"] = matched_user.get("email")
    session["user_role"] = matched_user.get("role", "candidate")
    session["company_id"] = matched_user.get("company_id")

    return jsonify({
        "message": "Login successful.",
        "user": {
            "id": matched_user.get("id"),
            "email": matched_user.get("email"),
            "full_name": matched_user.get("full_name"),
            "role": matched_user.get("role", "candidate"),
            "company_id": matched_user.get("company_id"),
            "company_name": matched_user.get("company_name")
        }
    }), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    user_id = session.get("user_id") or request.args.get("user_id") or "u-dev-001"
    db_data = supabase_service._read_local_db()
    matched = next((u for u in db_data.get("users", []) if u.get("id") == user_id), None)

    if not matched:
        matched = {
            "id": user_id,
            "email": "candidate@hiremind.ai",
            "full_name": "Demo Candidate",
            "role": "candidate",
            "company_id": None
        }

    return jsonify({"user": matched}), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."}), 200
