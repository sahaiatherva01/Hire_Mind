from flask import Blueprint, request, jsonify, session

from core.scoring import calculate_overall_readiness, get_round_progression_status
from db.client import db_client

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/progress", methods=["GET"])
def get_progress():
    user_id = request.args.get("user_id") or session.get("user_id") or "u-dev-001"
    track = request.args.get("track") or "default"
    prog = get_round_progression_status(user_id=user_id, track=track)
    return jsonify(prog), 200


@dashboard_bp.route("/readiness", methods=["GET"])
def get_readiness():
    user_id = request.args.get("user_id") or session.get("user_id") or "u-dev-001"
    track = request.args.get("track") or "default"
    user_prog = db_client.get_user_progress(user_id, track)
    round_scores = user_prog.get("round_scores", {})
    readiness = calculate_overall_readiness(round_scores)
    return jsonify(readiness), 200


@dashboard_bp.route("/evaluations", methods=["GET"])
def get_evaluations():
    evals = db_client.get_evaluations(limit=25)
    return jsonify({"evaluations": evals}), 200


@dashboard_bp.route("/reset", methods=["POST"])
def reset_progress():
    user_id = request.args.get("user_id") or session.get("user_id") or "u-dev-001"
    track = request.args.get("track") or "default"
    db_client.save_user_progress(user_id, track, {
        "round_scores": {},
        "current_round": "resume_screening"
    })
    return jsonify({"status": "reset", "user_id": user_id}), 200
