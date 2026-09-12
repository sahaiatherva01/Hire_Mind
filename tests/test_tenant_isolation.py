import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from db.client import db_client


def test_recruiter_tenant_isolation():
    print("\n--- Testing Recruiter Multi-Tenant Isolation ---")
    app = create_app()
    client = app.test_client()

    company_a = "comp_alpha_101"
    company_b = "comp_beta_202"

    # 1. Company A creates a job posting
    res_a = client.post("/api/recruit/jobs", json={
        "company_id": company_a,
        "title": "Lead Security Engineer",
        "description": "Lead cloud security, zero-trust architecture, and compliance.",
        "requirements": ["AWS", "IAM", "Kubernetes", "Cryptography"],
        "seniority": "lead"
    })
    assert res_a.status_code == 201
    job_a_id = res_a.get_json()["job_id"]
    print(f"✓ Company A created job #{job_a_id}")

    # 2. Company B creates a job posting
    res_b = client.post("/api/recruit/jobs", json={
        "company_id": company_b,
        "title": "Data Scientist",
        "description": "Develop predictive ML models and pipelines.",
        "requirements": ["Python", "PyTorch", "SQL", "Pandas"],
        "seniority": "mid"
    })
    assert res_b.status_code == 201
    job_b_id = res_b.get_json()["job_id"]
    print(f"✓ Company B created job #{job_b_id}")

    # 3. Verify Company A only sees Company A jobs
    list_a = client.get(f"/api/recruit/jobs?company_id={company_a}")
    assert list_a.status_code == 200
    jobs_for_a = list_a.get_json()["jobs"]
    job_ids_for_a = [j["id"] for j in jobs_for_a]
    assert job_a_id in job_ids_for_a
    assert job_b_id not in job_ids_for_a, "SECURITY VIOLATION: Company A can see Company B's job!"
    print("✓ Tenant filter verified: Company A cannot see Company B's job list.")

    # 4. Verify Company B only sees Company B jobs
    list_b = client.get(f"/api/recruit/jobs?company_id={company_b}")
    assert list_b.status_code == 200
    jobs_for_b = list_b.get_json()["jobs"]
    job_ids_for_b = [j["id"] for j in jobs_for_b]
    assert job_b_id in job_ids_for_b
    assert job_a_id not in job_ids_for_b, "SECURITY VIOLATION: Company B can see Company A's job!"
    print("✓ Tenant filter verified: Company B cannot see Company A's job list.")

    # 5. Screen candidate for Company A's job
    screen_a = client.post("/api/recruit/screen", json={
        "company_id": company_a,
        "job_id": job_a_id,
        "title": "Lead Security Engineer",
        "description": "AWS IAM cryptography",
        "candidates": [
            {"id": "cand_sec_1", "name": "Eve Cyber", "raw_text": "Experienced security analyst with AWS IAM.", "skills": ["AWS", "IAM"]}
        ]
    })
    assert screen_a.status_code == 200

    # 6. Verify Company A can view its own job candidates
    cands_a = client.get(f"/api/recruit/jobs/{job_a_id}/candidates?company_id={company_a}")
    assert cands_a.status_code == 200
    assert len(cands_a.get_json()["candidates"]) >= 1
    print("✓ Company A authorized access to its own candidates.")

    # 7. SECURITY CHECK: Verify Company B is FORBIDDEN (403) from accessing Company A's candidates
    unauthorized_attempt = client.get(f"/api/recruit/jobs/{job_a_id}/candidates?company_id={company_b}")
    assert unauthorized_attempt.status_code == 403, f"Expected 403 Forbidden, got {unauthorized_attempt.status_code}"
    print("✓ Cross-tenant access blocked with HTTP 403 Forbidden.")

    # 8. SECURITY CHECK: Verify Company B cannot trigger screening on Company A's job_id
    mismatched_screening = client.post("/api/recruit/screen", json={
        "company_id": company_b,
        "job_id": job_a_id,
        "title": "Spoofed Screening",
        "description": "Attempting unauthorized screening on job A",
        "candidates": []
    })
    assert mismatched_screening.status_code == 403, f"Expected 403 Forbidden, got {mismatched_screening.status_code}"
    print("✓ Cross-tenant screening attempt blocked with HTTP 403 Forbidden.")

    print("\n==================================================")
    print("🛡️ MULTI-TENANT ISOLATION FULLY VERIFIED!")
    print("==================================================")


if __name__ == "__main__":
    test_recruiter_tenant_isolation()
