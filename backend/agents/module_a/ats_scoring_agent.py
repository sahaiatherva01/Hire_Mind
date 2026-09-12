"""
HireMind AI — ATS+ Scoring Agent (Module A)
Calculates transparent 105-point rubric scores with itemized evidence citations.
"""
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from services.scoring import calculate_ats_category_scores


class ATSScoringAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="ATSScoringAgent",
            orchestrator_name="module_a_orchestrator"
        )

    def evaluate_resume(
        self,
        profile_data: dict,
        parser_metadata: dict,
        raw_text: str,
        jd_match_data: dict = None,
        entity_id: str = None
    ) -> Dict[str, Any]:
        """
        Executes ATS+ scoring across 8 categories and compiles evidence items.
        """
        scores = calculate_ats_category_scores(
            profile_data=profile_data,
            parser_metadata=parser_metadata,
            raw_text=raw_text,
            jd_match_data=jd_match_data
        )

        citations = [
            f"ATS Compatibility: {scores['ats_compatibility']}/15 (Layout multi-column: {parser_metadata.get('is_multi_column')})",
            f"Resume Structure: {scores['resume_structure']}/15 (Pages: {parser_metadata.get('page_count')})",
            f"Keyword Relevance: {scores['keyword_relevance']}/20",
            f"Content Quality: {scores['content_quality']}/15",
            f"Skills Representation: {scores['skills_representation']}/10",
            f"Quantified Impact: {scores['quantified_impact']}/10",
            f"Completeness: {scores['completeness']}/10",
            f"Readability & Consistency: {scores['readability_consistency']}/5",
            f"Total Normalized Score: {scores['overall_score']}/100"
        ]

        reasoning = (
            f"ATS+ Score of {scores['overall_score']}/100 calculated from 105 raw rubric points. "
            f"Strongest area: {self._get_strongest_category(scores)}, "
            f"Key improvement opportunity: {self._get_weakest_category(scores)}."
        )

        return self.build_agent_output(
            result=scores,
            citations=citations,
            reasoning=reasoning,
            confidence=0.98,
            entity_id=entity_id,
            entity_type="ats_scoring"
        )

    def _get_strongest_category(self, scores: dict) -> str:
        max_cats = {
            "ats_compatibility": 15, "resume_structure": 15, "keyword_relevance": 20,
            "content_quality": 15, "skills_representation": 10, "quantified_impact": 10,
            "completeness": 10, "readability_consistency": 5
        }
        ratios = [(k, scores[k] / max_cats[k]) for k in max_cats if k in scores]
        ratios.sort(key=lambda x: x[1], reverse=True)
        return ratios[0][0].replace("_", " ").title() if ratios else "General"

    def _get_weakest_category(self, scores: dict) -> str:
        max_cats = {
            "ats_compatibility": 15, "resume_structure": 15, "keyword_relevance": 20,
            "content_quality": 15, "skills_representation": 10, "quantified_impact": 10,
            "completeness": 10, "readability_consistency": 5
        }
        ratios = [(k, scores[k] / max_cats[k]) for k in max_cats if k in scores]
        ratios.sort(key=lambda x: x[1])
        return ratios[0][0].replace("_", " ").title() if ratios else "General"
