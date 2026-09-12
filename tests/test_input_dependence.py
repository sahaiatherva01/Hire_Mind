import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from resume.parsing import parse_document
from resume.agents import ResumeOrchestrator, JDMatchAgent


def test_input_dependent_scoring():
    print("\n--- 1. Testing Differential ATS+ Scoring on Two Distinct Resumes ---")
    orchestrator = ResumeOrchestrator()

    # Resume 1: Strong, quantified Senior Systems Engineer
    resume_strong = """
    Sarah Connor
    Email: sarah.c@systems.io | Phone: +1-415-555-0199 | San Francisco, CA
    
    Education:
    M.S. in Computer Science, Stanford University (2020)
    
    Experience:
    Principal Infrastructure Engineer at CloudScale (2021 - Present)
    - Architected multi-region Kubernetes clusters across AWS and GCP, achieving 99.999% uptime for 50M requests/day.
    - Optimized PostgreSQL query execution plans and Redis caching, cutting p99 latency by 55% from 420ms to 190ms.
    - Spearheaded zero-downtime deployment pipelines using Docker and GitHub Actions, increasing release frequency by 3x.
    
    Projects:
    Distributed Consensus Engine
    - Built Raft-based consensus protocol in Go with snapshotting and automated leader election.
    
    Skills:
    Go, Python, Kubernetes, Docker, AWS, GCP, PostgreSQL, Redis, Linux, System Design, CI/CD
    """

    # Resume 2: Sparse, unquantified entry level
    resume_weak = """
    John Doe
    
    Summary:
    Recent graduate looking for entry level work.
    
    Experience:
    Helped fix website bugs.
    Wrote some scripts in Python.
    
    Skills:
    Python, HTML
    """

    parsed_strong = parse_document(resume_strong.encode("utf-8"), "strong.txt")
    parsed_weak = parse_document(resume_weak.encode("utf-8"), "weak.txt")

    scan_strong = orchestrator.run_scan(parsed_strong)
    scan_weak = orchestrator.run_scan(parsed_weak)

    score_strong = scan_strong["score"]
    score_weak = scan_weak["score"]

    print(f"Strong Resume ATS Score: {score_strong}/100")
    print(f"Weak Resume ATS Score:   {score_weak}/100")

    assert score_strong > score_weak + 20.0, f"Expected strong resume to score substantially higher than weak resume ({score_strong} vs {score_weak})"
    assert scan_strong["category_scores"]["quantifiable_impact"]["score"] > scan_weak["category_scores"]["quantifiable_impact"]["score"]
    assert scan_strong["category_scores"]["structure"]["score"] > scan_weak["category_scores"]["structure"]["score"]
    print("✓ Dynamic ATS+ scoring confirmed: Scores strongly differentiate based on real content.")


def test_input_dependent_jd_matching():
    print("\n--- 2. Testing Differential JD Matching & Stability ---")
    candidate_skills = ["Python", "Flask", "PostgreSQL", "Docker"]
    jd_agent = JDMatchAgent()

    # JD A: Python Backend role (High alignment)
    jd_backend = "Looking for a Python Backend Engineer experienced with Flask, PostgreSQL, and Docker microservices."

    # JD B: Machine Learning role (Low alignment / many gaps)
    jd_ml = "Hiring Senior ML Engineer proficient in PyTorch, Computer Vision, CUDA, Model Quantization, and CI/CD."

    match_a = jd_agent.match_job_description(candidate_skills, jd_backend)["result"]
    match_b = jd_agent.match_job_description(candidate_skills, jd_ml)["result"]

    print(f"Match for Backend JD: {match_a['jd_match_score']}% (Matched: {match_a['matched_skills']})")
    print(f"Match for ML JD:      {match_b['jd_match_score']}% (Missing: {match_b['missing_skills']})")

    assert match_a["jd_match_score"] > match_b["jd_match_score"], "Backend JD should match substantially higher than ML JD"
    assert "Python" in match_a["matched_skills"]
    assert "PyTorch" in match_b["missing_skills"] or "Machine Learning" in match_b["missing_skills"] or len(match_b["missing_skills"]) > 0
    print("✓ Dynamic JD matching confirmed: Gaps and match % genuinely reflect JD requirements.")

    # Stability check: Run JD A twice
    match_a_repeat = jd_agent.match_job_description(candidate_skills, jd_backend)["result"]
    assert match_a["jd_match_score"] == match_a_repeat["jd_match_score"], "JD match must be deterministic and stable"
    print("✓ Scoring stability confirmed: Repeated identical inputs yield identical outputs.")


if __name__ == "__main__":
    test_input_dependent_scoring()
    test_input_dependent_jd_matching()
    print("\n==================================================")
    print("📊 REAL-DATA INPUT DEPENDENCE FULLY CONFIRMED!")
    print("==================================================")
