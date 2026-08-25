import json
import os
import random
import time

from flask import Blueprint, jsonify, request, session

from routes._guard import login_required
from services.round_engine import is_round_unlocked, get_cutoffs
from services.scoring import score_aptitude
from services.supabase_client import supabase_service

aptitude_bp = Blueprint("aptitude", __name__, url_prefix="/api/aptitude")

QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "aptitude_questions.json")
TIME_LIMIT_SECONDS = 900  # 15 minutes for a 8-question set
QUESTIONS_PER_ROUND = 8


def _load_questions():
    with open(QUESTIONS_PATH, "r") as f:
        return json.load(f)


def _public_view(q):
    """Strip the answer key before sending to the client."""
    return {
        "id": q["id"],
        "topic": q["topic"],
        "difficulty": q["difficulty"],
        "question": q["question"],
        "options": q["options"],
    }


@aptitude_bp.post("/start")
@login_required
def start():
    body = request.get_json(silent=True) or {}
    mode = body.get("mode", "practice")  # 'practice' | 'simulation'
    track = body.get("track", "default")
    user_id = session["user_id"]

    if mode == "simulation" and not is_round_unlocked(user_id, "aptitude", track):
        return jsonify({"error": "Aptitude round is locked. Clear Resume Screening first."}), 403

    all_questions = _load_questions()
    random.shuffle(all_questions)
    selected = all_questions[:QUESTIONS_PER_ROUND]

    # Stash the full (answer-bearing) question set in the session so /submit
    # can grade without trusting anything the client sends back except answers.
    session["aptitude_attempt"] = {
        "mode": mode,
        "track": track,
        "questions": selected,
        "started_at": time.time(),
    }

    return jsonify({
        "mode": mode,
        "time_limit_seconds": TIME_LIMIT_SECONDS,
        "questions": [_public_view(q) for q in selected],
    })


@aptitude_bp.post("/submit")
@login_required
def submit():
    user_id = session["user_id"]
    attempt_ctx = session.get("aptitude_attempt")
    if not attempt_ctx:
        return jsonify({"error": "No active aptitude attempt. Call /start first."}), 400

    body = request.get_json(silent=True) or {}
    answers = body.get("answers", {})  # { "question_id": option_index }

    time_taken = time.time() - attempt_ctx["started_at"]
    result = score_aptitude(
        attempt_ctx["questions"], answers, time_taken, TIME_LIMIT_SECONDS
    )

    mode = attempt_ctx["mode"]
    track = attempt_ctx["track"]
    cutoff = get_cutoffs(track).get("aptitude", 70)
    passed = result["score"] >= cutoff

    supabase_service.record_attempt({
        "user_id": user_id,
        "round": "aptitude",
        "mode": mode,
        "score": result["score"],
        "meta": {
            "accuracy": result["accuracy"],
            "speed": result["speed"],
            "difficulty": result["difficulty"],
            "correct_count": result["correct_count"],
            "total_questions": result["total_questions"],
            "weak_topics": result["weak_topics"],
        },
    })

    session.pop("aptitude_attempt", None)

    response = dict(result)
    response["cutoff"] = cutoff
    response["passed"] = passed
    response["mode"] = mode

    if mode == "simulation":
        response["next_round_unlocked"] = passed
        response["message"] = (
            "Cleared. DSA round unlocked." if passed
            else f"Below cutoff ({cutoff}%). Review weak topics and retry to unlock DSA."
        )

    return jsonify(response)


@aptitude_bp.get("/history")
@login_required
def history():
    user_id = session["user_id"]
    mode = request.args.get("mode")
    attempts = supabase_service.get_attempts(user_id, "aptitude", mode)
    return jsonify({"attempts": attempts})
