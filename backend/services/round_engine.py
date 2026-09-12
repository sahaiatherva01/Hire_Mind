"""
HireMind AI — Round Progression & Cutoff Engine
Backend authority enforcing Simulation mode progression and cutoff gates.
"""
from typing import Dict, Any, List, Optional
from config import Config
from services.supabase_client import supabase_service


class RoundEngine:
    ROUND_ORDER = Config.ROUND_ORDER

    @classmethod
    def get_cutoffs(cls, track: str = "default") -> Dict[str, int]:
        return Config.COMPANY_TRACKS.get(track, Config.DEFAULT_CUTOFFS)

    @classmethod
    def get_user_progress(cls, user_id: str, track: str = "default") -> Dict[str, Any]:
        """
        Calculates lock/unlock state and score for each round in Simulation Mode.
        """
        cutoffs = cls.get_cutoffs(track)
        data = supabase_service._read_local_db()
        records = [
            r for r in data.get("round_progress", [])
            if r.get("user_id") == user_id and r.get("mode") == "simulation"
        ]
        cleared_map = {r["round_name"]: r for r in records if r.get("passed")}

        rounds_status = []
        is_previous_cleared = True  # First round (resume_screening) is always unlocked

        for round_name in cls.ROUND_ORDER:
            cutoff = cutoffs.get(round_name, 70)
            rec = cleared_map.get(round_name)

            if rec:
                status = "cleared"
                score = rec.get("score")
                unlocked = True
                is_previous_cleared = True
            elif is_previous_cleared:
                status = "unlocked"
                score = None
                unlocked = True
                is_previous_cleared = False
            else:
                status = "locked"
                score = None
                unlocked = False
                is_previous_cleared = False

            rounds_status.append({
                "round_name": round_name,
                "display_name": round_name.replace("_", " ").title(),
                "status": status,
                "unlocked": unlocked,
                "score": score,
                "cutoff": cutoff
            })

        return {
            "user_id": user_id,
            "track": track,
            "mode": "simulation",
            "rounds": rounds_status
        }

    @classmethod
    def can_access_round(cls, user_id: str, round_name: str, mode: str = "simulation", track: str = "default") -> bool:
        """Determines if the candidate is authorized to access a round."""
        if mode == "practice":
            return True

        if round_name not in cls.ROUND_ORDER:
            return False

        idx = cls.ROUND_ORDER.index(round_name)
        if idx == 0:
            return True  # First round is always accessible

        # Check if previous round was cleared
        prev_round = cls.ROUND_ORDER[idx - 1]
        data = supabase_service._read_local_db()
        records = [
            r for r in data.get("round_progress", [])
            if r.get("user_id") == user_id and r.get("round_name") == prev_round and r.get("mode") == "simulation" and r.get("passed")
        ]
        return len(records) > 0

    @classmethod
    def record_round_attempt(
        cls,
        user_id: str,
        round_name: str,
        score: float,
        mode: str = "simulation",
        track: str = "default",
        breakdown: dict = None
    ) -> Dict[str, Any]:
        """Records a completed round attempt and evaluates cutoff pass/fail."""
        cutoff = cls.get_cutoffs(track).get(round_name, 70)
        passed = float(score) >= cutoff

        data = supabase_service._read_local_db()
        existing = None
        for r in data.get("round_progress", []):
            if r.get("user_id") == user_id and r.get("round_name") == round_name and r.get("mode") == mode:
                existing = r
                break

        if existing:
            existing["score"] = max(existing.get("score", 0), score)
            existing["passed"] = existing.get("passed") or passed
            existing["attempts"] = existing.get("attempts", 1) + 1
            existing["breakdown"] = breakdown or {}
        else:
            new_rec = {
                "id": f"rp-{user_id}-{round_name}-{mode}",
                "user_id": user_id,
                "round_name": round_name,
                "mode": mode,
                "score": score,
                "cutoff": cutoff,
                "passed": passed,
                "breakdown": breakdown or {},
                "attempts": 1
            }
            data.setdefault("round_progress", []).append(new_rec)

        supabase_service._write_local_db(data)
        return {
            "round_name": round_name,
            "score": score,
            "cutoff": cutoff,
            "passed": passed,
            "mode": mode
        }


round_engine = RoundEngine()
