import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app

app = create_app()
client = app.test_client()


def test_all_routes():
    print("\n--- Testing API Endpoints & Page Routes ---")

    # 1. Health check
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.data}"
    print("✓ GET /api/health -> 200 OK")

    # 2. Auth login
    r = client.post("/api/auth/login", json={"email": "candidate@hiremind.ai", "password": "devpass"})
    assert r.status_code == 200, f"Auth login failed: {r.data}"
    print("✓ POST /api/auth/login -> 200 OK")

    # 3. Dashboard Progress & Readiness
    r = client.get("/api/dashboard/progress?user_id=u-dev-001")
    assert r.status_code == 200
    print(f"✓ GET /api/dashboard/progress -> 200 OK ({len(r.json.get('rounds', []))} rounds)")

    r = client.get("/api/dashboard/readiness?user_id=u-dev-001")
    assert r.status_code == 200
    print(f"✓ GET /api/dashboard/readiness -> 200 OK (Score: {r.json.get('readiness_score')}%)")

    # 4. Resume Scan & Bullet Improvement
    r = client.post("/api/resume/improve-bullet", json={"bullet": "Built REST APIs for user authentication.", "role": "Backend Engineer"})
    assert r.status_code == 200
    print("✓ POST /api/resume/improve-bullet -> 200 OK")

    r = client.post("/api/resume/scan", json={"raw_text": "Alex Mercer\nEmail: alex@example.com\nPython, Docker, SQL"})
    assert r.status_code == 200
    print("✓ POST /api/resume/scan -> 200 OK")

    # 5. Aptitude Questions
    r = client.get("/api/aptitude/questions")
    assert r.status_code == 200
    print(f"✓ GET /api/aptitude/questions -> 200 OK ({len(r.json)} questions)")

    # 6. DSA Problems
    r = client.get("/api/dsa/problems")
    assert r.status_code == 200
    print(f"✓ GET /api/dsa/problems -> 200 OK ({len(r.json)} problems)")

    # 7. Recruiter Jobs
    r = client.get("/api/recruit/jobs?company_id=comp_alpha_101")
    assert r.status_code == 200
    print(f"✓ GET /api/recruit/jobs -> 200 OK ({len(r.json['jobs'])} jobs)")

    # 8. HTML Page Views & Static Assets
    for path in ["/", "/dashboard", "/resume", "/interview", "/recruit", "/login", "/signup", "/css/style.css", "/js/api.js"]:
        r = client.get(path)
        assert r.status_code == 200, f"Route {path} failed: {r.status_code}"
        print(f"✓ GET {path} -> 200 OK")

    print("\n==================================================")
    print("🎉 ALL ENDPOINTS & VIEWS FUNCTIONAL (200 OK)!")
    print("==================================================")


if __name__ == "__main__":
    test_all_routes()
