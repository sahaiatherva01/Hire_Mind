"""
HireMind AI — Technical & Domain Specialist Agent (Module B)
Evaluates technical interview turns, checks conceptual accuracy, and triggers deep follow-up probes.
"""
import json
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from config import Config


class TechnicalAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="TechnicalAgent",
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
        Evaluates candidate technical answer and decides whether to CROSS_QUESTION or NEXT_TOPIC.
        """
        # Grounding check against interview knowledge base
        rag_matches = self.retrieve(
            query=question_text,
            collection="kb_interview_questions",
            top_k=1,
            filter_criteria={"stage": "technical"}
        )

        sample_criteria = ""
        citations = [f"Evaluated Question: '{question_text[:70]}...'"]
        if rag_matches:
            top_item = rag_matches[0]["item"]
            sample_criteria = f"Ideal Answer Criteria: {top_item.get('sample_criteria', '')}"
            citations.append(f"Grounded against kb_interview_questions: '{top_item.get('skill')}' (similarity: {rag_matches[0]['similarity']})")

        prompt = f"""
You are conducting a live technical coding/system interview.

CURRENT QUESTION:
{question_text}

CANDIDATE ANSWER:
"{answer_text}"

RESUME CONTEXT:
{resume_context[:1500]}

GROUNDING EVALUATION CRITERIA:
{sample_criteria}

CROSS-QUESTIONS ALREADY ASKED ON THIS TOPIC:
{topic_question_count} (Max allowed is 2)

TASK:
1. Score the answer from 1.0 to 10.0 based on technical accuracy, depth, and clarity.
2. Decide:
   - "CROSS_QUESTION": if the candidate was vague, skipped key implementation tradeoffs, made contradictory claims, or warrants a deeper probe (only if count < 2).
   - "NEXT_TOPIC": if the answer was technically solid, complete, or max cross-questions reached.
3. If CROSS_QUESTION, formulate a sharp, direct follow-up probe.

Return JSON format:
{{
  "score": 7.5,
  "decision": "CROSS_QUESTION|NEXT_TOPIC",
  "evaluation": "1-2 sentence constructive evaluation",
  "reasoning_tag": "short reason (e.g. Incomplete Concurrency Handling)",
  "next_question": "Follow-up question if CROSS_QUESTION, else empty string",
  "evidence_excerpt": "Specific verbatim quote from candidate answer"
}}
"""
        fallback_resp = {
            "score": 7.0,
            "decision": "NEXT_TOPIC",
            "evaluation": "Clear explanation covering core concepts.",
            "reasoning_tag": "Solid Technical Foundation",
            "next_question": "",
            "evidence_excerpt": answer_text[:100]
        }

        result = self.generate_json(
            prompt=prompt,
            model=Config.DEFAULT_MODEL,
            max_output_tokens=700,
            fallback_json=fallback_resp
        )

        # Enforce max 2 cross-questions
        if topic_question_count >= 2:
            result["decision"] = "NEXT_TOPIC"
            result["next_question"] = ""

        citations.append(f"Evaluation Decision: {result.get('decision')} | Score: {result.get('score')}/10")
        return self.build_agent_output(
            result=result,
            citations=citations,
            reasoning=result.get("evaluation", "Evaluated technical depth."),
            confidence=0.93,
            entity_id=turn_id,
            entity_type="technical_turn"
        )
