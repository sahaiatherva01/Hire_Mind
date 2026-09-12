"""
HireMind AI — Automated Verification Suite for Agentic Architecture & pgvector RAG
"""
import sys
import os
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BASE_DIR))

from services.rag_service import retrieve, embed_text
from services.scoring import calculate_ats_category_scores, score_aptitude_round, score_dsa_round, calculate_readiness_score
from services.round_engine import round_engine
from agents.module_a.resume_orchestrator import resume_orchestrator
from agents.module_b.interview_orchestrator import interview_orchestrator
from agents.module_c.screening_orchestrator import screening_orchestrator


def test_rag_collections():
    print("\n--- 1. Testing RAG Retrieval Across All 5 Seed Collections ---")
    
    # Collection 1: kb_interview_questions
    q_matches = retrieve(query="Java garbage collection memory leak", collection="kb_interview_questions", top_k=2)
    assert len(q_matches) > 0, "kb_interview_questions retrieval failed"
    print(f"✓ kb_interview_questions retrieved {len(q_matches)} items. Top: {q_matches[0]['item'].get('question_text')[:60]}... (sim: {q_matches[0]['similarity']})")

    # Collection 2: kb_skills_taxonomy
    s_matches = retrieve(query="Spring Boot", collection="kb_skills_taxonomy", top_k=1)
    assert len(s_matches) > 0, "kb_skills_taxonomy retrieval failed"
    print(f"✓ kb_skills_taxonomy retrieved: {s_matches[0]['item'].get('canonical_skill')} [Category: {s_matches[0]['item'].get('category')}] (sim: {s_matches[0]['similarity']})")

    # Collection 3: kb_jd_corpus
    jd_matches = retrieve(query="Senior Backend Engineer Python FastAPI", collection="kb_jd_corpus", top_k=1)
    assert len(jd_matches) > 0, "kb_jd_corpus retrieval failed"
    print(f"✓ kb_jd_corpus retrieved: {jd_matches[0]['item'].get('role_title')} (sim: {jd_matches[0]['similarity']})")

    # Collection 4: kb_resume_best_practices
    rbp_matches = retrieve(query="Google XYZ formula quantify metrics bullet", collection="kb_resume_best_practices", top_k=1)
    assert len(rbp_matches) > 0, "kb_resume_best_practices retrieval failed"
    print(f"✓ kb_resume_best_practices retrieved: {rbp_matches[0]['item'].get('category')} (sim: {rbp_matches[0]['similarity']})")

    # Collection 5: kb_company_interview_style
    comp_matches = retrieve(query="Amazon Leadership Principles ownership", collection="kb_company_interview_style", top_k=1)
    assert len(comp_matches) > 0, "kb_company_interview_style retrieval failed"
    print(f"✓ kb_company_interview_style retrieved: {comp_matches[0]['item'].get('company_name')} (sim: {comp_matches[0]['similarity']})")


def test_module_a_resume_intelligence():
    print("\n--- 2. Testing Module A (Resume Intelligence Pipeline) ---")
    raw_resume = """
    Alex Mercer
    Email: alex@example.com | Phone: +1-555-0199 | San Francisco, CA
    
    Education:
    B.S. Computer Science, UC Berkeley (GPA: 3.8/4.0), 2022
    
    Experience:
    Software Engineer at TechCorp Solutions (2022 - Present)
    - Architected and deployed microservices using Python and Flask.
    - Optimized PostgreSQL query execution plans, reducing p99 API response latency by 35%.
    - Built responsive frontend dashboards using React and TypeScript.
    
    Projects:
    ResumeLens AI: Intelligent resume evaluation engine using Python, PyTorch, and Docker.
    
    Skills:
    Python, Flask, PostgreSQL, Docker, React, TypeScript, Git, REST APIs
    """
    
    result = resume_orchestrator.analyze_resume_pipeline(
        raw_text=raw_resume,
        job_description="Seeking a Backend Engineer with Python, PostgreSQL, and REST API experience."
    )
    
    assert "ats_scores" in result, "ATS scores missing"
    assert "skill_profile" in result, "Skill profile missing"
    assert "agent_audit" in result, "Agent audit evidence missing"
    
    scores = result["ats_scores"]
    print(f"✓ Overall ATS+ Score: {scores.get('overall_score')}/100")
    print(f"✓ Grounded Canonical Skills: {result['skill_profile'].get('normalized_skills')}")
    print(f"✓ Top Improvements: {len(result.get('top_improvements', []))} items generated")
    
    # Test single bullet rewrite
    rewrite = resume_orchestrator.improve_bullet("Worked on database queries to make them faster.", "Backend Engineer")
    print(f"✓ Single Bullet Rewrite (XYZ format): {rewrite['result'].get('improved')}")


