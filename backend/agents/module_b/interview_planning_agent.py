"""
HireMind AI — Interview Planning Agent (Module B)
Generates 8-10 targeted interview questions retrieval-grounded in kb_interview_questions.
"""
import json
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent
from config import Config


class InterviewPlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="InterviewPlanningAgent",
            orchestrator_name="module_b_orchestrator"
        )

    def generate_question_bank(
        self,
        parsed_resume: dict,
        target_role: Optional[str] = "Software Engineer",
        company_track: Optional[str] = "default",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates calibrated interview questions using candidate resume and grounding questions from RAG.
        """
        target_role = target_role or "Software Engineer"

        # 1. RAG Grounding: Retrieve real-world interview questions from kb_interview_questions
        rag_matches = self.retrieve(
            query=f"{target_role} {json.dumps(parsed_resume.get('skill_profile', {}).get('normalized_skills', [])[:5])}",
            collection="kb_interview_questions",
            top_k=5,
            filter_criteria={"role": target_role}
        )

        grounding_bank = ""
        citations = []
        for m in rag_matches:
            item = m["item"]
            grounding_bank += f"\n- [{item.get('stage')}/{item.get('difficulty')}] {item.get('question_text')} (Target Skill: {item.get('skill')})"
            citations.append(f"Grounded against kb_interview_questions: '{item.get('question_text')[:60]}...' (similarity: {m['similarity']})")

        # 2. RAG Grounding: Retrieve company interview style if specific track selected
        company_style_note = ""
        if company_track and company_track != "default":
            style_matches = self.retrieve(
                query=company_track,
                collection="kb_company_interview_style",
                top_k=1
            )
            if style_matches:
                st_item = style_matches[0]["item"]
                company_style_note = f"\nCompany Track Focus ({st_item.get('company_name')}): {st_item.get('evaluation_focus')}. Key Principles: {', '.join(st_item.get('culture_principles', []))}"
                citations.append(f"Applied company interview style: '{st_item.get('company_name')}'")

        prompt = f"""
You are an elite technical interviewer designing an 8-10 question interview session.

TARGET ROLE:
{target_role}
{company_style_note}

CANDIDATE RESUME PROFILE:
{json.dumps(parsed_resume, ensure_ascii=False)[:4000]}

REAL-WORLD QUESTION BANK EXAMPLES (USE AS GROUNDING TEMPLATES FOR STYLE & DEPTH):
{grounding_bank}

RULES:
- Generate exactly 8-10 questions.
- Distribute across stages: Technical Deep Dive (3-4), Project Defense (2-3), System Architecture / Problem Solving (2), HR/Behavioral (1-2).
- Ground questions specifically in candidate's actual projects, technologies, and claimed metrics.
- Avoid generic trivia; ask about implementation tradeoffs, debugging, scale bottlenecks, and decisions.

Return JSON format:
{{
  "questions": [
    {{
      "question": "...",
      "source_tag": "resume:<project_or_skill>",
      "stage": "technical|project_defense|hr|aptitude",
      "topic": "...",
      "difficulty": "easy|medium|hard"
    }}
  ]
}}
"""
        fallback_questions = {
            "questions": [
                {
                    "question": f"Walk me through the architecture of your primary project and the key engineering tradeoffs you made.",
                    "source_tag": "resume:primary_project",
                    "stage": "project_defense",
                    "topic": "Architecture",
                    "difficulty": "medium"
                },
                {
                    "question": f"How did you design and optimize database queries or API endpoints for high performance?",
                    "source_tag": "resume:backend_skills",
                    "stage": "technical",
                    "topic": "Databases & Performance",
                    "difficulty": "medium"
                },
                {
                    "question": f"Describe a scenario where you resolved a complex production bug or race condition.",
                    "source_tag": "resume:debugging",
                    "stage": "technical",
                    "topic": "Troubleshooting",
                    "difficulty": "hard"
                },
                {
                    "question": f"Tell me about a time you had a technical disagreement with a team member and how you reached alignment.",
                    "source_tag": "behavioral:collaboration",
                    "stage": "hr",
                    "topic": "Conflict Resolution",
                    "difficulty": "medium"
                }
            ]
        }

        result = self.generate_json(
            prompt=prompt,
            model=Config.DEFAULT_MODEL,
            max_output_tokens=2000,
            fallback_json=fallback_questions
        )

        questions = result.get("questions", [])
        citations.append(f"Synthesized {len(questions)} calibrated interview questions across multiple stages.")

        return self.build_agent_output(
            result={"questions": questions},
            citations=citations,
            reasoning=f"Generated {len(questions)} resume-grounded questions calibrated against kb_interview_questions.",
            confidence=0.95,
            entity_id=session_id,
            entity_type="interview_plan"
        )
