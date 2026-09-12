"""
HireMind AI — Supabase Client with local JSON database fallback
"""
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path

from config import Config

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

# Custom exception classes
class SupabaseNotConfiguredError(Exception):
    pass

class SupabaseAuthError(Exception):
    pass

class SupabaseServiceError(Exception):
    pass

class SupabaseStoragePermissionError(Exception):
    pass


class SupabaseService:
    def __init__(self):
        self.supabase: Optional[Client] = None
        self._is_local_fallback = False
        self._init_client()

    def _init_client(self):
        url = Config.SUPABASE_URL
        key = Config.SUPABASE_KEY or Config.SUPABASE_ANON_KEY

        if url and key and not key.startswith("your_") and create_client:
            try:
                self.supabase = create_client(url, key)
                self._is_local_fallback = False
                print("[SupabaseService] Connected to remote Supabase instance.")
                return
            except Exception as e:
                print(f"[SupabaseService] Failed to connect to Supabase: {e}. Falling back to local DB.")

        self.supabase = None
        self._is_local_fallback = True
        print("[SupabaseService] Operating in local fallback mode (local_db.json).")

    def is_configured(self) -> bool:
        return self.supabase is not None

    def check_connection(self) -> bool:
        if not self.supabase:
            return False
        try:
            self.supabase.table("profiles").select("id").limit(1).execute()
            return True
        except Exception:
            return False

    # ---------------------------------------------------------
    # Local JSON DB Helpers
    # ---------------------------------------------------------
    def _read_local_db(self) -> dict:
        p = Config.LOCAL_DB_PATH
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "users": [],
            "round_progress": [],
            "interview_sessions": [],
            "question_bank": [],
            "transcript": [],
            "resumes": [],
            "recruit_jobs": [],
            "recruit_candidates": [],
            "recruit_assessments": [],
            "evaluations": []
        }

    def _write_local_db(self, data: dict):
        p = Config.LOCAL_DB_PATH
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # ---------------------------------------------------------
    # Resume Management
    # ---------------------------------------------------------
    def upload_resume(self, file_bytes: bytes, file_name: str) -> str:
        safe_name = f"{uuid.uuid4()}_{os.path.basename(file_name)}"
        if self.supabase:
            try:
                self.supabase.storage.from_("resumes").upload(
                    path=safe_name,
                    file=file_bytes,
                    file_options={"content-type": "application/pdf"}
                )
                return safe_name
            except Exception as e:
                print(f"[SupabaseService] Storage upload failed: {e}. Falling back to local disk.")

        # Local storage fallback
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        local_path = os.path.join(Config.UPLOAD_FOLDER, safe_name)
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        return safe_name

    def download_resume(self, file_path: str) -> bytes:
        if self.supabase:
            try:
                return self.supabase.storage.from_("resumes").download(file_path)
            except Exception:
                pass
        local_path = os.path.join(Config.UPLOAD_FOLDER, file_path)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()
        raise FileNotFoundError(f"Resume file not found: {file_path}")

    def insert_resume(self, session_id: str, file_path: str, user_id: Optional[str] = None, file_name: Optional[str] = None) -> str:
        resume_id = str(uuid.uuid4())
        record = {
            "id": resume_id,
            "session_id": session_id,
            "file_path": file_path,
            "file_name": file_name,
            "user_id": user_id,
            "parsed_json": None,
            "ats_scores": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if self.supabase:
            try:
                res = self.supabase.table("resumes").insert(record).execute()
                if res.data:
                    return res.data[0]["id"]
            except Exception as e:
                print(f"[SupabaseService] insert_resume remote failed: {e}")

        data = self._read_local_db()
        data.setdefault("resumes", []).append(record)
        self._write_local_db(data)
        return resume_id

    def get_resume(self, resume_id: str) -> Dict[str, Any]:
        if self.supabase:
            try:
                res = self.supabase.table("resumes").select("*").eq("id", resume_id).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass

        data = self._read_local_db()
        for r in data.get("resumes", []):
            if r.get("id") == resume_id or r.get("session_id") == resume_id:
                return r
        raise ValueError(f"Resume {resume_id} not found.")

    def update_parsed_resume(self, resume_id: str, parsed_json: dict, ats_scores: dict = None):
        payload = {"parsed_json": parsed_json}
        if ats_scores:
            payload["ats_scores"] = ats_scores

        if self.supabase:
            try:
                self.supabase.table("resumes").update(payload).eq("id", resume_id).execute()
                return
            except Exception as e:
                print(f"[SupabaseService] update_parsed_resume remote failed: {e}")

        data = self._read_local_db()
        for r in data.get("resumes", []):
            if r.get("id") == resume_id:
                r.update(payload)
                break
        self._write_local_db(data)

    # ---------------------------------------------------------
    # Interview Sessions
    # ---------------------------------------------------------
    def create_interview_session(
        self,
        resume_id: Optional[str] = None,
        voice_pref: str = "male",
        target_role: str = "Software Engineer",
        user_id: Optional[str] = None,
        mode: str = "practice",
        company_track: str = "default"
    ) -> str:
        session_id = str(uuid.uuid4())
        rec = {
            "id": session_id,
            "resume_id": resume_id,
            "user_id": user_id,
            "voice_preference": voice_pref,
            "target_role": target_role,
            "mode": mode,
            "company_track": company_track,
            "status": "in_progress",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if self.supabase:
            try:
                res = self.supabase.table("interview_sessions").insert(rec).execute()
                if res.data:
                    return res.data[0]["id"]
            except Exception as e:
                print(f"[SupabaseService] create_interview_session remote failed: {e}")

        data = self._read_local_db()
        data.setdefault("interview_sessions", []).append(rec)
        self._write_local_db(data)
        return session_id

    def get_interview_session(self, session_id: str) -> Dict[str, Any]:
        if self.supabase:
            try:
                res = self.supabase.table("interview_sessions").select("*").eq("id", session_id).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass
        data = self._read_local_db()
        for s in data.get("interview_sessions", []):
            if s.get("id") == session_id:
                return s
        return {"id": session_id, "status": "in_progress", "target_role": "Software Engineer"}

    def update_interview_session(self, session_id: str, **kwargs):
        if self.supabase:
            try:
                self.supabase.table("interview_sessions").update(kwargs).eq("id", session_id).execute()
                return
            except Exception as e:
                print(f"[SupabaseService] update_interview_session remote failed: {e}")

        data = self._read_local_db()
        for s in data.get("interview_sessions", []):
            if s.get("id") == session_id:
                s.update(kwargs)
                break
        self._write_local_db(data)

    def insert_questions(self, session_id: str, questions: List[Dict[str, Any]]):
        rows = []
        for i, q in enumerate(questions):
            rows.append({
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "seed_question": q.get("question") or q.get("question_text", ""),
                "source_tag": q.get("source_tag", "generic"),
                "stage": q.get("stage", "technical"),
                "topic": q.get("topic", "general"),
                "difficulty": q.get("difficulty", "medium"),
                "topic_question_count": 0,
                "status": "pending",
                "order_index": i
            })

        if self.supabase:
            try:
                self.supabase.table("question_bank").insert(rows).execute()
                return
            except Exception as e:
                print(f"[SupabaseService] insert_questions remote failed: {e}")

        data = self._read_local_db()
        data.setdefault("question_bank", []).extend(rows)
        self._write_local_db(data)

    def get_active_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self.supabase:
            try:
                res = self.supabase.table("question_bank").select("*").eq("session_id", session_id).eq("status", "active").limit(1).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass
        data = self._read_local_db()
        for q in data.get("question_bank", []):
            if q.get("session_id") == session_id and q.get("status") == "active":
                return q
        return None

    def get_next_pending_question(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self.supabase:
            try:
                res = self.supabase.table("question_bank").select("*").eq("session_id", session_id).eq("status", "pending").order("order_index").limit(1).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass
        data = self._read_local_db()
        pending = [q for q in data.get("question_bank", []) if q.get("session_id") == session_id and q.get("status") == "pending"]
        if pending:
            pending.sort(key=lambda x: x.get("order_index", 0))
            return pending[0]
        return None

    def update_question_status(self, question_id: str, status: str):
        if self.supabase:
            try:
                self.supabase.table("question_bank").update({"status": status}).eq("id", question_id).execute()
                return
            except Exception:
                pass
        data = self._read_local_db()
        for q in data.get("question_bank", []):
            if q.get("id") == question_id:
                q["status"] = status
                break
        self._write_local_db(data)

    def increment_topic_question_count(self, question_id: str):
        data = self._read_local_db()
        cnt = 1
        for q in data.get("question_bank", []):
            if q.get("id") == question_id:
                q["topic_question_count"] = (q.get("topic_question_count") or 0) + 1
                cnt = q["topic_question_count"]
                break
        self._write_local_db(data)

        if self.supabase:
            try:
                self.supabase.table("question_bank").update({"topic_question_count": cnt}).eq("id", question_id).execute()
            except Exception:
                pass

    def insert_transcript_turn(self, session_id: str, question_bank_id: str, question_text: str, answer_text: Optional[str] = None, is_followup: bool = False, score: Optional[float] = None) -> Dict[str, Any]:
        turn = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "question_bank_id": question_bank_id,
            "question_text": question_text,
            "answer_text": answer_text,
            "is_followup": is_followup,
            "gemini_evaluation": None,
            "reasoning_tag": None,
            "score": score,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if self.supabase:
            try:
                res = self.supabase.table("transcript").insert(turn).execute()
                if res.data:
                    return res.data[0]
            except Exception as e:
                print(f"[SupabaseService] insert_transcript_turn remote failed: {e}")

        data = self._read_local_db()
        data.setdefault("transcript", []).append(turn)
        self._write_local_db(data)
        return turn

    def get_session_transcript(self, session_id: str) -> List[Dict[str, Any]]:
        if self.supabase:
            try:
                res = self.supabase.table("transcript").select("*").eq("session_id", session_id).order("created_at").execute()
                if res.data:
                    return res.data
            except Exception:
                pass
        data = self._read_local_db()
        turns = [t for t in data.get("transcript", []) if t.get("session_id") == session_id]
        turns.sort(key=lambda x: x.get("created_at", ""))
        return turns

    # ---------------------------------------------------------
    # Evaluations & Audit Logging
    # ---------------------------------------------------------
    def log_evaluation(
        self,
        entity_type: str,
        entity_id: str,
        orchestrator: str,
        agent_name: str,
        result_json: dict,
        evidence_json: dict,
        confidence: float,
        retrieval_logs: list = None
    ) -> str:
        eval_id = str(uuid.uuid4())
        rec = {
            "id": eval_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "orchestrator": orchestrator,
            "agent_name": agent_name,
            "result_json": result_json,
            "evidence_json": evidence_json,
            "confidence": confidence,
            "retrieval_logs": retrieval_logs or [],
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        if self.supabase:
            try:
                self.supabase.table("evaluations").insert(rec).execute()
                return eval_id
            except Exception as e:
                print(f"[SupabaseService] log_evaluation remote failed: {e}")

        data = self._read_local_db()
        data.setdefault("evaluations", []).append(rec)
        self._write_local_db(data)
        return eval_id


supabase_service = SupabaseService()
