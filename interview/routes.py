import os
import json
from flask import Blueprint, request, jsonify, session

from config import Config
from interview.agents import InterviewOrchestrator
from interview.sandbox import CodeSandbox
from db.client import db_client
from core.scoring import can_progress_to_next_round

interview_bp = Blueprint("interview", __name__)
orchestrator = InterviewOrchestrator()


# --- Live Interview Simulator Endpoints ---
@interview_bp.route("/api/interview/start", methods=["POST"])
def start_interview():
    data = request.get_json(silent=True) or {}
    role = data.get("role", "Software Engineer")
    stage = data.get("stage", "technical")
    user_id = session.get("user_id") or data.get("user_id", "u-dev-001")

    session_data = orchestrator.start_session(user_id=user_id, role=role, stage=stage)
    return jsonify(session_data), 200


@interview_bp.route("/api/interview/answer", methods=["POST"])
@interview_bp.route("/api/interview/submit-answer", methods=["POST"])
def submit_answer():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    answer = data.get("answer")
    user_id = session.get("user_id") or data.get("user_id", "u-dev-001")

    if not session_id or not answer:
        return jsonify({"error": "Missing session_id or answer."}), 400

    result = orchestrator.process_candidate_answer(session_id=session_id, answer=answer, user_id=user_id)
    return jsonify(result), 200


@interview_bp.route("/api/interview/session/<session_id>", methods=["GET"])
def get_session(session_id: str):
    sess = db_client.get_interview_session(session_id)
    if not sess:
        return jsonify({"error": "Session not found."}), 404
    turns = db_client.get_session_turns(session_id)
    return jsonify({"session": sess, "turns": turns}), 200


# --- Aptitude Assessment Endpoints ---
@interview_bp.route("/api/aptitude/questions", methods=["GET"])
def get_aptitude_questions():
    apt_path = Config.DATA_DIR / "aptitude_questions.json"
    if os.path.exists(apt_path):
        with open(apt_path, "r", encoding="utf-8") as f:
            questions = json.load(f)
            # Strip correct_answer before sending to frontend
            sanitized = []
            for q in questions:
                sanitized.append({
                    "id": q.get("id"),
                    "category": q.get("category"),
                    "difficulty": q.get("difficulty"),
                    "question": q.get("question"),
                    "options": q.get("options")
                })
            return jsonify(sanitized), 200
    return jsonify([]), 200


@interview_bp.route("/api/aptitude/submit", methods=["POST"])
def submit_aptitude():
    data = request.get_json(silent=True) or {}
    user_answers = data.get("answers", {})  # { q_id: selected_index }
    user_id = session.get("user_id") or data.get("user_id", "u-dev-001")

    apt_path = Config.DATA_DIR / "aptitude_questions.json"
    correct_count = 0
    total_count = 0

    if os.path.exists(apt_path):
        with open(apt_path, "r", encoding="utf-8") as f:
            all_q = json.load(f)
            total_count = len(all_q)
            for q in all_q:
                qid = str(q.get("id"))
                if qid in user_answers and user_answers[qid] == q.get("correct_answer"):
                    correct_count += 1

    score = round((correct_count / max(1, total_count)) * 100.0, 1)

    # Update round 2 progress
    prog = db_client.get_user_progress(user_id)
    round_scores = prog.get("round_scores", {})
    round_scores["aptitude"] = score
    prog["round_scores"] = round_scores
    db_client.save_user_progress(user_id, "default", prog)

    progression = can_progress_to_next_round("aptitude", score)

    return jsonify({
        "score": score,
        "correct": correct_count,
        "total": total_count,
        "progression": progression
    }), 200


# --- DSA Sandbox Endpoints ---
@interview_bp.route("/api/dsa/problems", methods=["GET"])
def get_dsa_problems():
    dsa_path = Config.DATA_DIR / "dsa_problems.json"
    if os.path.exists(dsa_path):
        with open(dsa_path, "r", encoding="utf-8") as f:
            problems = json.load(f)
            # Remove hidden tests for client display
            public_problems = []
            for p in problems:
                p_copy = {k: v for k, v in p.items() if k != "hidden_tests"}
                public_problems.append(p_copy)
            return jsonify(public_problems), 200
    return jsonify([]), 200


@interview_bp.route("/api/dsa/run", methods=["POST"])
def run_dsa_code():
    data = request.get_json(silent=True) or {}
    problem_id = data.get("problem_id", 1)
    code = data.get("code", "")
    user_id = session.get("user_id") or data.get("user_id", "u-dev-001")

    if not code:
        return jsonify({"error": "No code submitted."}), 400

    dsa_path = Config.DATA_DIR / "dsa_problems.json"
    target_problem = None
    if os.path.exists(dsa_path):
        with open(dsa_path, "r", encoding="utf-8") as f:
            for p in json.load(f):
                if p.get("id") == problem_id:
                    target_problem = p
                    break

    if not target_problem:
        return jsonify({"error": f"Problem #{problem_id} not found."}), 404

    # Run against both public and hidden test cases
    all_tests = target_problem.get("public_tests", []) + target_problem.get("hidden_tests", [])
    exec_result = CodeSandbox.execute_code(code, all_tests)

    # If all passed or high correctness, update round 3 score
    if exec_result.get("correctness_percentage", 0) >= 70:
        prog = db_client.get_user_progress(user_id)
        round_scores = prog.get("round_scores", {})
        round_scores["dsa"] = exec_result["correctness_percentage"]
        prog["round_scores"] = round_scores
        db_client.save_user_progress(user_id, "default", prog)

    exec_result["progression"] = can_progress_to_next_round("dsa", exec_result.get("correctness_percentage", 0))
    return jsonify(exec_result), 200
