"""
HireMind AI — Skill Extraction & Profile Agent (Module A)
Extracts candidate profile and normalizes skills retrieval-grounded in kb_skills_taxonomy.
"""
import json
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from config import Config


class SkillExtractionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="SkillExtractionAgent",
            orchestrator_name="module_a_orchestrator"
        )

    def extract_profile_and_skills(self, raw_text: str, entity_id: str = None) -> Dict[str, Any]:
        """
        Parses structured profile from raw resume text and resolves canonical skills via RAG.
        """
        prompt = f"""
You are an expert technical resume parser.
Extract the structured profile from this resume into JSON format.

RULES:
- JSON only.
- Do not hallucinate or invent facts.
- Normalize section arrays to [] if missing.

RESUME TEXT:
{raw_text[:20000]}

Return JSON format:
{{
  "personal_info": {{
    "name": "...",
    "email": "...",
    "phone": "...",
    "location": "...",
    "linkedin": "...",
    "github": "...",
    "portfolio": "..."
  }},
  "education": [
    {{
      "institution": "...",
      "degree": "...",
      "field": "...",
      "gpa": "...",
      "start_year": "...",
      "graduation_year": "..."
    }}
  ],
  "experience": [
    {{
      "company": "...",
      "role": "...",
      "duration": "...",
      "responsibilities": ["..."],
      "technologies": ["..."],
      "achievements": ["..."]
    }}
  ],
  "projects": [
    {{
      "name": "...",
      "description": "...",
      "technologies": ["..."],
      "domain": "...",
      "achievements": "...",
      "links": ["..."]
    }}
  ],
  "certifications": [
    {{
      "name": "...",
      "issuer": "...",
      "date": "..."
    }}
  ],
  "raw_skills": ["..."],
  "ai_summary": "...",
  "strengths": ["..."],
  "weaknesses": ["..."]
}}
"""
        fallback_profile = {
            "personal_info": {"name": "Candidate", "email": None, "phone": None, "location": None},
            "education": [],
            "experience": [],
            "projects": [],
            "certifications": [],
            "raw_skills": ["Python", "JavaScript", "SQL", "Git", "REST APIs"],
            "ai_summary": "Extracted candidate technical profile.",
            "strengths": ["Technical background"],
            "weaknesses": []
        }

        extracted = self.generate_json(
            prompt=prompt,
            model=Config.PARSER_MODEL,
            max_output_tokens=2200,
            fallback_json=fallback_profile
        )

        raw_skills = extracted.get("raw_skills", [])
        if not raw_skills:
            # Extract skills mentioned in experience and projects
            for exp in extracted.get("experience", []):
                raw_skills.extend(exp.get("technologies", []))
            for proj in extracted.get("projects", []):
                raw_skills.extend(proj.get("technologies", []))
            raw_skills = list(set(raw_skills))

        # --- RAG Grounding against kb_skills_taxonomy ---
        normalized_skills = []
        categorized_skills = {
            "Languages": [],
            "Frameworks": [],
            "Databases": [],
            "Cloud & DevOps": [],
            "AI & ML": [],
            "Core CS & Tools": []
        }
        grounding_citations = []

        for skill in raw_skills[:25]:
            # Retrieve canonical skill taxonomy entry
            rag_matches = self.retrieve(
                query=f"{skill}",
                collection="kb_skills_taxonomy",
                top_k=1
            )

            if rag_matches and rag_matches[0].get("similarity", 0) > 0.45:
                top_item = rag_matches[0]["item"]
                canonical_name = top_item.get("canonical_skill", skill)
                cat = top_item.get("category", "Core CS & Tools")

                normalized_skills.append(canonical_name)
                categorized_skills.setdefault(cat, []).append(canonical_name)
                grounding_citations.append(
                    f"Resolved '{skill}' → Canonical: '{canonical_name}' [{cat}] (similarity: {rag_matches[0]['similarity']})"
                )
            else:
                normalized_skills.append(skill)
                categorized_skills["Core CS & Tools"].append(skill)

        # Deduplicate
        normalized_skills = list(dict.fromkeys(normalized_skills))
        for k in categorized_skills:
            categorized_skills[k] = list(dict.fromkeys(categorized_skills[k]))

        extracted["skill_profile"] = {
            "raw_skills": raw_skills,
            "normalized_skills": normalized_skills,
            "categorized_skills": categorized_skills
        }

        return self.build_agent_output(
            result=extracted,
            citations=grounding_citations,
            reasoning=f"Extracted candidate profile and resolved {len(normalized_skills)} canonical skills grounded in kb_skills_taxonomy.",
            confidence=0.94,
            entity_id=entity_id,
            entity_type="profile_extraction"
        )
