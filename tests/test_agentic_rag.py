import sys
from pathlib import Path

# Add root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.retrieval import retrieve
from core.scoring import calculate_ats_category_scores, calculate_overall_readiness, can_progress_to_next_round
from resume.parsing import parse_document
from resume.agents import ResumeOrchestrator
from interview.agents import InterviewOrchestrator
from interview.sandbox import CodeSandbox
from recruit.agents import ScreeningOrchestrator


def test_rag_collections():
    print("\n--- 1. Testing RAG Retrieval Across Seed Collections ---")

    # Collection 1: kb_interview_questions
    q_matches = retrieve(query="Java garbage collection memory leak", collection="kb_interview_questions", top_k=2)
    assert len(q_matches) > 0, "kb_interview_questions retrieval failed"
    print(f"✓ kb_interview_questions retrieved {len(q_matches)} items. Top: {q_matches[0]['content'][:60]}... (sim: {q_matches[0]['similarity']})")

    # Collection 2: kb_skills_taxonomy
    s_matches = retrieve(query="Spring Boot", collection="kb_skills_taxonomy", top_k=1)
    assert len(s_matches) > 0, "kb_skills_taxonomy retrieval failed"
    print(f"✓ kb_skills_taxonomy retrieved: {s_matches[0]['content'][:60]} (sim: {s_matches[0]['similarity']})")

    # Collection 3: kb_jd_corpus
    jd_matches = retrieve(query="Senior Backend Engineer Python FastAPI", collection="kb_jd_corpus", top_k=1)
    assert len(jd_matches) > 0, "kb_jd_corpus retrieval failed"
    print(f"✓ kb_jd_corpus retrieved: {jd_matches[0]['content'][:60]} (sim: {jd_matches[0]['similarity']})")

    # Collection 4: kb_resume_best_practices
    rbp_matches = retrieve(query="Google XYZ formula quantify metrics bullet", collection="kb_resume_best_practices", top_k=1)
    assert len(rbp_matches) > 0, "kb_resume_best_practices retrieval failed"
    print(f"✓ kb_resume_best_practices retrieved: {rbp_matches[0]['content'][:60]} (sim: {rbp_matches[0]['similarity']})")

    # Collection 5: kb_company_interview_style (Unpopulated per directive)
    comp_matches = retrieve(query="Amazon Leadership Principles", collection="kb_company_interview_style", top_k=1)
    assert len(comp_matches) == 0, "kb_company_interview_style should be unpopulated until real B2B ingestion"
    print("✓ kb_company_interview_style is cleanly unpopulated per directive.")


def test_module_a_resume_intelligence():
    print("\n--- 2. Testing Module A: Resume Intelligence Pipeline ---")
    raw_resume = """
    Alex Mercer
    Email: alex@example.com | Phone: +1-555-0199 | San Francisco, CA
    
    Education:
    B.S. Computer Science, UC Berkeley (GPA: 3.8/4.0), 2022
    
    Experience:
    Software Engineer at TechCorp Solutions (2022 - Present)
    - Architected and deployed microservices using Python and Flask, reducing API response times by 35% for 2M daily requests.
    - Spearheaded PostgreSQL migration to AWS RDS, cutting database query latency by 40%.
    - Built real-time notification service with Redis and WebSockets.
    
    Projects:
    Distributed Task Queue
    - Implemented asynchronous worker pool in Go and Redis with exponential backoff retry logic.
    
    Skills:
    Python, Flask, Go, PostgreSQL, Redis, Docker, Kubernetes, AWS, Git
    """
    parsed = parse_document(raw_resume.encode("utf-8"), "alex_resume.txt")
    assert parsed["page_count"] >= 1
    assert parsed["contact"]["email"] == "alex@example.com"
    assert parsed["contact"]["phone"] == "+1-555-0199"

    orchestrator = ResumeOrchestrator()
    scan_report = orchestrator.run_scan(parsed_data=parsed, jd_text="Looking for Senior Python Backend Engineer with AWS and Redis experience")
    assert scan_report["score"] > 60.0
    assert "Python" in scan_report["skills"]["skills"]
    assert len(scan_report["evidence"]) > 0
    print(f"✓ Scan Report ATS Score: {scan_report['score']}/100 with {len(scan_report['evidence'])} citations.")


