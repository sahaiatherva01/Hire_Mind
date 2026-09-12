"""
HireMind AI — Screening Orchestrator (Module C)
Owns recruiter job management, batch candidate screening pipeline, and assessment generation.
"""
import uuid
import time
from typing import Dict, Any, List, Optional

from agents.module_c.jd_parsing_agent import JDParsingAgent
from agents.module_c.bulk_match_agent import BulkMatchAgent
from agents.module_c.ranking_agent import RankingAgent
from agents.module_c.assessment_generation_agent import AssessmentGenerationAgent
from agents.module_a.parsing_agent import ParsingAgent
from agents.module_a.skill_extraction_agent import SkillExtractionAgent
from services.supabase_client import supabase_service


class ScreeningOrchestrator:
    def __init__(self):
        self.orchestrator_name = "module_c_orchestrator"
        self.jd_parsing_agent = JDParsingAgent()
        self.bulk_match_agent = BulkMatchAgent()
        self.ranking_agent = RankingAgent()
        self.assessment_agent = AssessmentGenerationAgent()
        self.doc_parsing_agent = ParsingAgent()
        self.skill_extraction_agent = SkillExtractionAgent()

    def create_job(
        self,
        company_id: str,
        title: str,
        department: str,
        jd_text: str
    ) -> Dict[str, Any]:
        """
        Creates a new job posting, parses its requirements via JDParsingAgent, and stores it under company_id.
        """
        job_id = f"job-{uuid.uuid4()}"

        # Parse requirements
        parsed_out = self.jd_parsing_agent.parse_job_description(
            jd_text=jd_text,
            title=title,
            entity_id=job_id
        )
        parsed_reqs = parsed_out["result"]

        job_rec = {
            "id": job_id,
            "company_id": company_id,
            "title": title,
            "department": department,
            "jd_text": jd_text,
            "parsed_requirements": parsed_reqs,
            "status": "active",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        # Store in DB
        data = supabase_service._read_local_db()
        data.setdefault("recruit_jobs", []).append(job_rec)
        supabase_service._write_local_db(data)

        if supabase_service.supabase:
            try:
                supabase_service.supabase.table("recruit_jobs").insert(job_rec).execute()
            except Exception as e:
                print(f"[ScreeningOrchestrator] Remote job insert error: {e}")

        return {
            "job_id": job_id,
            "job": job_rec,
            "evidence": parsed_out["evidence"]
        }

    def list_company_jobs(self, company_id: str) -> List[Dict[str, Any]]:
        """Lists all active jobs for the given company tenant."""
        data = supabase_service._read_local_db()
        jobs = [j for j in data.get("recruit_jobs", []) if j.get("company_id") == company_id]
        return jobs

    def process_batch_resumes(
        self,
        company_id: str,
        job_id: str,
        files_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Processes a batch of candidate resumes for a specific job:
        1. Ingests & extracts candidate profiles.
        2. Executes bulk JD matching.
        3. Ranks candidates into Strong / Review / Weak tiers.
        """
        # 1. Fetch job requirements
        data = supabase_service._read_local_db()
        target_job = None
        for j in data.get("recruit_jobs", []):
            if j.get("id") == job_id and j.get("company_id") == company_id:
                target_job = j
                break

        if not target_job:
            raise ValueError(f"Job {job_id} not found for company {company_id}.")

        jd_text = target_job.get("jd_text", "")

        # 2. Parse candidates
        parsed_candidates = []
        for item in files_data:
            filename = item.get("filename", "resume.pdf")
            file_bytes = item.get("file_bytes")
            cand_name = item.get("candidate_name") or filename.replace(".pdf", "").replace("_", " ").title()
            email = item.get("email") or f"{cand_name.lower().replace(' ', '.')}@example.com"

            # Parse doc
            parse_out = self.doc_parsing_agent.parse_document(file_bytes, filename)
            raw_text = parse_out["result"].get("raw_text", "")

            # Extract profile & skills
            extract_out = self.skill_extraction_agent.extract_profile_and_skills(raw_text)
            profile = extract_out["result"]

            # Save resume record
            resume_id = supabase_service.insert_resume(
                session_id=f"recruit-{uuid.uuid4()}",
                file_path=filename,
                file_name=filename
            )

            cand_rec = {
                "id": f"cand-{uuid.uuid4()}",
                "resume_id": resume_id,
                "candidate_name": profile.get("personal_info", {}).get("name") or cand_name,
                "email": profile.get("personal_info", {}).get("email") or email,
                "parsed_profile": profile,
                "raw_text": raw_text
            }
            parsed_candidates.append(cand_rec)

        # 3. Bulk Match Agent
        match_out = self.bulk_match_agent.match_candidates_batch(
            company_id=company_id,
            job_id=job_id,
            jd_text=jd_text,
            candidates=parsed_candidates
        )
        match_results = match_out["result"]

        # 4. Ranking Agent
        rank_out = self.ranking_agent.rank_candidates(
            match_results=match_results,
            company_id=company_id,
            job_id=job_id
        )
        rankings = rank_out["result"]

        # Store candidate rankings in DB
        for cand in rankings:
            rec = {
                "id": cand.get("candidate_id") or str(uuid.uuid4()),
                "company_id": company_id,
                "job_id": job_id,
                "candidate_name": cand.get("candidate_name"),
                "email": cand.get("email"),
                "match_score": cand.get("match_score"),
                "ranking_category": cand.get("ranking_category"),
                "evidence_summary": cand
            }
            data.setdefault("recruit_candidates", []).append(rec)

        supabase_service._write_local_db(data)

        return {
            "job_id": job_id,
            "company_id": company_id,
            "total_candidates_processed": len(rankings),
            "rankings": rankings,
            "agent_audit": {
                "bulk_match": match_out["evidence"],
                "ranking": rank_out["evidence"]
            }
        }

    def list_job_candidates(self, company_id: str, job_id: str) -> List[Dict[str, Any]]:
        """Returns the ranked candidate list for a given job posting."""
        data = supabase_service._read_local_db()
        cands = [c for c in data.get("recruit_candidates", []) if c.get("job_id") == job_id and c.get("company_id") == company_id]
        cands.sort(key=lambda x: -float(x.get("match_score", 0)))
        return cands

    def generate_role_assessment(
        self,
        company_id: str,
        job_id: str,
        duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """Generates a custom role assessment test for the job."""
        data = supabase_service._read_local_db()
        target_job = None
        for j in data.get("recruit_jobs", []):
            if j.get("id") == job_id and j.get("company_id") == company_id:
                target_job = j
                break

        if not target_job:
            raise ValueError(f"Job {job_id} not found.")

        title = target_job.get("title", "Software Engineer")
        req_skills = target_job.get("parsed_requirements", {}).get("required_skills", ["Python", "SQL"])

        assessment_out = self.assessment_agent.generate_assessment(
            job_title=title,
            required_skills=req_skills,
            duration_minutes=duration_minutes,
            company_id=company_id,
            job_id=job_id
        )

        test_data = assessment_out["result"]
        assessment_id = f"test-{uuid.uuid4()}"
        rec = {
            "id": assessment_id,
            "company_id": company_id,
            "job_id": job_id,
            "title": test_data.get("title"),
            "questions": test_data.get("questions", []),
            "duration_minutes": duration_minutes,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        data.setdefault("recruit_assessments", []).append(rec)
        supabase_service._write_local_db(data)

        return {
            "assessment_id": assessment_id,
            "assessment": test_data,
            "evidence": assessment_out["evidence"]
        }


screening_orchestrator = ScreeningOrchestrator()
