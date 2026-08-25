"""
Round Engine — the single authority on round progression.

Per the spec: "The frontend never decides whether a round is unlocked.
The Flask backend does." This module is that authority for Simulation Mode.
Practice Mode ignores all of this and stays fully open.
"""
from config import Config
from services.supabase_client import supabase_service

# Rounds not yet built (see MVP roadmap). Until their evaluation engine
# exists, they're treated as auto-cleared so they don't permanently block
# progression through the rounds that *are* live. Remove an entry here
# as soon as its round gets a real scoring route.
AUTO_CLEARED_ROUNDS = {"resume_screening"}


def get_cutoffs(track="default"):
    return Config.COMPANY_TRACKS.get(track, Config.DEFAULT_CUTOFFS)


def get_round_status(user_id, track="default"):
    """
    Returns an ordered list of round states for Simulation Mode:
      { round, status: 'cleared' | 'unlocked' | 'locked', best_score, cutoff }
    Round 1 (resume_screening) is always unlocked. Each subsequent round
    unlocks only once the previous round's best simulation-mode score
    clears its cutoff.
    """
    cutoffs = get_cutoffs(track)
    statuses = []
    previous_cleared = True  # round 0 has no prerequisite

    for round_name in Config.ROUND_ORDER:
        cutoff = cutoffs.get(round_name, 70)

        if round_name in AUTO_CLEARED_ROUNDS:
            best, cleared = None, True
        else:
            best = supabase_service.best_score(user_id, round_name, mode="simulation")
            cleared = best is not None and best >= cutoff

        if previous_cleared:
            status = "cleared" if cleared else "unlocked"
        else:
            status = "locked"

        statuses.append({
            "round": round_name,
            "status": status,
            "best_score": best,
            "cutoff": cutoff,
        })

        previous_cleared = previous_cleared and cleared

    return statuses


def is_round_unlocked(user_id, round_name, track="default"):
    statuses = {s["round"]: s["status"] for s in get_round_status(user_id, track)}
    return statuses.get(round_name) in ("unlocked", "cleared")


def final_hiring_decision(user_id, track="default"):
    """Section 13: aggregate all simulation-mode rounds into a final report."""
    cutoffs = get_cutoffs(track)
    breakdown = {}
    all_cleared = True
    total = 0
    counted = 0

    for round_name in Config.ROUND_ORDER:
        if round_name == "resume_screening":
            continue
        best = supabase_service.best_score(user_id, round_name, mode="simulation")
        cutoff = cutoffs.get(round_name, 70)
        cleared = best is not None and best >= cutoff
        breakdown[round_name] = {"score": best, "cutoff": cutoff, "cleared": cleared}
        if best is not None:
            total += best
            counted += 1
        all_cleared = all_cleared and cleared

    overall = round(total / counted, 1) if counted else 0

    return {
        "breakdown": breakdown,
        "overall": overall,
        "status": "cleared" if all_cleared and counted == len(Config.ROUND_ORDER) - 1 else "in_progress",
        "recommendation": "READY FOR PLACEMENT" if all_cleared and counted == len(Config.ROUND_ORDER) - 1 else "CONTINUE PREPARATION",
    }
