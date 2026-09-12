"""
HireMind AI — Candidate Dashboard & Progression Routes
"""
from flask import Blueprint, request, jsonify, session
from services.round_engine import round_engine
from services.scoring import calculate_readiness_score
from services.supabase_client import supabase_service

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/progress", methods=["GET"])
def get_progress():
    """Returns simulation track lock/unlock status and scores for all rounds."""
    user_id = request.args.get("user_id") or session.get("user_id") or "u-dev-001"
    track = request.args.get("track") or "default"

    progress = round_engine.get_user_progress(user_id=user_id, track=track)
    return jsonify(progress), 200


@dashboard_bp.route("/readiness", methods=["GET"])
def get_readiness():
    """Calculates aggregate candidate readiness score (0-100) across all rounds."""
    user_id = request.args.get("user_id") or session.get("user_id") or "u-dev-001"
    db_data = supabase_service._read_local_db()

    user_records = [
        r for r in db_data.get("round_progress", [])
        if r.get("user_id") == user_id
    ]

    round_scores = {}
    for r in user_records:
        r_name = r.get("round_name")
        r_score = r.get("score")
        if r_name and r_score is not None:
            round_scores[r_name] = float(r_score)

    readiness = calculate_readiness_score(round_scores)
    return jsonify(readiness), 200


@dashboard_bp.route("/evaluations", methods=["GET"])
def get_evaluations():
    """Returns audit log of recent agent outputs and RAG retrieval citations."""
    db_data = supabase_service._read_local_db()
    evals = db_data.get("evaluations", [])
    evals.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"evaluations": evals[:20]}), 200
