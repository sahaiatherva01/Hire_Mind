from flask import Blueprint, jsonify, session, request

from routes._guard import login_required
from services.round_engine import get_round_status, final_hiring_decision
from services.supabase_client import supabase_service

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api")


@dashboard_bp.get("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    track = request.args.get("track", "default")

    simulation_status = get_round_status(user_id, track)

    practice_summary = {}
    for round_name in ["aptitude", "dsa", "technical", "project_defense", "hr"]:
        attempts = supabase_service.get_attempts(user_id, round_name, mode="practice")
        practice_summary[round_name] = {
            "attempts": len(attempts),
            "best_score": max((a["score"] for a in attempts), default=None),
            "last_score": attempts[0]["score"] if attempts else None,
        }

    return jsonify({
        "simulation": simulation_status,
        "practice": practice_summary,
        "track": track,
    })


@dashboard_bp.get("/rounds/status")
@login_required
def rounds_status():
    """Used by the frontend before entering any simulation round to confirm access."""
    user_id = session["user_id"]
    track = request.args.get("track", "default")
    return jsonify({"rounds": get_round_status(user_id, track)})


@dashboard_bp.get("/report/final")
@login_required
def final_report():
    user_id = session["user_id"]
    track = request.args.get("track", "default")
    return jsonify(final_hiring_decision(user_id, track))
