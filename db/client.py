import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path

from config import Config

from werkzeug.security import generate_password_hash, check_password_hash

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

    def check_remote_schema(self) -> Dict[str, Any]:
        """Validates if tables defined in db/schema.sql are present in the remote Supabase project."""
        if not self.supabase:
            return {"configured": False, "status": "offline_local", "message": "Operating in local JSON fallback mode."}
        try:
            self.supabase.table("profiles").select("id").limit(1).execute()
            return {"configured": True, "status": "schema_ready", "message": "Supabase connection and schema verified."}
        except Exception as e:
            err_msg = str(e)
            print("=" * 65)
            print("⚠️ [SupabaseService] Remote Supabase connected but tables are missing!")
            print(f"Details: {err_msg}")
            print("👉 Run the SQL in db/schema.sql in your Supabase SQL editor.")
            print("=" * 65)
            return {
                "configured": True,
                "status": "schema_missing",
                "message": "Connected to Supabase, but schema tables are missing. Please execute db/schema.sql.",
                "error": err_msg
            }

    def _read_local_db(self) -> Dict[str, Any]:
        local_path = Config.LOCAL_DB_PATH
        if os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Ensure lists for all collections
                    for k in ["users", "resumes", "interview_sessions", "transcript", "evaluations", "round_progress", "recruit_jobs", "recruit_candidates"]:
                        if k not in data or not isinstance(data[k], list):
                            data[k] = []
                    return data
            except Exception:
                pass
        return {
            "users": [],
            "resumes": [],
            "interview_sessions": [],
            "transcript": [],
            "evaluations": [],
            "round_progress": [],
            "recruit_jobs": [],
            "recruit_candidates": [],
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
        for u in db["users"]:
            if u.get("email") == email:
                raise ValueError("User with this email already exists.")

        user_id = f"usr_{uuid.uuid4().hex[:10]}"
        pwd_hash = generate_password_hash(password)
        user_data = {
            "id": user_id,
            "email": email,
            "password_hash": pwd_hash,
            "full_name": full_name,
            "role": role,
            "company_id": company_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        db["users"].append(user_data)
        self._write_local_db(db)
        return {"user": {"id": user_id, "email": email, "full_name": full_name, "role": role, "company_id": company_id}}

    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        if self.supabase:
            res = self.supabase.auth.sign_in_with_password({"email": email, "password": password})
            prof = self.supabase.table("profiles").select("*").eq("id", res.user.id).single().execute()
            return {"user": prof.data, "session": {"access_token": res.session.access_token}}

        db = self._read_local_db()
        for u in db["users"]:
            if u.get("email") == email:
                stored_hash = u.get("password_hash")
                valid = False
                if stored_hash:
                    try:
                        valid = check_password_hash(stored_hash, password)
                    except Exception:
                        valid = False
                    if not valid and stored_hash == password:
                        # Auto-upgrade legacy plaintext string to genuine werkzeug hash
                        u["password_hash"] = generate_password_hash(password)
                        self._write_local_db(db)
                        valid = True
                elif u.get("password"):
                    if u.get("password") == password:
                        u["password_hash"] = generate_password_hash(password)
                        del u["password"]
                        self._write_local_db(db)
                        valid = True

                if valid:
                    return {
                        "user": {k: v for k, v in u.items() if k not in ["password", "password_hash"]},
                        "session": {"access_token": f"token_{u.get('id')}"}
                    }
                break
        raise ValueError("Invalid email or password.")

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self.supabase:
            res = self.supabase.table("profiles").select("*").eq("id", user_id).single().execute()
            return res.data
        db = self._read_local_db()
        for u in db["users"]:
            if u.get("id") == user_id:
                return {k: v for k, v in u.items() if k not in ["password", "password_hash"]}
        return None

    # --- Resumes ---
    def upload_resume_file(self, file_bytes: bytes, filename: str, user_id: str) -> Optional[str]:
        """
        Uploads binary resume file to Supabase Storage bucket 'resumes' for persistent storage across dyno restarts.
        Falls back to local disk when operating offline.
        """
        clean_fn = f"{int(datetime.now(timezone.utc).timestamp())}_{filename.replace(' ', '_')}"
        storage_path = f"{user_id}/{clean_fn}"
        if self.supabase:
            try:
                self.supabase.storage.from_("resumes").upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": "application/octet-stream", "upsert": "true"}
                )
                return storage_path
            except Exception as e:
                print(f"[SupabaseService] Notice: Supabase storage upload skipped ({e})")

        # Local fallback filesystem storage
        upload_dir = Config.UPLOAD_FOLDER / user_id
        os.makedirs(upload_dir, exist_ok=True)
        local_path = upload_dir / clean_fn
        try:
            with open(local_path, "wb") as f:
                f.write(file_bytes)
            return str(local_path)
        except Exception:
            return None

    def save_resume(self, user_id: str, filename: str, parsed_text: str, structured_data: Dict[str, Any], ats_score: Optional[float] = None, file_url: Optional[str] = None) -> str:
        resume_id = str(uuid.uuid4())
        record = {
            "id": resume_id,
            "user_id": user_id,
            "filename": filename,
            "parsed_text": parsed_text,
            "structured_data": structured_data,
            "ats_score": ats_score,
            "file_url": file_url,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        if self.supabase:
            self.supabase.table("resumes").insert(record).execute()
            return resume_id

        db = self._read_local_db()
        db["resumes"].append(record)
        self._write_local_db(db)
        return resume_id

    def get_resumes(self, user_id: str) -> List[Dict[str, Any]]:
        if self.supabase:
            res = self.supabase.table("resumes").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return res.data or []
        db = self._read_local_db()
        return [r for r in db["resumes"] if r.get("user_id") == user_id]

    def get_resume(self, resume_id: str) -> Optional[Dict[str, Any]]:
        if self.supabase:
            res = self.supabase.table("resumes").select("*").eq("id", resume_id).single().execute()
            return res.data
        db = self._read_local_db()
        for r in db["resumes"]:
            if r.get("id") == resume_id:
                return r
        return None

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
        db["interview_sessions"].append(record)
        self._write_local_db(db)
        return session_id

    def get_interview_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self.supabase:
            res = self.supabase.table("interview_sessions").select("*").eq("id", session_id).single().execute()
            return res.data
        db = self._read_local_db()
        for s in db["interview_sessions"]:
            if s.get("id") == session_id:
                return s
        return None

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
        db["transcript"].append(turn_data)
        self._write_local_db(db)

    def get_session_turns(self, session_id: str) -> List[Dict[str, Any]]:
        if self.supabase:
            res = self.supabase.table("transcripts").select("*").eq("session_id", session_id).order("turn_index").execute()
            return res.data or []
        db = self._read_local_db()
        turns = [t for t in db["transcript"] if t.get("session_id") == session_id]
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
        for s in db["interview_sessions"]:
            if s.get("id") == session_id:
                s["status"] = "completed"
                s["overall_score"] = evaluation_data.get("overall_score", 0)
                s["evaluation_report"] = evaluation_data
                s["completed_at"] = datetime.now(timezone.utc).isoformat()
                break
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

    # --- Recruiter Operations with Strict Tenant Isolation ---
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
        db["recruit_jobs"].append(record)
        self._write_local_db(db)
        return job_id

    def get_jobs(self, company_id: str) -> List[Dict[str, Any]]:
        """Strictly tenant-isolated job list."""
        if self.supabase:
            res = self.supabase.table("jobs").select("*").eq("company_id", company_id).order("created_at", desc=True).execute()
            return res.data or []
        db = self._read_local_db()
        return [j for j in db["recruit_jobs"] if j.get("company_id") == company_id]

    def get_job(self, job_id: str, company_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Tenant-isolated job retrieval."""
        if self.supabase:
            query = self.supabase.table("jobs").select("*").eq("id", job_id)
            if company_id:
                query = query.eq("company_id", company_id)
            res = query.single().execute()
            return res.data
        db = self._read_local_db()
        for j in db["recruit_jobs"]:
            if j.get("id") == job_id:
                if company_id is None or j.get("company_id") == company_id:
                    return j
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
        db["recruit_candidates"].append(record)
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
        apps = [a for a in db["recruit_candidates"] if a.get("job_id") == job_id]
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
        for r in db["round_progress"]:
            if r.get("user_id") == user_id and r.get("track", "default") == track:
                return r

        # Default progression template
        return {
            "user_id": user_id,
            "track": track,
            "current_round": Config.ROUND_ORDER[0],
            "round_scores": {},
            "round_status": {Config.ROUND_ORDER[0]: "unlocked"}
        }

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
        found = False
        for i, r in enumerate(db["round_progress"]):
            if r.get("user_id") == user_id and r.get("track", "default") == track:
                db["round_progress"][i] = record
                found = True
                break
        if not found:
            db["round_progress"].append(record)
        self._write_local_db(db)


db_client = SupabaseService()
