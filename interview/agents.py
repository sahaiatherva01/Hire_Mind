import uuid
from typing import Dict, Any, List, Optional

from core.evaluation import BaseAgent
from db.client import db_client
from core.scoring import can_progress_to_next_round


class InterviewPlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="InterviewPlanningAgent", orchestrator_name="interview_orchestrator")

    def plan_interview(self, role: str, stage: str = "technical", company_tag: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        evidence = self.retrieve(
            query=f"{role} {stage}",
            collection="kb_interview_questions",
            top_k=5,
            filter_criteria={"stage": stage} if stage in ["technical", "hr", "project_defense"] else None
        )

        questions = []
        for idx, item in enumerate(evidence):
            raw = item.get("raw_data", {})
            questions.append({
                "id": raw.get("id", f"q-{idx+1}"),
                "question": raw.get("question_text") or item.get("content"),
                "skill": raw.get("skill", "Engineering"),
                "difficulty": raw.get("difficulty", "medium"),
                "sample_criteria": raw.get("sample_criteria", "Clear technical explanation and tradeoffs")
            })

        if not questions:
            # Fallback based on stage
            defaults = {
                "technical": "Explain how you handle concurrency and race conditions in high-throughput backend services.",
                "project_defense": "Describe the most complex architectural decision you made in your recent project. What were the alternatives?",
                "hr": "Tell me about a time you strongly disagreed with a technical direction. How did you resolve it?"
            }
            questions.append({
                "id": "q-default-1",
                "question": defaults.get(stage, defaults["technical"]),
                "skill": "Software Engineering",
                "difficulty": "medium",
                "sample_criteria": "Demonstrates structured thinking and technical depth"
            })

        result = {
            "role": role,
            "stage": stage,
            "questions": questions,
            "question_count": len(questions)
        }

        return self.format_output(
            result=result,
            evidence=evidence,
            confidence=0.94,
            input_summary=f"Planned {len(questions)} questions for {role} ({stage})",
            user_id=user_id
        )


class TechnicalAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="TechnicalAgent", orchestrator_name="interview_orchestrator")

    def evaluate_answer_and_followup(self, question: str, answer: str, criteria: str, user_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        evidence = self.retrieve(query=f"{question} {criteria}", collection="kb_interview_questions", top_k=2)

        prompt = f"""Evaluate this candidate answer to a technical question.
Question: "{question}"
Evaluation Criteria: "{criteria}"
Candidate Answer: "{answer}"

Assess whether the answer demonstrates conceptual accuracy, technical depth, and specific examples.
Provide a concise follow-up cross-question challenging their answer or digging deeper.
Return JSON with keys:
"score": integer between 0 and 100,
"strengths": list of strings,
"improvements": list of strings,
"follow_up_question": string,
"feedback": string
"""
        fallback = {
            "score": 78,
            "strengths": ["Clear communication of core concept", "Identified primary architectural considerations"],
            "improvements": ["Could elaborate more on failure modes and edge case handling"],
            "follow_up_question": "How would your approach change if data volume increased by 100x and network latency spiked?",
            "feedback": "Solid conceptual explanation with good fundamentals."
        }

        result = self.generate_json_response(prompt, fallback=fallback)
        return self.format_output(
            result=result,
            evidence=evidence,
            confidence=0.89,
            input_summary=f"Evaluated answer for: {question[:40]}",
            user_id=user_id,
            session_id=session_id
        )


class ProjectDefenseAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="ProjectDefenseAgent", orchestrator_name="interview_orchestrator")

    def probe_project(self, project_summary: str, candidate_answer: str, user_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        evidence = self.retrieve(query="microservices architecture distributed systems trade-offs", collection="kb_interview_questions", top_k=2)

        prompt = f"""You are a Principal Engineer conducting a Project Architecture Defense interview.
Candidate Project: "{project_summary}"
Candidate Explanation: "{candidate_answer}"

Evaluate the technical ownership, depth, and clarity of design trade-offs.
Return JSON with:
"score": integer between 0 and 100,
"architectural_depth": "high" or "medium" or "low",
"probe_question": string targeting trade-offs, bottlenecks, or failure modes,
"feedback": string
"""
        fallback = {
            "score": 82,
            "architectural_depth": "high",
            "probe_question": "If your primary database replica goes down during peak traffic, what guarantees does your service preserve?",
            "feedback": "Strong command of data flow and component decoupling."
        }

        result = self.generate_json_response(prompt, fallback=fallback)
        return self.format_output(
            result=result,
            evidence=evidence,
            confidence=0.90,
            input_summary=f"Project defense probe: {project_summary[:40]}",
            user_id=user_id,
            session_id=session_id
        )


class HRAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="HRAgent", orchestrator_name="interview_orchestrator")

    def evaluate_behavioral(self, question: str, answer: str, user_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        evidence = self.retrieve(query="behavioral leadership STAR principles conflict resolution", collection="kb_interview_questions", top_k=2)

        prompt = f"""Evaluate this behavioral/culture fit response using the STAR (Situation, Task, Action, Result) method.
Question: "{question}"
Answer: "{answer}"

Assess whether the candidate gave a specific, measurable result and took personal accountability.
Return JSON with:
"score": integer between 0 and 100,
"star_breakdown": {{"situation_clear": bool, "action_specified": bool, "result_quantified": bool}},
"strengths": list of strings,
"feedback": string
"""
        fallback = {
            "score": 80,
            "star_breakdown": {"situation_clear": True, "action_specified": True, "result_quantified": False},
            "strengths": ["Clear context setting", "Focus on collaborative outcome"],
            "feedback": "Good ownership narrative. Quantifying the final impact would strengthen the answer."
        }

        result = self.generate_json_response(prompt, fallback=fallback)
        return self.format_output(
            result=result,
            evidence=evidence,
            confidence=0.88,
            input_summary=f"HR STAR evaluation: {question[:40]}",
            user_id=user_id,
            session_id=session_id
        )


class EvaluationAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_name="EvaluationAgent", orchestrator_name="interview_orchestrator")

    def generate_final_report(self, session_turns: List[Dict[str, Any]], stage: str, role: str, user_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        evidence = self.retrieve(query=f"{role} {stage} performance criteria", collection="kb_interview_questions", top_k=2)

        turn_scores = []
        for t in session_turns:
            meta = t.get("metadata", {})
            if "score" in meta:
                turn_scores.append(float(meta["score"]))

        avg_score = round(sum(turn_scores) / max(1, len(turn_scores)), 1) if turn_scores else 75.0

        report = {
            "overall_score": avg_score,
            "role": role,
            "stage": stage,
            "turns_completed": len(session_turns),
            "dimensions": {
                "technical_competence": min(100.0, avg_score + 2.0),
                "communication_clarity": min(100.0, max(60.0, avg_score - 1.0)),
                "problem_solving": avg_score
            },
            "strengths": [
                "Strong foundational domain knowledge",
                "Articulated technical reasoning with structured steps"
            ],
            "areas_for_growth": [
                "Incorporate more quantifiable outcome metrics into answers",
                "Proactively explore failure modes and edge cases without prompting"
            ]
        }

        return self.format_output(
            result=report,
            evidence=evidence,
            confidence=0.93,
            input_summary=f"Final interview debrief report for {role} ({stage})",
            user_id=user_id,
            session_id=session_id
        )


class InterviewOrchestrator:
    def __init__(self):
        self.planning_agent = InterviewPlanningAgent()
        self.technical_agent = TechnicalAgent()
        self.project_agent = ProjectDefenseAgent()
        self.hr_agent = HRAgent()
        self.eval_agent = EvaluationAgent()

    def start_session(self, user_id: str, role: str = "Software Engineer", stage: str = "technical") -> Dict[str, Any]:
        session_id = db_client.create_interview_session(user_id=user_id, role=role, stage=stage)
        plan = self.planning_agent.plan_interview(role=role, stage=stage, user_id=user_id)

        first_q = plan["result"]["questions"][0] if plan["result"]["questions"] else {
            "id": "q-1",
            "question": "Can you walk me through your technical background and experience?",
            "sample_criteria": "Structured introduction"
        }

        # Save question as turn 0
        db_client.add_transcript_turn(
            session_id=session_id,
            speaker="interviewer",
            content=first_q["question"],
            turn_index=0,
            stage=stage,
            metadata={"question_id": first_q.get("id"), "criteria": first_q.get("sample_criteria")}
        )

        return {
            "session_id": session_id,
            "role": role,
            "stage": stage,
            "current_question": first_q["question"],
            "turn_index": 0,
            "total_questions_planned": len(plan["result"]["questions"]),
            "evidence": plan.get("evidence", [])
        }

    def process_candidate_answer(self, session_id: str, answer: str, user_id: str) -> Dict[str, Any]:
        turns = db_client.get_session_turns(session_id)
        current_turn_index = len(turns)

        # Find the last interviewer question
        last_question = "Tell me about your approach."
        criteria = "Technical correctness"
        for t in reversed(turns):
            if t.get("speaker") == "interviewer":
                last_question = t.get("content", "")
                criteria = t.get("metadata", {}).get("criteria", criteria)
                break

        sess = db_client.get_interview_session(session_id) or {}
        stage = sess.get("stage", "technical")

        # Evaluate answer via specialist agent
        if stage == "hr":
            eval_out = self.hr_agent.evaluate_behavioral(last_question, answer, user_id=user_id, session_id=session_id)
        elif stage == "project_defense":
            eval_out = self.project_agent.probe_project("Architecture", answer, user_id=user_id, session_id=session_id)
        else:
            eval_out = self.technical_agent.evaluate_answer_and_followup(last_question, answer, criteria, user_id=user_id, session_id=session_id)

        eval_res = eval_out["result"]

        # Store candidate turn
        db_client.add_transcript_turn(
            session_id=session_id,
            speaker="candidate",
            content=answer,
            turn_index=current_turn_index,
            stage=stage,
            metadata=eval_res
        )

        # Decide whether to ask follow-up or complete session (default 4 turns)
        if current_turn_index >= 6:
            final_report_out = self.eval_agent.generate_final_report(
                session_turns=db_client.get_session_turns(session_id),
                stage=stage,
                role=sess.get("role", "Software Engineer"),
                user_id=user_id,
                session_id=session_id
            )
            db_client.save_interview_evaluation(session_id, final_report_out["result"])

            # Update progression score
            round_mapping = {"technical": "technical", "project_defense": "project_defense", "hr": "hr"}
            round_key = round_mapping.get(stage, "technical")
            prog = db_client.get_user_progress(user_id)
            round_scores = prog.get("round_scores", {})
            round_scores[round_key] = final_report_out["result"]["overall_score"]
            prog["round_scores"] = round_scores
            db_client.save_user_progress(user_id, "default", prog)

            return {
                "session_id": session_id,
                "is_completed": True,
                "evaluation": eval_res,
                "final_report": final_report_out["result"],
                "progression": can_progress_to_next_round(round_key, final_report_out["result"]["overall_score"])
            }

        next_q = eval_res.get("follow_up_question") or eval_res.get("probe_question") or "Can you expand on how you validated this approach?"

        db_client.add_transcript_turn(
            session_id=session_id,
            speaker="interviewer",
            content=next_q,
            turn_index=current_turn_index + 1,
            stage=stage,
            metadata={"criteria": "Follow-up depth"}
        )

        return {
            "session_id": session_id,
            "is_completed": False,
            "turn_index": current_turn_index + 1,
            "next_question": next_q,
            "evaluation": eval_res
        }
