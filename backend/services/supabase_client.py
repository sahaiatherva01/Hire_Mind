"""
Supabase service wrapper.

Centralizes every Supabase call (auth, DB, storage) so the rest of the app
never touches the SDK directly. If SUPABASE_URL / SUPABASE_ANON_KEY are not
set, falls back to a local JSON-file store so the app is runnable and
demoable before real Supabase credentials exist (swap-in, not a rewrite).
"""
import json
import os
import uuid
from datetime import datetime, timezone

from config import Config

LOCAL_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "local_db.json")


def _supabase_configured():
    return bool(Config.SUPABASE_URL and Config.SUPABASE_ANON_KEY)


class LocalStore:
    """Minimal file-backed store standing in for Supabase during local dev."""

    def __init__(self, path):
        self.path = path
        if not os.path.exists(self.path):
            self._write({"users": {}, "attempts": [], "sessions": {}})

    def _read(self):
        with open(self.path, "r") as f:
            return json.load(f)

    def _write(self, data):
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    # ---- Auth ----
    def sign_up(self, email, password, full_name):
        data = self._read()
        if email in data["users"]:
            return None, "An account with this email already exists."
        user_id = str(uuid.uuid4())
        data["users"][email] = {
            "id": user_id,
            "email": email,
            "password": password,  # NOTE: local dev only — real Supabase handles hashing
            "full_name": full_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resume_profile": None,
        }
        self._write(data)
        return data["users"][email], None

    def sign_in(self, email, password):
        data = self._read()
        user = data["users"].get(email)
        if not user or user["password"] != password:
            return None, "Invalid email or password."
        return user, None

    def get_user(self, user_id):
        data = self._read()
        for u in data["users"].values():
            if u["id"] == user_id:
                return u
        return None

    # ---- Attempts / progress ----
    def record_attempt(self, attempt):
        data = self._read()
        attempt["id"] = str(uuid.uuid4())
        attempt["created_at"] = datetime.now(timezone.utc).isoformat()
        data["attempts"].append(attempt)
        self._write(data)
        return attempt

    def get_attempts(self, user_id, round_name=None, mode=None):
        data = self._read()
        results = [a for a in data["attempts"] if a["user_id"] == user_id]
        if round_name:
            results = [a for a in results if a["round"] == round_name]
        if mode:
            results = [a for a in results if a["mode"] == mode]
        return sorted(results, key=lambda a: a["created_at"], reverse=True)

    def best_score(self, user_id, round_name, mode="simulation"):
        attempts = self.get_attempts(user_id, round_name, mode)
        if not attempts:
            return None
        return max(a["score"] for a in attempts)


_local_store = LocalStore(LOCAL_DB_PATH)


class SupabaseService:
    """
    Public interface used by routes. Delegates to real Supabase SDK when
    configured, otherwise to LocalStore. Swap the internals here when real
    Supabase credentials are added — route code never changes.
    """

    def __init__(self):
        self.configured = _supabase_configured()
        if self.configured:
            # Lazy import so the package isn't a hard requirement for local dev
            from supabase import create_client
            self.client = create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)
        else:
            self.client = None

    def sign_up(self, email, password, full_name):
        if self.configured:
            res = self.client.auth.sign_up({"email": email, "password": password})
            if res.user:
                self.client.table("profiles").insert({
                    "id": res.user.id, "email": email, "full_name": full_name
                }).execute()
                return {"id": res.user.id, "email": email, "full_name": full_name}, None
            return None, "Sign up failed."
        return _local_store.sign_up(email, password, full_name)

    def sign_in(self, email, password):
        if self.configured:
            try:
                res = self.client.auth.sign_in_with_password({"email": email, "password": password})
                user = res.user
                return {"id": user.id, "email": user.email}, None
            except Exception as e:
                return None, str(e)
        return _local_store.sign_in(email, password)

    def get_user(self, user_id):
        if self.configured:
            res = self.client.table("profiles").select("*").eq("id", user_id).single().execute()
            return res.data
        return _local_store.get_user(user_id)

    def record_attempt(self, attempt):
        if self.configured:
            res = self.client.table("attempts").insert(attempt).execute()
            return res.data[0] if res.data else attempt
        return _local_store.record_attempt(attempt)

    def get_attempts(self, user_id, round_name=None, mode=None):
        if self.configured:
            q = self.client.table("attempts").select("*").eq("user_id", user_id)
            if round_name:
                q = q.eq("round", round_name)
            if mode:
                q = q.eq("mode", mode)
            res = q.order("created_at", desc=True).execute()
            return res.data
        return _local_store.get_attempts(user_id, round_name, mode)

    def best_score(self, user_id, round_name, mode="simulation"):
        if self.configured:
            attempts = self.get_attempts(user_id, round_name, mode)
            return max((a["score"] for a in attempts), default=None)
        return _local_store.best_score(user_id, round_name, mode)


supabase_service = SupabaseService()
