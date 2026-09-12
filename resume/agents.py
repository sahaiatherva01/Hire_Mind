import re
from typing import Dict, Any, List, Optional

from core.evaluation import BaseAgent
from core.scoring import calculate_ats_category_scores
from core.gemini import generate_json


class SkillExtractionAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="SkillExtractionAgent", orchestrator_name="resume_orchestrator")

    def extract_skills(self, resume_text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        evidence = self.retrieve(query=resume_text[:500], collection="kb_skills_taxonomy", top_k=5)

        # Extract explicit skill matches against known taxonomy
        found_skills = []
        text_lower = resume_text.lower()
        for doc in evidence:
            raw = doc.get("raw_data", {})
            canonical = raw.get("canonical_skill") or raw.get("canonical_name")
            if not canonical:
                continue
            synonyms = raw.get("synonyms", [])
            if canonical.lower() in text_lower:
                if canonical not in found_skills:
                    found_skills.append(canonical)
            else:
                for syn in synonyms:
                    if syn.lower() in text_lower:
                        if canonical not in found_skills:
                            found_skills.append(canonical)
                        break

        # Common tech skills regex detection
        tech_patterns = [
            "Python", "JavaScript", "TypeScript", "React", "Node.js", "SQL", "PostgreSQL",
            "Docker", "Kubernetes", "AWS", "GCP", "Git", "Flask", "Django", "FastAPI",
            "C++", "Java", "Go", "Rust", "Redis", "GraphQL", "MongoDB", "Linux"
        ]
        for skill in tech_patterns:
            if re.search(rf"\b{re.escape(skill)}\b", resume_text, re.IGNORECASE):
                if skill not in found_skills:
                    found_skills.append(skill)

        categorized = {
            "languages": [s for s in found_skills if s in ["Python", "JavaScript", "TypeScript", "C++", "Java", "Go", "Rust", "SQL"]],
            "frameworks": [s for s in found_skills if s in ["React", "Node.js", "Flask", "Django", "FastAPI"]],
            "infrastructure": [s for s in found_skills if s in ["Docker", "Kubernetes", "AWS", "GCP", "Linux", "Redis", "PostgreSQL", "MongoDB", "Git"]],
        }

        result = {
            "skills": found_skills,
            "categorized": categorized,
            "skill_count": len(found_skills)
        }

        return self.format_output(
            result=result,
            evidence=evidence,
            confidence=0.92,
            input_summary="Extracted technical skill profile",
            user_id=user_id
        )


class ATSScoringAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="ATSScoringAgent", orchestrator_name="resume_orchestrator")

    def score_resume(self, parsed_data: Dict[str, Any], skill_data: Dict[str, Any], jd_match: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        evidence = self.retrieve(query="ATS layout action verbs quantifiable impact", collection="kb_resume_best_practices", top_k=3)

        profile_for_scoring = {
            "experience": [{"title": "Work Experience"}] if parsed_data.get("sections_detected", {}).get("experience") else [],
            "education": [{"degree": "Education"}] if parsed_data.get("sections_detected", {}).get("education") else [],
            "projects": [{"name": "Project"}] if parsed_data.get("sections_detected", {}).get("projects") else [],
            "contact": parsed_data.get("contact", {}),
            "skill_profile": {
                "normalized_skills": skill_data.get("skills", []),
                "categorized_skills": skill_data.get("categorized", {})
            }
        }

        parser_metadata = {
            "page_count": parsed_data.get("page_count", 1),
            "is_multi_column": parsed_data.get("is_multi_column", False),
            "has_tables": parsed_data.get("has_tables", False)
        }

        scoring_result = calculate_ats_category_scores(
            profile_data=profile_for_scoring,
            parser_metadata=parser_metadata,
            raw_text=parsed_data.get("raw_text", ""),
            jd_match_data=jd_match
        )

        return self.format_output(
            result=scoring_result,
            evidence=evidence,
            confidence=0.95,
            input_summary="Computed ATS+ 105-point rubric score",
            user_id=user_id
        )


class JDMatchAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="JDMatchAgent", orchestrator_name="resume_orchestrator")

    def match_job_description(self, resume_skills: List[str], jd_text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        evidence = self.retrieve(query=jd_text[:400], collection="kb_jd_corpus", top_k=2)

        jd_lower = jd_text.lower()
        matched_skills = [s for s in resume_skills if s.lower() in jd_lower]

        # Scan for missing skills mentioned in JD
        common_requirements = [
            "Python", "JavaScript", "TypeScript", "React", "Node.js", "Docker", "Kubernetes",
            "AWS", "PostgreSQL", "Redis", "GraphQL", "CI/CD", "System Design", "Microservices"
        ]
        missing_skills = []
        for req in common_requirements:
            if req.lower() in jd_lower and req not in matched_skills:
                missing_skills.append(req)

        total_reqs = len(matched_skills) + len(missing_skills)
        match_score = round((len(matched_skills) / max(1, total_reqs)) * 100.0, 1)

        result = {
            "jd_match_score": match_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "total_jd_skills_detected": total_reqs
        }

        return self.format_output(
            result=result,
            evidence=evidence,
            confidence=0.88,
            input_summary="JD Keyword and Semantic Gap Analysis",
            user_id=user_id
        )


class ImprovementAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="ImprovementAgent", orchestrator_name="resume_orchestrator")

    def improve_bullet(self, bullet: str, role: str = "Software Engineer", user_id: Optional[str] = None) -> Dict[str, Any]:
        evidence = self.retrieve(query=bullet, collection="kb_resume_best_practices", top_k=2)
        guidance = "\n".join([f"- {e.get('content')}" for e in evidence])

        prompt = f"""You are an elite technical resume coach applying the Google XYZ formula:
'Accomplished [X] as measured by [Y], by doing [Z]'.

Retrieved best practice rules:
{guidance}

Original bullet:
"{bullet}"

Rewrite this bullet point to be high-impact, starting with a strong action verb and including realistic metric placeholders if unquantified. Return valid JSON only with keys:
"improved_bullet": string,
"changes_made": list of strings,
"formula_breakdown": {{"action": string, "impact": string, "method": string}}
"""
        fallback = {
            "improved_bullet": f"Engineered scalable solution for {bullet.lower().rstrip('.')}, optimizing execution efficiency by 30% through modular architecture.",
            "changes_made": ["Added active action verb", "Framed with Google XYZ outcome structure", "Included quantifiable efficiency metric"],
            "formula_breakdown": {"action": "Engineered", "impact": "Optimized execution efficiency by 30%", "method": "Modular architecture"}
        }

        result = self.generate_json_response(prompt, fallback=fallback)
        return self.format_output(
            result=result,
            evidence=evidence,
            confidence=0.90,
            input_summary=f"Bullet rewrite: {bullet[:50]}",
            user_id=user_id
        )


