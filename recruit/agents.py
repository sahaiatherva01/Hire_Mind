import re
from typing import Dict, Any, List, Optional
import numpy as np

from core.evaluation import BaseAgent
from core.gemini import embed_text


class JDParsingAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="JDParsingAgent", orchestrator_name="recruiter_orchestrator")

    def parse_job_description(self, title: str, description: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        evidence = self.retrieve(query=f"{title} {description[:300]}", collection="kb_jd_corpus", top_k=2)

        # Detect technical skill requirements
        tech_keywords = [
            "Python", "JavaScript", "TypeScript", "React", "Node.js", "SQL", "PostgreSQL",
            "Docker", "Kubernetes", "AWS", "GCP", "FastAPI", "Go", "Rust", "Redis",
            "System Design", "Microservices", "CI/CD", "Machine Learning", "PyTorch"
        ]
        desc_lower = description.lower()
        required_skills = [k for k in tech_keywords if k.lower() in desc_lower]
        if not required_skills:
            required_skills = ["Software Engineering", "Problem Solving", "Git"]

        seniority = "mid"
        if any(w in desc_lower or w in title.lower() for w in ["senior", "sr", "lead", "principal", "staff"]):
            seniority = "senior"
        elif any(w in desc_lower or w in title.lower() for w in ["junior", "jr", "intern", "entry"]):
            seniority = "junior"

        result = {
            "title": title,
            "seniority": seniority,
            "required_skills": required_skills,
            "skill_count": len(required_skills)
        }

        return self.format_output(
            result=result,
            evidence=evidence,
            confidence=0.92,
            input_summary=f"Parsed JD: {title}",
            user_id=user_id
        )


class BulkMatchAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="BulkMatchAgent", orchestrator_name="recruiter_orchestrator")

    def score_candidate(self, candidate_resume: Dict[str, Any], jd_skills: List[str], jd_text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        evidence = self.retrieve(query=jd_text[:300], collection="kb_skills_taxonomy", top_k=3)

        cand_text = candidate_resume.get("raw_text", "")
        cand_skills = candidate_resume.get("skills", [])
        cand_lower = cand_text.lower()

        # Skill overlap
        matched_skills = []
        for s in jd_skills:
            if s in cand_skills or s.lower() in cand_lower:
                matched_skills.append(s)

        missing_skills = [s for s in jd_skills if s not in matched_skills]
        skill_score = round((len(matched_skills) / max(1, len(jd_skills))) * 100.0, 1)

        # Semantic cosine similarity
        jd_vec = np.array(embed_text(jd_text), dtype=np.float32)
        res_vec = np.array(embed_text(cand_text[:1000]), dtype=np.float32)
        norm_jd = np.linalg.norm(jd_vec)
        norm_res = np.linalg.norm(res_vec)

        if norm_jd > 0 and norm_res > 0:
            cos_sim = float(np.dot(jd_vec, res_vec) / (norm_jd * norm_res))
            semantic_score = round(max(0.0, min(100.0, cos_sim * 100.0)), 1)
        else:
            semantic_score = skill_score

        composite = round(0.60 * skill_score + 0.40 * semantic_score, 1)

        result = {
            "composite_score": composite,
            "skill_score": skill_score,
            "semantic_score": semantic_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills
        }

        return self.format_output(
            result=result,
            evidence=evidence,
            confidence=0.90,
            input_summary=f"Matched candidate {candidate_resume.get('name', 'Candidate')}",
            user_id=user_id
        )


class RankingAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="RankingAgent", orchestrator_name="recruiter_orchestrator")

    def rank_candidates(self, scored_candidates: List[Dict[str, Any]], user_id: Optional[str] = None) -> Dict[str, Any]:
        sorted_list = sorted(scored_candidates, key=lambda c: c.get("composite_score", 0), reverse=True)

        ranked = []
        for rank, c in enumerate(sorted_list, 1):
            c_copy = dict(c)
            c_copy["rank"] = rank
            c_copy["recommendation"] = "Fast Track" if c.get("composite_score", 0) >= 80 else ("Review" if c.get("composite_score", 0) >= 65 else "Hold")
            ranked.append(c_copy)

        result = {
            "ranked_candidates": ranked,
            "total_screened": len(ranked),
            "fast_track_count": len([c for c in ranked if c["recommendation"] == "Fast Track"])
        }

        return self.format_output(
            result=result,
            evidence=[],
            confidence=0.95,
            input_summary=f"Ranked {len(ranked)} candidates",
            user_id=user_id
        )


class AssessmentGenerationAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="AssessmentGenerationAgent", orchestrator_name="recruiter_orchestrator")

    def generate_assessment_for_jd(self, jd_title: str, required_skills: List[str], count: int = 3, user_id: Optional[str] = None) -> Dict[str, Any]:
        query_str = f"{jd_title} " + " ".join(required_skills[:4])
        evidence = self.retrieve(query=query_str, collection="kb_interview_questions", top_k=count)

        questions = []
        for idx, item in enumerate(evidence):
            raw = item.get("raw_data", {})
            questions.append({
                "id": raw.get("id", f"gen-{idx+1}"),
                "question": raw.get("question_text") or item.get("content"),
                "skill": raw.get("skill", required_skills[0] if required_skills else "General"),
                "difficulty": raw.get("difficulty", "medium"),
                "sample_criteria": raw.get("sample_criteria", "Evaluates deep technical reasoning")
            })

        result = {
            "job_title": jd_title,
            "screening_questions": questions
        }

        return self.format_output(
            result=result,
            evidence=evidence,
            confidence=0.92,
            input_summary=f"Generated screening assessment for {jd_title}",
            user_id=user_id
        )


class ScreeningOrchestrator:
    def __init__(self):
        self.jd_agent = JDParsingAgent()
        self.match_agent = BulkMatchAgent()
        self.ranking_agent = RankingAgent()
        self.assessment_agent = AssessmentGenerationAgent()

    def screen_batch(self, title: str, description: str, candidates: List[Dict[str, Any]], user_id: Optional[str] = None) -> Dict[str, Any]:
        # 1. Parse JD
        jd_parsed = self.jd_agent.parse_job_description(title=title, description=description, user_id=user_id)["result"]
        req_skills = jd_parsed["required_skills"]

        # 2. Score each candidate
        scored = []
        for cand in candidates:
            match_out = self.match_agent.score_candidate(
                candidate_resume=cand,
                jd_skills=req_skills,
                jd_text=description,
                user_id=user_id
            )
            cand_res = dict(cand)
            cand_res.update(match_out["result"])
            cand_res["evidence"] = match_out.get("evidence", [])
            scored.append(cand_res)

        # 3. Rank candidates
        rank_out = self.ranking_agent.rank_candidates(scored_candidates=scored, user_id=user_id)

        # 4. Generate assessment questions
        assess_out = self.assessment_agent.generate_assessment_for_jd(
            jd_title=title,
            required_skills=req_skills,
            count=3,
            user_id=user_id
        )

        return {
            "job_profile": jd_parsed,
            "ranking": rank_out["result"],
            "assessment": assess_out["result"]
        }
