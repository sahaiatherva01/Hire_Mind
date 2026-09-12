from flask import Blueprint, request, jsonify, session

from recruit.agents import ScreeningOrchestrator
from db.client import db_client

recruit_bp = Blueprint("recruit", __name__, url_prefix="/api/recruit")
orchestrator = ScreeningOrchestrator()


@recruit_bp.route("/jobs", methods=["GET"])
def get_company_jobs():
    """Returns jobs strictly filtered by the authenticated company_id."""
    company_id = request.args.get("company_id") or session.get("company_id")
    if not company_id:
        return jsonify({"error": "company_id is required for recruiter job operations."}), 400

    jobs = db_client.get_jobs(company_id=company_id)
    return jsonify({"company_id": company_id, "jobs": jobs}), 200


@recruit_bp.route("/jobs", methods=["POST"])
def create_job():
    """Creates a job posting tied strictly to the company_id."""
    data = request.get_json(silent=True) or {}
    company_id = data.get("company_id") or session.get("company_id")
    title = data.get("title")
    description = data.get("description", "")
    requirements = data.get("requirements", [])
    seniority = data.get("seniority", "mid")

    if not company_id:
        return jsonify({"error": "company_id is required."}), 400
    if not title:
        return jsonify({"error": "Job title is required."}), 400

    job_id = db_client.create_job(
        company_id=company_id,
        title=title,
        description=description,
        requirements=requirements,
        seniority=seniority
    )
    return jsonify({"message": "Job created successfully", "job_id": job_id, "company_id": company_id}), 201


@recruit_bp.route("/jobs/<job_id>/candidates", methods=["GET"])
def get_job_candidates(job_id: str):
    """
    Returns candidate applications for a job.
    Enforces strict tenant isolation: returns 403 Forbidden if job belongs to another company.
    """
    company_id = request.args.get("company_id") or session.get("company_id")
    if not company_id:
        return jsonify({"error": "company_id parameter is required."}), 400

    # Verify job ownership
    job = db_client.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404

    if job.get("company_id") != company_id:
        return jsonify({"error": "Forbidden: Cannot access candidates for another company's job posting."}), 403

    candidates = db_client.get_job_applications(job_id=job_id, company_id=company_id)
    return jsonify({"job_id": job_id, "company_id": company_id, "candidates": candidates}), 200


@recruit_bp.route("/screen", methods=["POST"])
def screen_candidates_batch():
    """
    Runs multi-agent screening on a candidate batch against a target job description.
    Verifies tenant ownership if job_id is provided.
    """
    data = request.get_json(silent=True) or {}
    company_id = data.get("company_id") or session.get("company_id")
    job_id = data.get("job_id")
    title = data.get("title")
    description = data.get("description", "")
    candidates = data.get("candidates", [])
    user_id = session.get("user_id") or "recruiter-001"

    if not company_id:
        return jsonify({"error": "company_id is required for batch screening."}), 400

    if job_id:
        job = db_client.get_job(job_id)
        if not job:
            return jsonify({"error": f"Job #{job_id} not found."}), 404
        if job.get("company_id") != company_id:
            return jsonify({"error": "Forbidden: Tenant mismatch for job_id."}), 403
        title = title or job.get("title")
        description = description or job.get("description")

    if not title or not description:
        return jsonify({"error": "Job title and description are required."}), 400

    screen_result = orchestrator.screen_batch(
        title=title,
        description=description,
        candidates=candidates,
        user_id=user_id
    )

    # Persist ranked candidates as applications if job_id exists
    if job_id:
        for cand in screen_result["ranking"]["ranked_candidates"]:
            db_client.submit_job_application(
                job_id=job_id,
                candidate_id=cand.get("id") or cand.get("email", "unknown"),
                resume_id=cand.get("resume_id", "batch"),
                score=cand.get("composite_score", 0),
                rank_data=cand
            )

    return jsonify({
        "company_id": company_id,
        "job_id": job_id,
        **screen_result
    }), 200
