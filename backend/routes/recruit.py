"""
HireMind AI — Recruiter Portal Routes (Module C)
"""
from flask import Blueprint, request, jsonify, session
from agents.module_c.screening_orchestrator import screening_orchestrator

recruit_bp = Blueprint("recruit", __name__, url_prefix="/api/recruit")


@recruit_bp.route("/jobs", methods=["POST"])
def create_job():
    """Creates a new job posting and extracts structured requirements."""
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    department = (data.get("department") or "Engineering").strip()
    jd_text = (data.get("jd_text") or "").strip()
    company_id = session.get("company_id") or data.get("company_id") or "comp-techcorp-101"

    if not title or not jd_text:
        return jsonify({"error": "Job title and description are required."}), 400

    try:
        res = screening_orchestrator.create_job(
            company_id=company_id,
            title=title,
            department=department,
            jd_text=jd_text
        )
        return jsonify(res), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create job: {str(e)}"}), 500


@recruit_bp.route("/jobs", methods=["GET"])
def list_jobs():
    """Lists all active jobs for the recruiter's company."""
    company_id = session.get("company_id") or request.args.get("company_id") or "comp-techcorp-101"
    jobs = screening_orchestrator.list_company_jobs(company_id=company_id)
    return jsonify({"jobs": jobs}), 200


@recruit_bp.route("/screen-batch", methods=["POST"])
def screen_batch_resumes():
    """
    Accepts multiple uploaded resume files for a job, runs bulk matching,
    and returns explainable Strong/Review/Weak rankings.
    """
    job_id = request.form.get("job_id")
    company_id = session.get("company_id") or request.form.get("company_id") or "comp-techcorp-101"

    if not job_id:
        return jsonify({"error": "job_id is required."}), 400

    uploaded_files = request.files.getlist("files")
    if not uploaded_files or len(uploaded_files) == 0:
        return jsonify({"error": "No resume files uploaded."}), 400

    files_data = []
    for f in uploaded_files:
        if f.filename:
            files_data.append({
                "filename": f.filename,
                "file_bytes": f.read(),
                "candidate_name": f.filename.replace(".pdf", "").replace(".docx", "").replace("_", " ").title()
            })

    try:
        res = screening_orchestrator.process_batch_resumes(
            company_id=company_id,
            job_id=job_id,
            files_data=files_data
        )
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": f"Batch screening failed: {str(e)}"}), 500


@recruit_bp.route("/candidates", methods=["GET"])
def list_candidates():
    """Returns ranked candidate list for a job."""
    job_id = request.args.get("job_id")
    company_id = session.get("company_id") or request.args.get("company_id") or "comp-techcorp-101"

    if not job_id:
        return jsonify({"error": "job_id is required."}), 400

    candidates = screening_orchestrator.list_job_candidates(company_id=company_id, job_id=job_id)
    return jsonify({"candidates": candidates}), 200


@recruit_bp.route("/generate-assessment", methods=["POST"])
def generate_assessment():
    """Generates customized assessment test for the role."""
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    duration_minutes = int(data.get("duration_minutes", 30))
    company_id = session.get("company_id") or data.get("company_id") or "comp-techcorp-101"

    if not job_id:
        return jsonify({"error": "job_id is required."}), 400

    try:
        res = screening_orchestrator.generate_role_assessment(
            company_id=company_id,
            job_id=job_id,
            duration_minutes=duration_minutes
        )
        return jsonify(res), 201
    except Exception as e:
        return jsonify({"error": f"Assessment generation failed: {str(e)}"}), 500
