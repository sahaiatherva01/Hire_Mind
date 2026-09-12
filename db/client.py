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
                return
            except Exception:
                pass

        self.supabase = None
        self._is_local_fallback = True

    def is_configured(self) -> bool:
        return self.supabase is not None

    def _read_local_db(self) -> Dict[str, Any]:
        local_path = Config.LOCAL_DB_PATH
        if os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "users": {},
            "resumes": {},
            "interview_sessions": {},
            "transcripts": {},
            "evaluations": [],
            "user_progress": {},
            "jobs": {},
            "applications": {},
        }

    def _write_local_db(self, data: Dict[str, Any]):
        local_path = Config.LOCAL_DB_PATH
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # --- Authentication & Profiles ---
    def sign_up(self, email: str, password: str, full_name: str = "", role: str = "candidate", company_id: Optional[str] = None) -> Dict[str, Any]:
        if self.supabase:
            res = self.supabase.auth.sign_up({"email": email, "password": password})
            user_id = res.user.id if res.user else str(uuid.uuid4())
            self.supabase.table("profiles").upsert({
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "role": role,
                "company_id": company_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            return {"user": {"id": user_id, "email": email, "full_name": full_name, "role": role, "company_id": company_id}}

        db = self._read_local_db()
        for uid, u in db["users"].items():
            if u.get("email") == email:
                raise ValueError("User with this email already exists.")

        user_id = f"usr_{uuid.uuid4().hex[:10]}"
        user_data = {
            "id": user_id,
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": role,
            "company_id": company_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        db["users"][user_id] = user_data
        self._write_local_db(db)
        return {"user": {"id": user_id, "email": email, "full_name": full_name, "role": role, "company_id": company_id}}

    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        if self.supabase:
            res = self.supabase.auth.sign_in_with_password({"email": email, "password": password})
            prof = self.supabase.table("profiles").select("*").eq("id", res.user.id).single().execute()
            return {"user": prof.data, "session": {"access_token": res.session.access_token}}

        db = self._read_local_db()
        for uid, u in db["users"].items():
            if u.get("email") == email and u.get("password") == password:
                return {"user": {k: v for k, v in u.items() if k != "password"}, "session": {"access_token": f"token_{uid}"}}
        raise ValueError("Invalid email or password.")

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self.supabase:
            res = self.supabase.table("profiles").select("*").eq("id", user_id).single().execute()
            return res.data
        db = self._read_local_db()
        user = db["users"].get(user_id)
        if user:
            return {k: v for k, v in user.items() if k != "password"}
        return None

    # --- Resumes ---
    def save_resume(self, user_id: str, filename: str, parsed_text: str, structured_data: Dict[str, Any], ats_score: Optional[float] = None) -> str:
        resume_id = str(uuid.uuid4())
        record = {
            "id": resume_id,
            "user_id": user_id,
            "filename": filename,
            "parsed_text": parsed_text,
            "structured_data": structured_data,
            "ats_score": ats_score,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        if self.supabase:
            self.supabase.table("resumes").insert(record).execute()
            return resume_id

        db = self._read_local_db()
        db["resumes"][resume_id] = record
        self._write_local_db(db)
        return resume_id

    def get_resumes(self, user_id: str) -> List[Dict[str, Any]]:
        if self.supabase:
            res = self.supabase.table("resumes").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return res.data or []
        db = self._read_local_db()
        return [r for r in db["resumes"].values() if r.get("user_id") == user_id]

    def get_resume(self, resume_id: str) -> Optional[Dict[str, Any]]:
        if self.supabase:
            res = self.supabase.table("resumes").select("*").eq("id", resume_id).single().execute()
            return res.data
        db = self._read_local_db()
        return db["resumes"].get(resume_id)

    # --- Interview Sessions ---
    def create_interview_session(self, user_id: str, role: str, stage: str = "technical", company_tag: Optional[str] = None) -> str:
        session_id = str(uuid.uuid4())
        record = {
            "id": session_id,
            "user_id": user_id,
            "role": role,
            "stage": stage,
            "company_tag": company_tag,
            "status": "in_progress",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        if self.supabase:
            self.supabase.table("interview_sessions").insert(record).execute()
            return session_id

        db = self._read_local_db()
        db["interview_sessions"][session_id] = record
        db["transcripts"][session_id] = []
        self._write_local_db(db)
        return session_id

    def get_interview_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self.supabase:
            res = self.supabase.table("interview_sessions").select("*").eq("id", session_id).single().execute()
            return res.data
        db = self._read_local_db()
        return db["interview_sessions"].get(session_id)

    def add_transcript_turn(self, session_id: str, speaker: str, content: str, turn_index: int, stage: str, metadata: Optional[Dict[str, Any]] = None):
        turn_data = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "speaker": speaker,
            "content": content,
            "turn_index": turn_index,
            "stage": stage,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        if self.supabase:
            self.supabase.table("transcripts").insert(turn_data).execute()
            return

        db = self._read_local_db()
        if session_id not in db["transcripts"]:
            db["transcripts"][session_id] = []
        db["transcripts"][session_id].append(turn_data)
        self._write_local_db(db)

    def get_session_turns(self, session_id: str) -> List[Dict[str, Any]]:
        if self.supabase:
            res = self.supabase.table("transcripts").select("*").eq("session_id", session_id).order("turn_index").execute()
            return res.data or []
        db = self._read_local_db()
        turns = db["transcripts"].get(session_id, [])
        return sorted(turns, key=lambda x: x.get("turn_index", 0))

    def save_interview_evaluation(self, session_id: str, evaluation_data: Dict[str, Any]):
        if self.supabase:
            self.supabase.table("interview_sessions").update({
                "status": "completed",
                "overall_score": evaluation_data.get("overall_score", 0),
                "evaluation_report": evaluation_data,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", session_id).execute()
            return

        db = self._read_local_db()
        if session_id in db["interview_sessions"]:
            db["interview_sessions"][session_id]["status"] = "completed"
            db["interview_sessions"][session_id]["overall_score"] = evaluation_data.get("overall_score", 0)
            db["interview_sessions"][session_id]["evaluation_report"] = evaluation_data
            db["interview_sessions"][session_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
            self._write_local_db(db)

    # --- Agent Evaluations & Audit Trail ---
    def log_evaluation(self, agent_name: str, module: str, input_summary: str, result: Dict[str, Any], evidence: List[Dict[str, Any]], confidence: float, user_id: Optional[str] = None, session_id: Optional[str] = None):
        record = {
            "id": str(uuid.uuid4()),
            "agent_name": agent_name,
            "module": module,
            "input_summary": input_summary[:500],
            "result": result,
            "evidence": evidence,
            "confidence": confidence,
            "user_id": user_id,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        if self.supabase:
            try:
                self.supabase.table("evaluations").insert(record).execute()
                return
            except Exception:
                pass

        db = self._read_local_db()
        db["evaluations"].append(record)
        self._write_local_db(db)

    def get_evaluations(self, limit: int = 50) -> List[Dict[str, Any]]:
        if self.supabase:
            try:
                res = self.supabase.table("evaluations").select("*").order("created_at", desc=True).limit(limit).execute()
                return res.data or []
            except Exception:
                pass
        db = self._read_local_db()
        return sorted(db.get("evaluations", []), key=lambda x: x.get("created_at", ""), reverse=True)[:limit]

    # --- Recruiter B2B Operations with Strict Tenant Isolation ---
    def create_job(self, company_id: str, title: str, description: str, requirements: List[str], seniority: str = "mid") -> str:
        job_id = str(uuid.uuid4())
        record = {
            "id": job_id,
            "company_id": company_id,
            "title": title,
            "description": description,
            "requirements": requirements,
            "seniority": seniority,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        if self.supabase:
            self.supabase.table("jobs").insert(record).execute()
            return job_id

        db = self._read_local_db()
        db["jobs"][job_id] = record
        self._write_local_db(db)
        return job_id

    def get_jobs(self, company_id: str) -> List[Dict[str, Any]]:
        """Strictly tenant-isolated job list."""
        if self.supabase:
            res = self.supabase.table("jobs").select("*").eq("company_id", company_id).order("created_at", desc=True).execute()
            return res.data or []
        db = self._read_local_db()
        return [j for j in db["jobs"].values() if j.get("company_id") == company_id]

    def get_job(self, job_id: str, company_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Tenant-isolated job retrieval."""
        if self.supabase:
            query = self.supabase.table("jobs").select("*").eq("id", job_id)
            if company_id:
                query = query.eq("company_id", company_id)
            res = query.single().execute()
            return res.data
        db = self._read_local_db()
        job = db["jobs"].get(job_id)
        if job and (company_id is None or job.get("company_id") == company_id):
            return job
        return None

    def submit_job_application(self, job_id: str, candidate_id: str, resume_id: str, score: float, rank_data: Dict[str, Any]) -> str:
        app_id = str(uuid.uuid4())
        record = {
            "id": app_id,
            "job_id": job_id,
            "candidate_id": candidate_id,
            "resume_id": resume_id,
            "score": score,
            "rank_data": rank_data,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        if self.supabase:
            self.supabase.table("job_applications").insert(record).execute()
            return app_id

        db = self._read_local_db()
        db["applications"][app_id] = record
        self._write_local_db(db)
        return app_id

    def get_job_applications(self, job_id: str, company_id: str) -> List[Dict[str, Any]]:
        """Returns applications for a job ONLY if that job belongs to the requested company_id."""
        job = self.get_job(job_id, company_id)
        if not job:
            return []

        if self.supabase:
            res = self.supabase.table("job_applications").select("*").eq("job_id", job_id).order("score", desc=True).execute()
            return res.data or []

        db = self._read_local_db()
        apps = [a for a in db["applications"].values() if a.get("job_id") == job_id]
        return sorted(apps, key=lambda x: x.get("score", 0), reverse=True)

    # --- Simulation Progression ---
    def get_user_progress(self, user_id: str, track: str = "default") -> Dict[str, Any]:
        if self.supabase:
            try:
                res = self.supabase.table("user_progress").select("*").eq("user_id", user_id).eq("track", track).single().execute()
                if res.data:
                    return res.data
            except Exception:
                pass

        db = self._read_local_db()
        key = f"{user_id}_{track}"
        return db["user_progress"].get(key, {
            "user_id": user_id,
            "track": track,
            "current_round": Config.ROUND_ORDER[0],
            "round_scores": {},
            "round_status": {Config.ROUND_ORDER[0]: "unlocked"}
        })

    def save_user_progress(self, user_id: str, track: str, progress_data: Dict[str, Any]):
        record = {
            "user_id": user_id,
            "track": track,
            **progress_data,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if self.supabase:
            try:
                self.supabase.table("user_progress").upsert(record).execute()
                return
            except Exception:
                pass

        db = self._read_local_db()
        key = f"{user_id}_{track}"
        db["user_progress"][key] = record
        self._write_local_db(db)


db_client = SupabaseService()
