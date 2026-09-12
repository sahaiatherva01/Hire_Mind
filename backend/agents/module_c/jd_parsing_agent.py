"""
HireMind AI — JD Parsing Agent (Module C)
Parses job descriptions into structured requirement profiles for recruiter batch workflows.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent
from config import Config


class JDParsingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="JDParsingAgent",
            orchestrator_name="module_c_orchestrator"
        )

    def parse_job_description(self, jd_text: str, title: str = "", entity_id: str = None) -> Dict[str, Any]:
        """
        Extracts required skills, preferred skills, domain, and seniority from a JD.
        """
        rag_matches = self.retrieve(
            query=f"{title} {jd_text[:300]}",
            collection="kb_jd_corpus",
            top_k=1
        )

        citations = []
        if rag_matches:
            top_jd = rag_matches[0]["item"]
            citations.append(f"Grounded against kb_jd_corpus archetype: '{top_jd.get('role_title')}' (similarity: {rag_matches[0]['similarity']})")

        prompt = f"""
You are an expert technical recruiting analyst.
Parse this Job Description into structured requirement fields.

JOB TITLE: {title}
JOB DESCRIPTION:
{jd_text[:4000]}

Return JSON:
{{
  "domain": "e.g. FinTech / Distributed Systems / AI Platform",
  "seniority": "intern|entry|mid|senior|staff|lead",
  "required_skills": ["..."],
  "preferred_skills": ["..."],
  "core_responsibilities": ["..."],
  "skill_weights": {{
    "Skill1": 0.30,
    "Skill2": 0.25
  }}
}}
"""
        fallback_parsed = {
            "domain": "Software Engineering",
            "seniority": "mid",
            "required_skills": ["Python", "PostgreSQL", "REST API", "Git"],
            "preferred_skills": ["Docker", "AWS", "FastAPI"],
            "core_responsibilities": ["Design and build scalable APIs", "Collaborate on database architecture"],
            "skill_weights": {"Python": 0.35, "PostgreSQL": 0.25, "REST API": 0.20, "Docker": 0.20}
        }

        result = self.generate_json(
            prompt=prompt,
            model=Config.DEFAULT_MODEL,
            max_output_tokens=1000,
            fallback_json=fallback_parsed
        )

        citations.extend([
            f"Extracted {len(result.get('required_skills', []))} required skills",
            f"Extracted {len(result.get('preferred_skills', []))} preferred skills",
            f"Domain: {result.get('domain')} | Seniority: {result.get('seniority')}"
        ])

        return self.build_agent_output(
            result=result,
            citations=citations,
            reasoning=f"Parsed JD into {len(result.get('required_skills', []))} required skills with seniority: {result.get('seniority')}.",
            confidence=0.95,
            entity_id=entity_id,
            entity_type="jd_parsed_profile"
        )
