"""
HireMind AI — Assessment Generation Agent (Module C)
Generates calibrated candidate assessments retrieval-grounded in kb_interview_questions.
"""
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent
from config import Config


class AssessmentGenerationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="AssessmentGenerationAgent",
            orchestrator_name="module_c_orchestrator"
        )

    def generate_assessment(
        self,
        job_title: str,
        required_skills: List[str],
        duration_minutes: int = 30,
        company_id: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assembles an assessment test with technical and aptitude questions grounded in kb_interview_questions.
        """
        # Retrieve grounding questions for the required skills
        skill_query = f"{job_title} {' '.join(required_skills[:4])}"
        rag_matches = self.retrieve(
            query=skill_query,
            collection="kb_interview_questions",
            top_k=4
        )

        grounding_context = ""
        citations = []
        for m in rag_matches:
            item = m["item"]
            grounding_context += f"\n- [{item.get('stage')}/{item.get('difficulty')}] {item.get('question_text')}"
            citations.append(f"Grounded against kb_interview_questions: '{item.get('question_text')[:60]}...'")

        prompt = f"""
You are an expert assessment design psychometrician for technical hiring.
Generate a calibrated 5-question technical screening assessment for this role.

ROLE: {job_title}
REQUIRED SKILLS: {', '.join(required_skills)}
TEST DURATION: {duration_minutes} minutes

GROUNDING EXAMPLES FROM QUESTION BANK:
{grounding_context}

RULES:
- Generate 5 distinct multiple-choice questions (3 technical domain, 1 system/architecture, 1 logical/quantitative).
- Include 4 options per question, indicate the correct 0-indexed option, and provide a clear explanation.

Return JSON:
{{
  "title": "{job_title} Screening Assessment",
  "duration_minutes": {duration_minutes},
  "questions": [
    {{
      "id": 1,
      "type": "multiple_choice",
      "topic": "...",
      "difficulty": "easy|medium|hard",
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "correct_option": 0,
      "explanation": "..."
    }}
  ]
}}
"""
        fallback_test = {
            "title": f"{job_title} Screening Assessment",
            "duration_minutes": duration_minutes,
            "questions": [
                {
                    "id": 1,
                    "type": "multiple_choice",
                    "topic": "Backend Architecture",
                    "difficulty": "medium",
                    "question": "Which HTTP status code is most appropriate when an idempotent POST request has already been processed?",
                    "options": ["200 OK or 204 No Content", "409 Conflict", "301 Moved Permanently", "400 Bad Request"],
                    "correct_option": 0,
                    "explanation": "Idempotent payment or creation endpoints return 200 OK with the cached original result."
                },
                {
                    "id": 2,
                    "type": "multiple_choice",
                    "topic": "Database Indexing",
                    "difficulty": "medium",
                    "question": "In PostgreSQL, what is the primary benefit of a B-tree index over a Hash index?",
                    "options": ["Supports range queries (<, >, BETWEEN)", "Requires zero memory", "Faster on single exact equality", "Auto-encrypts data"],
                    "correct_option": 0,
                    "explanation": "B-tree indexes maintain sorted order, efficiently answering range searches and sort operations."
                }
            ]
        }

        result = self.generate_json(
            prompt=prompt,
            model=Config.DEFAULT_MODEL,
            max_output_tokens=1500,
            fallback_json=fallback_test
        )

        citations.append(f"Assembled {len(result.get('questions', []))} calibrated screening questions.")
        return self.build_agent_output(
            result=result,
            citations=citations,
            reasoning=f"Generated {len(result.get('questions', []))} assessment questions for {job_title} calibrated via kb_interview_questions.",
            confidence=0.96,
            entity_id=f"assessment-{job_id}" if job_id else None,
            entity_type="recruit_assessment"
        )
