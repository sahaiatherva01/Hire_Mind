"""
HireMind AI — Full API Endpoints Test
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BASE_DIR))

import app

client = app.app.test_client()

def test_all_routes():
    print("--- Testing API Endpoints ---")
    
    # 1. Health
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health failed: {r.data}"
    print("✓ GET /api/health -> 200")

    # 2. Auth
    r = client.post("/api/auth/login", json={"email": "candidate@hiremind.ai", "password": "devpass"})
    assert r.status_code == 200, f"Auth login failed: {r.data}"
    print("✓ POST /api/auth/login -> 200")

    # 3. Dashboard Progress & Readiness
    r = client.get("/api/dashboard/progress?user_id=u-dev-001")
    assert r.status_code == 200
    print(f"✓ GET /api/dashboard/progress -> 200 ({len(r.json['rounds'])} rounds)")

    r = client.get("/api/dashboard/readiness?user_id=u-dev-001")
    assert r.status_code == 200
    print(f"✓ GET /api/dashboard/readiness -> 200 (Readiness: {r.json['overall_readiness']}%)")

    # 4. Resume Bullet Improvement
    r = client.post("/api/resume/improve-bullet", json={"bullet_text": "Built REST APIs for user authentication.", "role_context": "Backend Engineer"})
    assert r.status_code == 200
    print("✓ POST /api/resume/improve-bullet -> 200")

    # 5. Aptitude Questions
    r = client.get("/api/aptitude/questions?mode=practice")
    assert r.status_code == 200
    print(f"✓ GET /api/aptitude/questions -> 200 ({r.json['total']} questions)")

    # 6. DSA Problems
    r = client.get("/api/dsa/problems?mode=practice")
    assert r.status_code == 200
    print(f"✓ GET /api/dsa/problems -> 200 ({len(r.json['problems'])} problems)")

    # 7. Recruiter Jobs
    r = client.get("/api/recruit/jobs?company_id=comp-techcorp-101")
    assert r.status_code == 200
    print(f"✓ GET /api/recruit/jobs -> 200 ({len(r.json['jobs'])} jobs)")

    # 8. Static HTML Routes
    for path in ["/", "/dashboard", "/resume", "/interview", "/recruit", "/login", "/signup"]:
        r = client.get(path)
        assert r.status_code == 200, f"Route {path} failed: {r.status_code}"
        print(f"✓ GET {path} -> 200 HTML page")

    print("\n--- ALL API ENDPOINTS VERIFIED SUCCESSFULLY ---")

if __name__ == "__main__":
    test_all_routes()
