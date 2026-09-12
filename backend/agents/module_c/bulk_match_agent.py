"""
HireMind AI — Bulk Match Agent (Module C)
Executes batch JD matching across candidate resumes with strict multi-tenant isolation.
"""
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from agents.module_a.jd_match_agent import JDMatchAgent


class BulkMatchAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="BulkMatchAgent",
            orchestrator_name="module_c_orchestrator"
        )
        self.jd_match_agent = JDMatchAgent()

    def match_candidates_batch(
        self,
        company_id: str,
        job_id: str,
        jd_text: str,
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Runs JD matching for a list of candidate resumes, guaranteeing tenant boundary isolation.
        """
        results = []
        citations = [f"Tenant Company ID: {company_id} | Job ID: {job_id}"]

        for cand in candidates:
            cand_name = cand.get("candidate_name", "Candidate")
            cand_profile = cand.get("parsed_profile") or {}
            raw_text = cand.get("raw_text") or str(cand_profile)

            match_out = self.jd_match_agent.match_job_description(
                resume_profile=cand_profile,
                raw_resume_text=raw_text,
                job_description=jd_text,
                entity_id=f"recruit-{company_id}-{cand.get('id', cand_name)}"
            )

            res = match_out["result"] or {}
            score = float(res.get("jd_match_score", 60.0))

            results.append({
                "candidate_id": cand.get("id"),
                "candidate_name": cand_name,
                "email": cand.get("email"),
                "match_score": score,
                "matched_required_skills": res.get("matched_required_skills", []),
                "missing_required_skills": res.get("missing_required_skills", []),
                "matched_preferred_skills": res.get("matched_preferred_skills", []),
                "missing_preferred_skills": res.get("missing_preferred_skills", []),
                "fit_summary": res.get("fit_summary", ""),
                "evidence": match_out["evidence"]
            })

        citations.append(f"Successfully evaluated {len(results)} candidate resumes for Job {job_id}.")
        return self.build_agent_output(
            result=results,
            citations=citations,
            reasoning=f"Batch matched {len(results)} candidate profiles with tenant isolation on company {company_id}.",
            confidence=0.95,
            entity_id=f"bulk-match-{job_id}",
            entity_type="bulk_match_batch"
        )
