"""
HireMind AI — Interview Orchestrator (Module B)
Owns session lifecycle, question progression, specialist agent dispatch, and final debrief report.
"""
import uuid
from typing import Dict, Any, Optional

from agents.module_b.interview_planning_agent import InterviewPlanningAgent
from agents.module_b.technical_agent import TechnicalAgent
from agents.module_b.project_defense_agent import ProjectDefenseAgent
from agents.module_b.hr_agent import HRAgent
from agents.module_b.evaluation_agent import EvaluationAgent
from services.supabase_client import supabase_service
from services.round_engine import round_engine


class InterviewOrchestrator:
    def __init__(self):
        self.orchestrator_name = "module_b_orchestrator"
        self.planning_agent = InterviewPlanningAgent()
        self.technical_agent = TechnicalAgent()
        self.project_defense_agent = ProjectDefenseAgent()
        self.hr_agent = HRAgent()
        self.evaluation_agent = EvaluationAgent()

    def generate_and_store_questions(
        self,
        resume_id: str,
        target_role: Optional[str] = None,
        company_track: str = "default",
        user_id: Optional[str] = None,
        mode: str = "practice"
    ) -> Dict[str, Any]:
        """Creates session and generates tailored question bank via InterviewPlanningAgent."""
        resume_rec = supabase_service.get_resume(resume_id)
        parsed_json = resume_rec.get("parsed_json") or {}

        session_id = supabase_service.create_interview_session(
            resume_id=resume_id,
            user_id=user_id,
            target_role=target_role or "Software Engineer",
            mode=mode,
            company_track=company_track
        )

        plan_out = self.planning_agent.generate_question_bank(
            parsed_resume=parsed_json,
            target_role=target_role,
            company_track=company_track,
            session_id=session_id
        )

        questions = plan_out["result"].get("questions", [])
        supabase_service.insert_questions(session_id, questions)

        return {
            "session_id": session_id,
            "questions_count": len(questions),
            "status": "ready",
            "evidence": plan_out["evidence"]
        }

    def start_interview(
        self,
        session_id: str,
        voice_preference: str = "male"
    ) -> Dict[str, Any]:
        """Starts or resumes an interview session and returns the active question."""
        supabase_service.update_interview_session(
            session_id,
            voice_preference=voice_preference,
            status="in_progress"
        )

        active_q = supabase_service.get_active_question(session_id)
        if not active_q:
            first_q = supabase_service.get_next_pending_question(session_id)
            if not first_q:
                raise ValueError("No questions found in question bank for this session.")
            supabase_service.update_question_status(first_q["id"], "active")
            active_q = first_q

        return {
            "session_id": session_id,
            "question_id": active_q["id"],
            "question_text": active_q["seed_question"],
            "stage": active_q.get("stage", "technical"),
            "topic": active_q.get("topic", "General"),
            "is_followup": False
        }

    def submit_answer(
        self,
        session_id: str,
        question_bank_id: str,
        answer_text: str
    ) -> Dict[str, Any]:
        """
        Processes candidate answer turn, routes to stage-specific specialist agent,
        and determines whether to prompt a follow-up or advance to next topic.
        """
        answer_text = (answer_text or "").strip()
        if not answer_text:
            raise ValueError("Answer text cannot be empty.")

        # 1. Fetch current question and session context
        session_rec = supabase_service.get_interview_session(session_id)
        company_track = session_rec.get("company_track", "default")
        resume_rec = supabase_service.get_resume(session_rec.get("resume_id") or "")
        resume_context = str(resume_rec.get("parsed_json") or {})

        active_q = None
        data = supabase_service._read_local_db()
        for q in data.get("question_bank", []):
            if q.get("id") == question_bank_id:
                active_q = q
                break

        if not active_q:
            raise ValueError(f"Question {question_bank_id} not found.")

        stage = active_q.get("stage", "technical")
        q_text = active_q.get("seed_question", "")
        topic_count = active_q.get("topic_question_count", 0)

        # 2. Check for pre-created follow-up turn in transcript
        pending_turns = [
            t for t in data.get("transcript", [])
            if t.get("session_id") == session_id and t.get("question_bank_id") == question_bank_id and t.get("answer_text") is None
        ]

        turn_id = None
        is_followup = False
        if pending_turns:
            is_followup = True
            turn_rec = pending_turns[0]
            turn_id = turn_rec["id"]
            q_text = turn_rec["question_text"]
            turn_rec["answer_text"] = answer_text
            supabase_service._write_local_db(data)
        else:
            turn_rec = supabase_service.insert_transcript_turn(
                session_id=session_id,
                question_bank_id=question_bank_id,
                question_text=q_text,
                answer_text=answer_text,
                is_followup=False
            )
            turn_id = turn_rec["id"]

        # 3. Dispatch to stage specialist agent
        if stage == "project_defense":
            agent_out = self.project_defense_agent.evaluate_turn(
                question_text=q_text,
                answer_text=answer_text,
                resume_context=resume_context,
                topic_question_count=topic_count,
                turn_id=turn_id
            )
        elif stage == "hr":
            agent_out = self.hr_agent.evaluate_turn(
                question_text=q_text,
                answer_text=answer_text,
                company_track=company_track,
                topic_question_count=topic_count,
                turn_id=turn_id
            )
        else:  # Default technical
            agent_out = self.technical_agent.evaluate_turn(
                question_text=q_text,
                answer_text=answer_text,
                resume_context=resume_context,
                topic_question_count=topic_count,
                turn_id=turn_id
            )

        eval_result = agent_out["result"]
        decision = eval_result.get("decision", "NEXT_TOPIC")
        next_question = (eval_result.get("next_question") or "").strip()
        score = eval_result.get("score")

        # Update transcript turn with evaluation
        for t in data.get("transcript", []):
            if t.get("id") == turn_id:
                t["gemini_evaluation"] = eval_result.get("evaluation")
                t["reasoning_tag"] = eval_result.get("reasoning_tag")
                t["score"] = score
                break
        supabase_service._write_local_db(data)

        # 4. Handle follow-up branch
        if decision == "CROSS_QUESTION" and topic_count < 2 and next_question:
            supabase_service.increment_topic_question_count(question_bank_id)
            # Pre-create follow-up row with answer_text = None
            supabase_service.insert_transcript_turn(
                session_id=session_id,
                question_bank_id=question_bank_id,
                question_text=next_question,
                answer_text=None,
                is_followup=True
            )
            return {
                "question_id": question_bank_id,
                "question_text": next_question,
                "is_followup": True,
                "stage": stage,
                "agent_evidence": agent_out["evidence"],
                "session_complete": False
            }

        # 5. Move to next pending topic
        supabase_service.update_question_status(question_bank_id, "done")
        next_q = supabase_service.get_next_pending_question(session_id)

        if next_q:
            supabase_service.update_question_status(next_q["id"], "active")
            return {
                "question_id": next_q["id"],
                "question_text": next_q["seed_question"],
                "is_followup": False,
                "stage": next_q.get("stage", "technical"),
                "topic": next_q.get("topic", "General"),
                "agent_evidence": agent_out["evidence"],
                "session_complete": False
            }

        # All questions complete
        return {
            "session_complete": True,
            "message": "All interview topics concluded. You may now view your final debrief report.",
            "agent_evidence": agent_out["evidence"]
        }

    def end_interview_and_generate_report(self, session_id: str) -> Dict[str, Any]:
        """Concludes interview and generates final debrief report via EvaluationAgent."""
        turns = supabase_service.get_session_transcript(session_id)
        if not turns:
            raise ValueError("No transcript turns found for this interview session.")

        session_rec = supabase_service.get_interview_session(session_id)
        report_out = self.evaluation_agent.generate_final_report(turns, session_id=session_id)
        report_data = report_out["result"]

        overall_score = float(report_data.get("overall_score", 7.5))
        overall_100 = round(overall_score * 10.0, 1)

        supabase_service.update_interview_session(
            session_id,
            status="completed",
            overall_score=overall_score,
            summary_report=report_data
        )

        # Record progress for round engine (maps to 'technical', 'project_defense', or 'hr' simulation round)
        user_id = session_rec.get("user_id") or "u-dev-001"
        mode = session_rec.get("mode", "practice")
        round_engine.record_round_attempt(
            user_id=user_id,
            round_name="technical",
            score=overall_100,
            mode=mode,
            breakdown=report_data
        )

        return {
            "session_id": session_id,
            "overall_score": overall_score,
            "overall_score_percent": overall_100,
            "topic_scores": report_data.get("topic_scores", []),
            "summary_text": report_data.get("summary_text", ""),
            "strengths": report_data.get("strengths", []),
            "improvement_recommendations": report_data.get("improvement_recommendations", []),
            "evidence": report_out["evidence"]
        }


interview_orchestrator = InterviewOrchestrator()
