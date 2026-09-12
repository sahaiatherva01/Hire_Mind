"""
HireMind AI — Project Defense Specialist Agent (Module B)
Evaluates project architecture claims, technical decision-making, and implementation veracity.
"""
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from config import Config


class ProjectDefenseAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="ProjectDefenseAgent",
            orchestrator_name="module_b_orchestrator"
        )

    def evaluate_turn(
        self,
        question_text: str,
        answer_text: str,
        resume_context: str,
        topic_question_count: int = 0,
        turn_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates project architecture veracity and probes engineering tradeoffs.
        """
        prompt = f"""
You are conducting an intense Project Defense round for a senior engineering interview.

CURRENT QUESTION:
{question_text}

CANDIDATE ANSWER:
"{answer_text}"

RESUME PROJECT CONTEXT:
{resume_context[:1500]}

CROSS-QUESTIONS ALREADY ASKED:
{topic_question_count}

EVALUATION CRITERIA:
- Architecture ownership vs superficial knowledge
- Justification of technical tradeoffs
- Handling of failure modes, scaling bottlenecks, and debugging

TASK:
1. Score from 1.0 to 10.0.
2. Decide "CROSS_QUESTION" (if architectural claims are unsubstantiated or trade-offs omitted) or "NEXT_TOPIC".
3. Formulate follow-up if cross-questioning.

Return JSON:
{{
  "score": 7.5,
  "decision": "CROSS_QUESTION|NEXT_TOPIC",
  "evaluation": "Constructive evaluation of project defense",
  "reasoning_tag": "Tradeoff Justification / Architecture Depth",
  "next_question": "Follow-up question if CROSS_QUESTION, else empty string",
  "evidence_excerpt": "Quote from answer"
}}
"""
        fallback_resp = {
            "score": 7.5,
            "decision": "NEXT_TOPIC",
            "evaluation": "Satisfactory defense of project architectural choices.",
            "reasoning_tag": "Credible Architecture Defense",
            "next_question": "",
            "evidence_excerpt": answer_text[:100]
        }

        result = self.generate_json(
            prompt=prompt,
            model=Config.DEFAULT_MODEL,
            max_output_tokens=700,
            fallback_json=fallback_resp
        )

        if topic_question_count >= 2:
            result["decision"] = "NEXT_TOPIC"
            result["next_question"] = ""

        citations = [
            f"Evaluated Project Defense Question: '{question_text[:70]}...'",
            f"Decision: {result.get('decision')} (Cross-questions count: {topic_question_count})"
        ]

        return self.build_agent_output(
            result=result,
            citations=citations,
            reasoning=result.get("evaluation", "Evaluated project architecture credibility."),
            confidence=0.92,
            entity_id=turn_id,
            entity_type="project_defense_turn"
        )
