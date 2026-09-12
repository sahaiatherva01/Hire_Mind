"""
HireMind AI — Ranking Agent (Module C)
Evaluates bulk candidate matches and produces explainable Strong/Review/Weak classifications with audit evidence.
"""
from typing import Dict, Any, List
from agents.base_agent import BaseAgent


class RankingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="RankingAgent",
            orchestrator_name="module_c_orchestrator"
        )

    def rank_candidates(
        self,
        match_results: List[Dict[str, Any]],
        company_id: str,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Ranks candidates into Strong Match / Review Needed / Weak Match buckets with evidence citations.
        """
        ranked_candidates = []
        citations = [f"Ranking {len(match_results)} candidates for Job {job_id}"]

        for cand in match_results:
            score = cand.get("match_score", 0.0)
            missing_req = cand.get("missing_required_skills", [])
            matched_req = cand.get("matched_required_skills", [])

            # Classification logic with explainable rules
            if score >= 80.0 and len(missing_req) <= 1:
                category = "Strong Match"
                badge_color = "var(--color-green)"
                justification = f"High skill alignment ({score}%) covering {len(matched_req)} core requirements with minimal gaps."
            elif score >= 60.0 or len(matched_req) >= 2:
                category = "Review Needed"
                badge_color = "var(--color-amber)"
                justification = f"Moderate match ({score}%). Possesses core foundations ({', '.join(matched_req[:2])}) but missing {', '.join(missing_req[:2])}."
            else:
                category = "Weak Match"
                badge_color = "var(--color-red)"
                justification = f"Low alignment ({score}%). Missing essential required skills: {', '.join(missing_req[:3])}."

            cand_entry = {
                "candidate_id": cand.get("candidate_id"),
                "candidate_name": cand.get("candidate_name"),
                "email": cand.get("email"),
                "match_score": score,
                "ranking_category": category,
                "badge_color": badge_color,
                "justification": justification,
                "matched_required_skills": matched_req,
                "missing_required_skills": missing_req,
                "matched_preferred_skills": cand.get("matched_preferred_skills", []),
                "evidence_citations": [
                    f"Match Score: {score}%",
                    f"Matched Skills: {', '.join(matched_req)}",
                    f"Missing Requirements: {', '.join(missing_req) if missing_req else 'None'}"
                ]
            }
            ranked_candidates.append(cand_entry)

        # Sort: Strong Match first, then by match score descending
        cat_order = {"Strong Match": 0, "Review Needed": 1, "Weak Match": 2}
        ranked_candidates.sort(key=lambda x: (cat_order.get(x["ranking_category"], 3), -x["match_score"]))

        citations.append(f"Ranked distribution: {sum(1 for c in ranked_candidates if c['ranking_category'] == 'Strong Match')} Strong, "
                         f"{sum(1 for c in ranked_candidates if c['ranking_category'] == 'Review Needed')} Review, "
                         f"{sum(1 for c in ranked_candidates if c['ranking_category'] == 'Weak Match')} Weak.")

        return self.build_agent_output(
            result=ranked_candidates,
            citations=citations,
            reasoning=f"Completed multi-dimensional ranking with category evidence for {len(ranked_candidates)} candidates.",
            confidence=0.96,
            entity_id=f"rank-{company_id}-{job_id}",
            entity_type="recruit_rankings"
        )