def test_module_b_interview():
    print("\n--- 3. Testing Module B: Interview Engine & DSA Sandbox ---")
    orchestrator = InterviewOrchestrator()
    session_data = orchestrator.start_session(user_id="test_cand_01", role="Backend Engineer", stage="technical")
    assert session_data["session_id"]
    assert session_data["current_question"]
    print(f"✓ Interview session started. First question: {session_data['current_question'][:60]}...")

    answer_out = orchestrator.process_candidate_answer(
        session_id=session_data["session_id"],
        answer="I use connection pools like psycopg2 pool and cache frequent read queries in Redis with a 60-second TTL.",
        user_id="test_cand_01"
    )
    assert answer_out["session_id"]
    print("✓ Answer evaluated with follow-up generated.")

    # Sandbox test
    code = """
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        diff = target - n
        if diff in seen:
            return [seen[diff], i]
        seen[n] = i
    return []
"""
    test_cases = [
        {"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]},
        {"input": {"nums": [3, 2, 4], "target": 6}, "expected": [1, 2]}
    ]
    sandbox_out = CodeSandbox.execute_code(code, test_cases)
    assert sandbox_out["all_passed"] is True
    print(f"✓ DSA Sandbox executed: All passed in {sandbox_out['total_runtime_ms']}ms.")


def test_module_c_recruiter():
    print("\n--- 4. Testing Module C: Recruiter Screening & Ranking ---")
    orchestrator = ScreeningOrchestrator()
    candidates = [
        {"id": "c1", "name": "Alice", "raw_text": "Senior Python Developer with AWS, Docker, Kubernetes, microservices experience.", "skills": ["Python", "AWS", "Docker", "Kubernetes"]},
        {"id": "c2", "name": "Bob", "raw_text": "Junior Frontend developer with HTML, CSS, JavaScript, and some React.", "skills": ["HTML", "CSS", "JavaScript", "React"]},
    ]
    screen_out = orchestrator.screen_batch(
        title="Senior Backend Engineer",
        description="Must have strong Python, Docker, Kubernetes, AWS, and distributed systems experience.",
        candidates=candidates
    )
    ranked = screen_out["ranking"]["ranked_candidates"]
    assert len(ranked) == 2
    assert ranked[0]["id"] == "c1", "Alice should rank higher than Bob for Backend role"
    print(f"✓ Recruiter ranking verified. Top candidate: {ranked[0]['name']} (Score: {ranked[0]['composite_score']})")


def test_module_d_scoring_and_progression():
    print("\n--- 5. Testing Module D: Readiness & Simulation Cutoffs ---")
    p1 = can_progress_to_next_round("resume_screening", 75)
    assert p1["passed"] is True
    assert p1["next_round"] == "aptitude"

    p2 = can_progress_to_next_round("resume_screening", 55)
    assert p2["passed"] is False

    readiness = calculate_overall_readiness({
        "resume_screening": 85,
        "aptitude": 80,
        "dsa": 90,
        "technical": 75,
        "project_defense": 80,
        "hr": 85
    })
    assert readiness["readiness_score"] >= 80
    print(f"✓ Progression and Readiness verified (Score: {readiness['readiness_score']}/100)")


if __name__ == "__main__":
    test_rag_collections()
    test_module_a_resume_intelligence()
    test_module_b_interview()
    test_module_c_recruiter()
    test_module_d_scoring_and_progression()
    print("\n==================================================")
    print("🎉 ALL AGENTIC & RAG VERIFICATION TESTS PASSED!")
    print("==================================================")