def test_module_b_interview_simulator():
    print("\n--- 3. Testing Module B (Interview Simulator Pipeline) ---")
    
    # 1. Generate questions
    mock_resume = {
        "personal_info": {"name": "Alex Mercer"},
        "skill_profile": {"normalized_skills": ["Python", "Flask", "PostgreSQL", "Docker", "React"]},
        "projects": [{"name": "ResumeLens AI", "technologies": ["Python", "PyTorch", "Docker"]}]
    }
    
    plan = interview_orchestrator.planning_agent.generate_question_bank(
        parsed_resume=mock_resume,
        target_role="Senior Backend Engineer",
        company_track="amazon"
    )
    questions = plan["result"].get("questions", [])
    assert len(questions) > 0, "Question generation failed"
    print(f"✓ Generated {len(questions)} grounded interview questions. First: {questions[0]['question']}")
    
    # 2. Test turn evaluation with TechnicalAgent
    turn_eval = interview_orchestrator.technical_agent.evaluate_turn(
        question_text="How do you handle database connection pooling and transaction rollbacks under high concurrency in PostgreSQL?",
        answer_text="We configured PgBouncer for transaction-level connection pooling and used context managers with explicit exception catching to issue rollbacks on query failures.",
        resume_context="Python, PostgreSQL, Flask"
    )
    print(f"✓ TechnicalAgent Evaluation Decision: {turn_eval['result'].get('decision')} | Score: {turn_eval['result'].get('score')}/10")
    assert "score" in turn_eval["result"]


def test_module_c_recruiter_batch():
    print("\n--- 4. Testing Module C (Recruiter Batch Screening & Assessment) ---")
    
    # Create Job
    job_res = screening_orchestrator.create_job(
        company_id="comp-techcorp-101",
        title="Senior Python Backend Engineer",
        department="Core Infrastructure",
        jd_text="Requirements: 4+ years Python, PostgreSQL, Docker, Microservices, and REST APIs. Preferred: AWS, Kubernetes, Redis."
    )
    job_id = job_res["job_id"]
    print(f"✓ Created Job {job_id} with {len(job_res['job']['parsed_requirements']['required_skills'])} extracted skills")
    
    # Test Assessment generation
    test_res = screening_orchestrator.generate_role_assessment(
        company_id="comp-techcorp-101",
        job_id=job_id,
        duration_minutes=30
    )
    test = test_res["assessment"]
    print(f"✓ Generated Assessment: '{test.get('title')}' with {len(test.get('questions', []))} questions")
    assert len(test.get("questions", [])) > 0


def test_module_d_progression_readiness():
    print("\n--- 5. Testing Module D (Progression & Readiness Scoring) ---")
    
    user_id = "u-dev-001"
    
    # Test cutoff progression
    round_engine.record_round_attempt(user_id=user_id, round_name="resume_screening", score=85, mode="simulation")
    round_engine.record_round_attempt(user_id=user_id, round_name="aptitude", score=78, mode="simulation")
    
    progress = round_engine.get_user_progress(user_id=user_id)
    rounds = {r["round_name"]: r for r in progress["rounds"]}
    
    assert rounds["resume_screening"]["status"] == "cleared"
    assert rounds["aptitude"]["status"] == "cleared"
    assert rounds["dsa"]["status"] == "unlocked"  # DSA unlocked because aptitude cleared!
    assert rounds["technical"]["status"] == "locked"  # Technical locked until DSA cleared
    
    print("✓ Cutoff progression verified: Resume (cleared) → Aptitude (cleared) → DSA (unlocked) → Technical (locked)")
    
    # Calculate readiness score
    scores_map = {"resume_screening": 85, "aptitude": 78, "dsa": 80, "technical": 82}
    readiness = calculate_readiness_score(scores_map)
    print(f"✓ Aggregated Readiness Score: {readiness['overall_readiness']}/100 | Tier: {readiness['tier']}")
    assert readiness["overall_readiness"] > 0


if __name__ == "__main__":
    print("=================================================================")
    print("  HireMind AI — Agentic + RAG Upgrade Full Verification Suite   ")
    print("=================================================================")
    
    test_rag_collections()
    test_module_a_resume_intelligence()
    test_module_b_interview_simulator()
    test_module_c_recruiter_batch()
    test_module_d_progression_readiness()
    
    print("\n=================================================================")
    print("  ALL VERIFICATION TESTS PASSED! 🎉                             ")
    print("=================================================================\n")