class ResumeOrchestrator:
    def __init__(self):
        self.skill_agent = SkillExtractionAgent()
        self.ats_agent = ATSScoringAgent()
        self.jd_agent = JDMatchAgent()
        self.improvement_agent = ImprovementAgent()

    def run_scan(self, parsed_data: Dict[str, Any], jd_text: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        # 1. Skill Extraction
        skill_output = self.skill_agent.extract_skills(parsed_data.get("raw_text", ""), user_id=user_id)
        skills = skill_output["result"]["skills"]

        # 2. Optional JD Match
        jd_output = None
        if jd_text and jd_text.strip():
            jd_output = self.jd_agent.match_job_description(skills, jd_text, user_id=user_id)

        # 3. ATS Rubric Scoring
        ats_output = self.ats_agent.score_resume(
            parsed_data=parsed_data,
            skill_data=skill_output["result"],
            jd_match=jd_output["result"] if jd_output else None,
            user_id=user_id
        )

        return {
            "score": ats_output["result"]["overall_score"],
            "category_scores": ats_output["result"]["categories"],
            "raw_points": ats_output["result"]["raw_points"],
            "max_points": ats_output["result"]["max_points"],
            "skills": skill_output["result"],
            "jd_match": jd_output["result"] if jd_output else None,
            "evidence": ats_output.get("evidence", []) + (jd_output.get("evidence", []) if jd_output else []),
            "parsed_metadata": {
                "page_count": parsed_data.get("page_count", 1),
                "is_multi_column": parsed_data.get("is_multi_column", False),
                "has_tables": parsed_data.get("has_tables", False),
                "contact": parsed_data.get("contact", {}),
                "char_count": parsed_data.get("char_count", 0),
                "word_count": parsed_data.get("word_count", 0)
            }
        }
