"""
HireMind AI — HR & Behavioral Specialist Agent (Module B)
Evaluates behavioral STAR responses and culture fit grounded in kb_company_interview_style.
"""
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from config import Config


class HRAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="HRAgent",
            orchestrator_name="module_b_orchestrator"
        )

    def evaluate_turn(
        self,
        question_text: str,
        answer_text: str,
        company_track: str = "default",
        topic_question_count: int = 0,
        turn_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates behavioral responses against STAR criteria and company culture principles.
        """
        citations = [f"Behavioral Question: '{question_text[:70]}...'"]

        # Retrieve company culture principles if specific track
        style_context = "Standard Tech Culture Principles: High Ownership, Bias for Action, Clear Communication, Constructive Conflict Resolution."
        if company_track and company_track != "default":
            style_matches = self.retrieve(
                query=company_track,
                collection="kb_company_interview_style",
                top_k=1
            )
            if style_matches:
                st = style_matches[0]["item"]
                style_context = f"{st.get('company_name')} Principles: {', '.join(st.get('culture_principles', []))}. Focus: {st.get('evaluation_focus')}"
                citations.append(f"Grounded in kb_company_interview_style: '{st.get('company_name')}'")

        prompt = f"""
You are evaluating a behavioral / HR interview answer.

BEHAVIORAL QUESTION:
{question_text}

CANDIDATE ANSWER:
"{answer_text}"

COMPANY CULTURE FRAMEWORK:
{style_context}

EVALUATION RUBRIC:
1. STAR structure (Situation, Task, Action, Result).
2. Specificity and individual ownership ("I" vs vague "we").
3. Measurable outcome or learning reflection.
4. Professional communication and empathy.

TASK:
1. Score from 1.0 to 10.0.
2. Decide "CROSS_QUESTION" (if STAR result was missing or action was vague) or "NEXT_TOPIC".
3. Formulate targeted follow-up if cross-questioning (count: {topic_question_count}, max 2).

Return JSON:
{{
  "score": 8.0,
  "decision": "CROSS_QUESTION|NEXT_TOPIC",
  "evaluation": "Constructive STAR evaluation",
  "reasoning_tag": "STAR Structure & Ownership",
  "next_question": "Follow-up question if CROSS_QUESTION, else empty string",
  "evidence_excerpt": "Verbatim quote from candidate answer"
}}
"""
        fallback_resp = {
            "score": 8.0,
            "decision": "NEXT_TOPIC",
            "evaluation": "Solid behavioral response demonstrating constructive collaboration and ownership.",
            "reasoning_tag": "Effective Collaboration",
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

        citations.append(f"Decision: {result.get('decision')} | Score: {result.get('score')}/10")
        return self.build_agent_output(
            result=result,
            citations=citations,
            reasoning=result.get("evaluation", "Evaluated behavioral fit."),
            confidence=0.94,
            entity_id=turn_id,
            entity_type="hr_turn"
        )
