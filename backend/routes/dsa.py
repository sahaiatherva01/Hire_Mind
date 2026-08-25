import json
import os
import random
import time

from flask import Blueprint, jsonify, request, session

from routes._guard import login_required
from services.code_sandbox import run_solution, estimate_complexity_and_quality
from services.round_engine import is_round_unlocked, get_cutoffs
from services.scoring import score_dsa
from services.supabase_client import supabase_service

dsa_bp = Blueprint("dsa", __name__, url_prefix="/api/dsa")

PROBLEMS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "dsa_problems.json")


def _load_problems():
    with open(PROBLEMS_PATH, "r") as f:
        return json.load(f)


def _find_problem(problem_id):
    for p in _load_problems():
        if p["id"] == problem_id:
            return p
    return None


def _public_view(p):
    return {
        "id": p["id"],
        "title": p["title"],
        "difficulty": p["difficulty"],
        "topic": p["topic"],
        "statement": p["statement"],
        "function_signature": p["function_signature"],
        "starter_code": p["starter_code"],
        "examples": p["examples"],
        "time_limit_seconds": p["time_limit_seconds"],
    }


@dsa_bp.get("/problems")
@login_required
def list_problems():
    """Practice Mode: browse all problems freely."""
    return jsonify({"problems": [_public_view(p) for p in _load_problems()]})


@dsa_bp.post("/start")
@login_required
def start():
    body = request.get_json(silent=True) or {}
    mode = body.get("mode", "practice")
    track = body.get("track", "default")
    problem_id = body.get("problem_id")
    user_id = session["user_id"]

    if mode == "simulation" and not is_round_unlocked(user_id, "dsa", track):
        return jsonify({"error": "DSA round is locked. Clear Aptitude first."}), 403

    problems = _load_problems()
    if mode == "simulation":
        # Simulation mode: system picks a problem candidate hasn't solved.
        problem = random.choice(problems)
    else:
        problem = _find_problem(problem_id) if problem_id else random.choice(problems)

    if not problem:
        return jsonify({"error": "Problem not found."}), 404

    session["dsa_attempt"] = {
        "mode": mode,
        "track": track,
        "problem_id": problem["id"],
        "started_at": time.time(),
    }

    return jsonify({"mode": mode, "problem": _public_view(problem)})


@dsa_bp.post("/run")
@login_required
def run():
    """Run against public tests only — for iterating before final submit."""
    body = request.get_json(silent=True) or {}
    code = body.get("code", "")
    problem_id = body.get("problem_id")

    problem = _find_problem(problem_id)
    if not problem:
        return jsonify({"error": "Problem not found."}), 404
    if not code.strip():
        return jsonify({"error": "Submit some code first."}), 400

    result = run_solution(code, problem["function_signature"], problem["public_tests"], [])
    if result["error"]:
        return jsonify({"error": result["error"]}), 200
    return jsonify({"results": result["public_results"]})


@dsa_bp.post("/submit")
@login_required
def submit():
    user_id = session["user_id"]
    attempt_ctx = session.get("dsa_attempt")
    if not attempt_ctx:
        return jsonify({"error": "No active DSA attempt. Call /start first."}), 400

    body = request.get_json(silent=True) or {}
    code = body.get("code", "")
    problem = _find_problem(attempt_ctx["problem_id"])
    if not problem:
        return jsonify({"error": "Problem not found."}), 404

    exec_result = run_solution(
        code, problem["function_signature"], problem["public_tests"], problem["hidden_tests"]
    )
    if exec_result["error"]:
        # Still record a zero-ish attempt so history/weak-area tracking works
        all_results = []
    else:
        all_results = exec_result["public_results"] + exec_result["hidden_results"]

    quality = estimate_complexity_and_quality(code)
    time_taken = time.time() - attempt_ctx["started_at"]

    result = score_dsa(
        test_results=all_results or [{"passed": False}],
        complexity_rating=quality["complexity"],
        code_quality_rating=quality["code_quality"],
        time_taken_seconds=time_taken,
        time_limit_seconds=problem["time_limit_seconds"],
    )

    mode = attempt_ctx["mode"]
    track = attempt_ctx["track"]
    cutoff = get_cutoffs(track).get("dsa", 75)
    passed = result["score"] >= cutoff

    supabase_service.record_attempt({
        "user_id": user_id,
        "round": "dsa",
        "mode": mode,
        "score": result["score"],
        "meta": {
            "problem_id": problem["id"],
            "problem_title": problem["title"],
            "tests_passed": result["tests_passed"],
            "tests_total": result["tests_total"],
            "complexity": result["complexity"],
            "code_quality": result["code_quality"],
            "execution_error": exec_result["error"],
        },
    })

    session.pop("dsa_attempt", None)

    response = dict(result)
    response["cutoff"] = cutoff
    response["passed"] = passed
    response["mode"] = mode
    response["execution_error"] = exec_result["error"]

    if mode == "simulation":
        response["next_round_unlocked"] = passed
        response["message"] = (
            "Cleared. Technical Interview unlocked." if passed
            else f"Below cutoff ({cutoff}%). Practice weak areas and retry to unlock the Technical round."
        )

    return jsonify(response)


@dsa_bp.get("/history")
@login_required
def history():
    user_id = session["user_id"]
    mode = request.args.get("mode")
    attempts = supabase_service.get_attempts(user_id, "dsa", mode)
    return jsonify({"attempts": attempts})
