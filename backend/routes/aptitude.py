"""
HireMind AI — Aptitude Round Routes
"""
import json
import os
import random
from flask import Blueprint, request, jsonify, session
from config import Config
from services.scoring import score_aptitude_round
from services.round_engine import round_engine

aptitude_bp = Blueprint("aptitude", __name__, url_prefix="/api/aptitude")


def _load_questions():
    p = os.path.join(Config.DATA_DIR, "aptitude_questions.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@aptitude_bp.route("/questions", methods=["GET"])
def get_questions():
    """Returns questions for the test session."""
    user_id = request.args.get("user_id") or session.get("user_id") or "u-dev-001"
    mode = request.args.get("mode", "practice")
    track = request.args.get("track", "default")

    if mode == "simulation":
        if not round_engine.can_access_round(user_id=user_id, round_name="aptitude", mode=mode, track=track):
            return jsonify({
                "error": "LOCKED_ROUND",
                "message": "You must clear Resume Screening before unlocking the Aptitude Round in Simulation Mode."
            }), 403

    questions = _load_questions()
    # Strip correct_option and explanation for test delivery
    client_questions = []
    for q in questions:
        client_questions.append({
            "id": q["id"],
            "topic": q.get("topic", "General"),
            "difficulty": q.get("difficulty", "medium"),
            "question": q["question"],
            "options": q["options"]
        })

    return jsonify({
        "questions": client_questions,
        "total": len(client_questions),
        "duration_minutes": 15
    }), 200


@aptitude_bp.route("/submit", methods=["POST"])
def submit_test():
    """Evaluates submitted answers, scores accuracy/speed, and records round progress."""
    data = request.get_json(silent=True) or {}
    answers = data.get("answers", {})  # {str(q_id): chosen_option_index}
    time_taken_sec = int(data.get("time_taken_sec", 600))
    mode = data.get("mode", "practice")
    track = data.get("track", "default")
    user_id = session.get("user_id") or data.get("user_id") or "u-dev-001"

    all_qs = {str(q["id"]): q for q in _load_questions()}
    correct_count = 0
    results_detail = []

    for q_id_str, q in all_qs.items():
        user_choice = answers.get(q_id_str)
        is_correct = (user_choice == q["correct_option"])
        if is_correct:
            correct_count += 1

        results_detail.append({
            "id": q["id"],
            "question": q["question"],
            "user_choice": user_choice,
            "correct_option": q["correct_option"],
            "is_correct": is_correct,
            "explanation": q.get("explanation", "")
        })

    score_result = score_aptitude_round(
        correct_count=correct_count,
        total_questions=len(all_qs),
        time_taken_sec=time_taken_sec
    )

    # Record in round engine
    round_engine.record_round_attempt(
        user_id=user_id,
        round_name="aptitude",
        score=score_result["score"],
        mode=mode,
        track=track,
        breakdown=score_result
    )

    return jsonify({
        "score": score_result["score"],
        "accuracy": score_result["accuracy"],
        "speed": score_result["speed"],
        "difficulty": score_result["difficulty"],
        "passed": score_result["passed"],
        "correct_count": correct_count,
        "total_questions": len(all_qs),
        "details": results_detail
    }), 200
