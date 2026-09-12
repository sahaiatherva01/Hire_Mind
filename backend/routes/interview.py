"""
HireMind AI — Interview Simulator Routes (Module B)
"""
from flask import Blueprint, request, jsonify, session
from agents.module_b.interview_orchestrator import interview_orchestrator
from services.round_engine import round_engine

interview_bp = Blueprint("interview", __name__, url_prefix="/api/interview")


@interview_bp.route("/generate-questions", methods=["POST"])
def generate_questions():
    """Generates tailored question bank for an interview session."""
    data = request.get_json(silent=True) or {}
    resume_id = data.get("resume_id")
    target_role = data.get("target_role", "Software Engineer")
    company_track = data.get("company_track", "default")
    mode = data.get("mode", "practice")
    user_id = session.get("user_id") or data.get("user_id") or "u-dev-001"

    if not resume_id:
        return jsonify({"error": "resume_id is required"}), 400

    # Verification: check cutoff clearance in Simulation mode
    if mode == "simulation":
        can_access = round_engine.can_access_round(user_id=user_id, round_name="technical", mode=mode, track=company_track)
        if not can_access:
            return jsonify({
                "error": "LOCKED_ROUND",
                "message": "You must clear earlier Simulation rounds (Resume Screening, Aptitude, DSA) before unlocking the Technical Interview."
            }), 403

    try:
        res = interview_orchestrator.generate_and_store_questions(
            resume_id=resume_id,
            target_role=target_role,
            company_track=company_track,
            user_id=user_id,
            mode=mode
        )
        return jsonify(res), 201
    except Exception as e:
        return jsonify({"error": f"Failed to generate questions: {str(e)}"}), 500


@interview_bp.route("/start", methods=["POST"])
def start_interview():
    """Starts interview session and returns first active question."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    voice_pref = data.get("voice_preference", "male")

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    try:
        res = interview_orchestrator.start_interview(
            session_id=session_id,
            voice_preference=voice_pref
        )
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": f"Failed to start interview: {str(e)}"}), 500


@interview_bp.route("/answer", methods=["POST"])
def submit_answer():
    """Submits candidate answer turn and returns follow-up probe or next topic question."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    question_bank_id = data.get("question_bank_id")
    answer_text = data.get("answer_text", "").strip()

    if not session_id or not question_bank_id:
        return jsonify({"error": "session_id and question_bank_id are required"}), 400

    if not answer_text:
        return jsonify({"error": "answer_text cannot be empty"}), 400

    try:
        res = interview_orchestrator.submit_answer(
            session_id=session_id,
            question_bank_id=question_bank_id,
            answer_text=answer_text
        )
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": f"Failed to submit answer: {str(e)}"}), 500


@interview_bp.route("/end", methods=["POST"])
def end_interview():
    """Concludes interview session and generates final debrief report."""
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    try:
        res = interview_orchestrator.end_interview_and_generate_report(session_id=session_id)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": f"Failed to finalize report: {str(e)}"}), 500
