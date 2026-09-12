"""
HireMind AI — Resume Intelligence Orchestrator (Module A)
Owns session/request state, orchestrates specialist agents, and compiles unified CandidateProfile.
"""
import uuid
import time
from typing import Dict, Any, Optional

from agents.module_a.parsing_agent import ParsingAgent
from agents.module_a.skill_extraction_agent import SkillExtractionAgent
from agents.module_a.ats_scoring_agent import ATSScoringAgent
from agents.module_a.jd_match_agent import JDMatchAgent
from agents.module_a.improvement_agent import ImprovementAgent
from services.supabase_client import supabase_service


class ResumeOrchestrator:
    def __init__(self):
        self.orchestrator_name = "module_a_orchestrator"
        self.parsing_agent = ParsingAgent()
        self.skill_extraction_agent = SkillExtractionAgent()
        self.ats_scoring_agent = ATSScoringAgent()
        self.jd_match_agent = JDMatchAgent()
        self.improvement_agent = ImprovementAgent()

    def analyze_resume_pipeline(
        self,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        raw_text: Optional[str] = None,
        parser_metadata: Optional[dict] = None,
        job_description: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the full agentic analysis pipeline across all specialist agents.
        """
        session_id = session_id or str(uuid.uuid4())
        audit_entity_id = f"resume-{session_id}"

        # Step 1: Parsing Agent (if file bytes provided)
        if file_bytes and filename:
            parse_out = self.parsing_agent.parse_document(file_bytes, filename, entity_id=audit_entity_id)
            parser_metadata = parse_out["result"]
            raw_text = parser_metadata.get("raw_text", "")
        else:
            parser_metadata = parser_metadata or {"page_count": 1, "is_multi_column": False, "has_tables": False}
            raw_text = raw_text or ""

        if not raw_text or not raw_text.strip():
            raise ValueError("No readable text could be extracted from the uploaded document.")

        # Step 2: Skill Extraction Agent (grounded in kb_skills_taxonomy)
        extract_out = self.skill_extraction_agent.extract_profile_and_skills(raw_text, entity_id=audit_entity_id)
        extracted_profile = extract_out["result"]

        # Step 3: JD Match Agent (optional, grounded in kb_skills_taxonomy & kb_jd_corpus)
        jd_match_out = None
        jd_match_result = None
        if job_description and job_description.strip():
            jd_match_out = self.jd_match_agent.match_job_description(
                resume_profile=extracted_profile,
                raw_resume_text=raw_text,
                job_description=job_description,
                entity_id=audit_entity_id
            )
            jd_match_result = jd_match_out["result"]

        # Step 4: ATS Scoring Agent (105-point rubric normalized to 0-100)
        scoring_out = self.ats_scoring_agent.evaluate_resume(
            profile_data=extracted_profile,
            parser_metadata=parser_metadata,
            raw_text=raw_text,
            jd_match_data=jd_match_result,
            entity_id=audit_entity_id
        )
        ats_scores = scoring_out["result"]

        # Step 5: Improvement Agent (grounded in kb_resume_best_practices)
        improvement_out = self.improvement_agent.generate_top_improvements(
            profile_data=extracted_profile,
            ats_scores=ats_scores,
            entity_id=audit_entity_id
        )
        top_improvements = improvement_out["result"]

        # Assemble unified candidate profile response
        version_id = str(int(time.time()))
        unified_profile = {
            "version_id": version_id,
            "session_id": session_id,
            "personal_info": extracted_profile.get("personal_info", {}),
            "education": extracted_profile.get("education", []),
            "experience": extracted_profile.get("experience", []),
            "projects": extracted_profile.get("projects", []),
            "certifications": extracted_profile.get("certifications", []),
            "skill_profile": extracted_profile.get("skill_profile", {}),
            "ats_scores": ats_scores,
            "parser_metadata": parser_metadata,
            "ai_summary": extracted_profile.get("ai_summary", ""),
            "strengths": extracted_profile.get("strengths", []),
            "weaknesses": extracted_profile.get("weaknesses", []),
            "top_improvements": top_improvements,
            "job_match": jd_match_result,
            "agent_audit": {
                "parsing_agent": parse_out["evidence"] if "parse_out" in locals() else {},
                "skill_extraction_agent": extract_out["evidence"],
                "ats_scoring_agent": scoring_out["evidence"],
                "jd_match_agent": jd_match_out["evidence"] if jd_match_out else None,
                "improvement_agent": improvement_out["evidence"]
            }
        }

        # Persist to database / storage
        resume_id = supabase_service.insert_resume(
            session_id=session_id,
            file_path=filename or "raw_text_input",
            user_id=user_id,
            file_name=filename
        )
        supabase_service.update_parsed_resume(
            resume_id=resume_id,
            parsed_json=unified_profile,
            ats_scores=ats_scores
        )
        unified_profile["resume_id"] = resume_id

        return unified_profile

    def improve_bullet(self, bullet_text: str, role_context: Optional[str] = None) -> Dict[str, Any]:
        """Direct single-bullet improvement endpoint."""
        return self.improvement_agent.improve_single_bullet(
            bullet_text=bullet_text,
            role_context=role_context
        )


resume_orchestrator = ResumeOrchestrator()
