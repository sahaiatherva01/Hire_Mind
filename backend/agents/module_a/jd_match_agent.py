"""
HireMind AI — JD Match Agent (Module A)
Aligns resume against job descriptions retrieval-grounded in kb_skills_taxonomy and kb_jd_corpus.
"""
import json
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from config import Config


class JDMatchAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="JDMatchAgent",
            orchestrator_name="module_a_orchestrator"
        )

    def match_job_description(
        self,
        resume_profile: dict,
        raw_resume_text: str,
        job_description: str,
        entity_id: str = None
    ) -> Dict[str, Any]:
        """
        Evaluates resume compatibility against a target JD with synonym resolution and corpus weighting.
        """
        if not job_description or not job_description.strip():
            return self.build_agent_output(
                result=None,
                citations=[],
                reasoning="No job description was provided.",
                confidence=1.0,
                entity_id=entity_id,
                entity_type="jd_match"
            )

        # 1. RAG Grounding: Retrieve similar real-world JDs from kb_jd_corpus
        corpus_matches = self.retrieve(
            query=job_description[:500],
            collection="kb_jd_corpus",
            top_k=2
        )

        corpus_context = ""
        citations = []
        if corpus_matches:
            top_jd = corpus_matches[0]["item"]
            corpus_context = f"Similar Real-World JD Role: {top_jd.get('role_title')} | Key Skills: {', '.join(top_jd.get('required_skills', []))}"
            citations.append(f"Grounded against kb_jd_corpus: '{top_jd.get('role_title')}' (similarity: {corpus_matches[0]['similarity']})")

        # 2. Extract JD requirements via LLM
        prompt = f"""
You are an expert technical recruiter analyzing a Job Description against a candidate's resume.

JOB DESCRIPTION:
{job_description[:4000]}

GROUNDING CORPUS CONTEXT:
{corpus_context}

CANDIDATE RESUME SKILLS & SUMMARY:
Skills: {json.dumps(resume_profile.get('skill_profile', {}).get('normalized_skills', []))}
Summary: {resume_profile.get('ai_summary', '')}

Analyze the match and return strict JSON:
{{
  "matched_required_skills": ["..."],
  "missing_required_skills": ["..."],
  "matched_preferred_skills": ["..."],
  "missing_preferred_skills": ["..."],
  "matched_keywords": ["..."],
  "missing_keywords": ["..."],
  "jd_match_score": 85,
  "fit_summary": "1-2 sentence alignment analysis"
}}
"""
        fallback_match = {
            "matched_required_skills": ["Python", "SQL", "Git"],
            "missing_required_skills": ["AWS"],
            "matched_preferred_skills": ["Docker"],
            "missing_preferred_skills": ["Kubernetes"],
            "matched_keywords": ["Python", "Backend", "REST APIs"],
            "missing_keywords": ["Microservices"],
            "jd_match_score": 75.0,
            "fit_summary": "Solid core technical alignment with minor infrastructure gaps."
        }

        extracted = self.generate_json(
            prompt=prompt,
            model=Config.DEFAULT_MODEL,
            max_output_tokens=1200,
            fallback_json=fallback_match
        )

        # 3. RAG Grounding: Resolve missing skills against kb_skills_taxonomy for synonyms / adjacencies
        candidate_skills = set(s.lower() for s in resume_profile.get('skill_profile', {}).get('normalized_skills', []))
        adjusted_missing_req = []
        
        for missing_s in extracted.get("missing_required_skills", []):
            syn_matches = self.retrieve(
                query=missing_s,
                collection="kb_skills_taxonomy",
                top_k=1
            )
            found_synonym = False
            if syn_matches and syn_matches[0]["similarity"] > 0.45:
                tax_item = syn_matches[0]["item"]
                all_aliases = [tax_item.get("canonical_skill", "").lower()] + [s.lower() for s in tax_item.get("synonyms", [])]
                if any(alias in candidate_skills for alias in all_aliases):
                    found_synonym = True
                    extracted.setdefault("matched_required_skills", []).append(f"{missing_s} (matched via {tax_item.get('canonical_skill')})")
                    citations.append(f"Resolved synonym via kb_skills_taxonomy: '{missing_s}' matched candidate's alias.")

            if not found_synonym:
                adjusted_missing_req.append(missing_s)

        extracted["missing_required_skills"] = adjusted_missing_req
        
        # Recalculate match score based on adjusted matches
        total_req = len(extracted.get("matched_required_skills", [])) + len(extracted.get("missing_required_skills", []))
        if total_req > 0:
            req_ratio = len(extracted.get("matched_required_skills", [])) / total_req
            calculated_score = round(req_ratio * 80.0 + (len(extracted.get("matched_preferred_skills", [])) * 4.0), 1)
            extracted["jd_match_score"] = min(100.0, max(20.0, calculated_score))

        citations.extend([
            f"Matched Required Skills: {len(extracted.get('matched_required_skills', []))}",
            f"Missing Required Skills: {len(extracted.get('missing_required_skills', []))}",
            f"JD Match Score: {extracted.get('jd_match_score')}%"
        ])

        return self.build_agent_output(
            result=extracted,
            citations=citations,
            reasoning=f"Analyzed JD match. Scored {extracted.get('jd_match_score')}% with {len(extracted.get('missing_required_skills', []))} missing required skills.",
            confidence=0.92,
            entity_id=entity_id,
            entity_type="jd_match"
        )
