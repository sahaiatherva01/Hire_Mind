"""
HireMind AI — DSA Practice & Sandbox Routes
"""
import json
import os
from flask import Blueprint, request, jsonify, session
from config import Config
from services.code_sandbox import code_sandbox
from services.scoring import score_dsa_round
from services.round_engine import round_engine

dsa_bp = Blueprint("dsa", __name__, url_prefix="/api/dsa")


def _load_problems():
    p = os.path.join(Config.DATA_DIR, "dsa_problems.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@dsa_bp.route("/problems", methods=["GET"])
def get_problems():
    """Returns list of DSA problems."""
    user_id = request.args.get("user_id") or session.get("user_id") or "u-dev-001"
    mode = request.args.get("mode", "practice")
    track = request.args.get("track", "default")

    if mode == "simulation":
        if not round_engine.can_access_round(user_id=user_id, round_name="dsa", mode=mode, track=track):
            return jsonify({
                "error": "LOCKED_ROUND",
                "message": "You must clear Aptitude before unlocking the DSA Coding Round in Simulation Mode."
            }), 403

    problems = _load_problems()
    # Strip hidden tests from summary list
    summary = []
    for p in problems:
        summary.append({
            "id": p["id"],
            "title": p["title"],
            "difficulty": p["difficulty"],
            "topic": p["topic"],
            "examples": p.get("examples", [])
        })

    return jsonify({"problems": summary}), 200


@dsa_bp.route("/problems/<int:problem_id>", methods=["GET"])
def get_problem_detail(problem_id: int):
    """Returns single problem with statement, starter code, and public tests."""
    problems = _load_problems()
    target = next((p for p in problems if p["id"] == problem_id), None)
    if not target:
        return jsonify({"error": "Problem not found"}), 404

    return jsonify({
        "id": target["id"],
        "title": target["title"],
        "difficulty": target["difficulty"],
        "topic": target["topic"],
        "statement": target["statement"],
        "starter_code": target["starter_code"],
        "examples": target.get("examples", []),
        "public_tests": target.get("public_tests", []),
        "time_limit_seconds": target.get("time_limit_seconds", 900)
    }), 200


@dsa_bp.route("/run", methods=["POST"])
def run_code():
    """Runs code against public test cases only."""
    data = request.get_json(silent=True) or {}
    problem_id = data.get("problem_id")
    code = data.get("code", "")

    if not code.strip():
        return jsonify({"error": "Code cannot be empty."}), 400

    problems = _load_problems()
    target = next((p for p in problems if p["id"] == problem_id), None)
    if not target:
        return jsonify({"error": "Problem not found."}), 404

    public_tests = target.get("public_tests", [])
    exec_res = code_sandbox.execute_code(code, public_tests)
    return jsonify(exec_res), 200


@dsa_bp.route("/submit", methods=["POST"])
def submit_code():
    """Runs code against public + hidden test cases, evaluates correctness/complexity/speed, and records round score."""
    data = request.get_json(silent=True) or {}
    problem_id = data.get("problem_id")
    code = data.get("code", "")
    time_taken_sec = int(data.get("time_taken_sec", 300))
    mode = data.get("mode", "practice")
    track = data.get("track", "default")
    user_id = session.get("user_id") or data.get("user_id") or "u-dev-001"

    if not code.strip():
        return jsonify({"error": "Code cannot be empty."}), 400

    problems = _load_problems()
    target = next((p for p in problems if p["id"] == problem_id), None)
    if not target:
        return jsonify({"error": "Problem not found."}), 404

    all_tests = target.get("public_tests", []) + target.get("hidden_tests", [])
    exec_res = code_sandbox.execute_code(code, all_tests)

    score_res = score_dsa_round(
        tests_passed=exec_res["passed_tests"],
        total_tests=exec_res["total_tests"],
        runtime_ms=exec_res["average_runtime_ms"],
        code_lines=exec_res["code_lines"],
        time_taken_sec=time_taken_sec
    )

    # Record in round engine
    round_engine.record_round_attempt(
        user_id=user_id,
        round_name="dsa",
        score=score_res["score"],
        mode=mode,
        track=track,
        breakdown=score_res
    )

    return jsonify({
        "execution": exec_res,
        "score_details": score_res,
        "passed": score_res["passed"]
    }), 200
