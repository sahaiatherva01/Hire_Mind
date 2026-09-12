from flask import Blueprint, request, jsonify, session

from resume.parsing import parse_document
from resume.agents import ResumeOrchestrator, ImprovementAgent, JDMatchAgent
from db.client import db_client
from core.scoring import can_progress_to_next_round

resume_bp = Blueprint("resume", __name__, url_prefix="/api/resume")
orchestrator = ResumeOrchestrator()
improvement_agent = ImprovementAgent()
jd_match_agent = JDMatchAgent()


@resume_bp.route("/scan", methods=["POST"])
@resume_bp.route("/analyze", methods=["POST"])
def scan_resume():
    """
    Scans a resume file (PDF, DOCX, TXT) or raw text payload.
    Executes parsing, skill extraction, ATS 105pt scoring, and optional JD matching.
    """
    raw_text = None
    filename = "resume.txt"
    parsed_data = None
    jd_text = request.form.get("job_description") or request.form.get("jd_text")
    user_id = session.get("user_id") or request.form.get("user_id") or "u-dev-001"

    file_url = None
    if "file" in request.files:
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Empty filename provided."}), 400
        filename = file.filename
        try:
            file_bytes = file.read()
            parsed_data = parse_document(file_bytes, filename)
            file_url = db_client.upload_resume_file(file_bytes, filename, user_id)
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as e:
            return jsonify({"error": f"Failed to process file: {str(e)}"}), 500

    elif request.is_json:
        data = request.get_json(silent=True) or {}
        raw_text = data.get("raw_text") or data.get("text")
        filename = data.get("filename", "pasted_resume.txt")
        jd_text = jd_text or data.get("job_description") or data.get("jd_text")
        user_id = data.get("user_id", user_id)

        if not raw_text or not raw_text.strip():
            return jsonify({"error": "Empty resume text provided."}), 400

        try:
            parsed_data = parse_document(raw_text.encode("utf-8"), filename)
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        return jsonify({"error": "No file or text provided in request."}), 400

    # Run multi-agent scan
    report = orchestrator.run_scan(parsed_data=parsed_data, jd_text=jd_text, user_id=user_id)

    # Persist to database (including Supabase Storage file_url if available)
    resume_id = db_client.save_resume(
        user_id=user_id,
        filename=filename,
        parsed_text=parsed_data.get("raw_text", ""),
        structured_data=report,
        ats_score=report["score"],
        file_url=file_url
    )
    report["resume_id"] = resume_id
    report["file_url"] = file_url

    # Update round 1 score in user simulation progress
    prog = db_client.get_user_progress(user_id)
    round_scores = prog.get("round_scores", {})
    round_scores["resume_screening"] = report["score"]
    prog["round_scores"] = round_scores

    progression = can_progress_to_next_round("resume_screening", report["score"])
    report["progression"] = progression

    db_client.save_user_progress(user_id, "default", prog)

    return jsonify(report), 200


@resume_bp.route("/upload", methods=["POST"])
def upload_file_only():
    """Parses file layout and returns structural metadata."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]
    try:
        parsed = parse_document(file.read(), file.filename)
        return jsonify(parsed), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@resume_bp.route("/improve-bullet", methods=["POST"])
def improve_bullet():
    """Rewrites bullet point using Google XYZ formula grounded in retrieved examples."""
    data = request.get_json(silent=True) or {}
    bullet = data.get("bullet")
    role = data.get("role", "Software Engineer")
    user_id = session.get("user_id") or data.get("user_id", "u-dev-001")

    if not bullet or not bullet.strip():
        return jsonify({"error": "No bullet text provided."}), 400

    out = improvement_agent.improve_bullet(bullet, role=role, user_id=user_id)
    return jsonify(out), 200


@resume_bp.route("/match-jd", methods=["POST"])
def match_jd():
    """Matches resume skills against target job description."""
    data = request.get_json(silent=True) or {}
    skills = data.get("skills", [])
    jd_text = data.get("jd_text") or data.get("job_description")
    user_id = session.get("user_id") or data.get("user_id", "u-dev-001")

    if not jd_text or not jd_text.strip():
        return jsonify({"error": "Job description text is required."}), 400

    out = jd_match_agent.match_job_description(skills, jd_text, user_id=user_id)
    return jsonify(out), 200


@resume_bp.route("/history", methods=["GET"])
def resume_history():
    user_id = request.args.get("user_id") or session.get("user_id") or "u-dev-001"
    resumes = db_client.get_resumes(user_id)
    return jsonify(resumes), 200
