from flask import Blueprint, request, jsonify, session
from db.client import db_client

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()
    role = data.get("role", "candidate")
    company_id = data.get("company_id") or (f"comp-{email.split('@')[0]}" if role == "recruiter" else None)

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    try:
        user_res = db_client.sign_up(email=email, password=password, full_name=full_name, role=role, company_id=company_id)
        user = user_res["user"]
        session["user_id"] = user["id"]
        session["user_email"] = user["email"]
        session["user_role"] = user["role"]
        session["company_id"] = user.get("company_id")
        return jsonify({"message": "Account created successfully", "user": user}), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 409
    except Exception as e:
        return jsonify({"error": f"Failed to create account: {str(e)}"}), 500


@auth_bp.route("/signin", methods=["POST"])
@auth_bp.route("/login", methods=["POST"])
def signin():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    try:
        auth_res = db_client.sign_in(email=email, password=password)
        user = auth_res["user"]
        session["user_id"] = user["id"]
        session["user_email"] = user["email"]
        session["user_role"] = user.get("role", "candidate")
        session["company_id"] = user.get("company_id")
        return jsonify({"message": "Signed in successfully", "user": user}), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 401
    except Exception as e:
        return jsonify({"error": f"Authentication failed: {str(e)}"}), 500


@auth_bp.route("/signout", methods=["POST"])
@auth_bp.route("/logout", methods=["POST"])
def signout():
    session.clear()
    return jsonify({"message": "Signed out successfully"}), 200


@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    user_id = session.get("user_id") or request.args.get("user_id")
    if not user_id:
        return jsonify({"user": None, "authenticated": False}), 200

    profile = db_client.get_profile(user_id)
    if profile:
        return jsonify({"user": profile, "authenticated": True}), 200
    return jsonify({"user": {"id": user_id, "email": session.get("user_email"), "role": session.get("user_role", "candidate")}, "authenticated": True}), 200
