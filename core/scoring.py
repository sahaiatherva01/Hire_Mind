import re
from typing import Dict, Any, List, Optional
from config import Config
from db.client import db_client


def calculate_ats_category_scores(
    profile_data: dict,
    parser_metadata: dict,
    raw_text: str,
    jd_match_data: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Computes transparent ATS+ scores across 8 categories (105 raw points max).
    Returns category breakdown and overall score normalized to 0-100.
    """
    text_len = len(raw_text or "")
    pages = parser_metadata.get("page_count", 1)
    raw_lower = (raw_text or "").lower()

    # 1. ATS Compatibility (Max 15)
    ats_comp = 15.0
    if parser_metadata.get("is_multi_column", False):
        ats_comp -= 3.0
    if parser_metadata.get("has_tables", False):
        ats_comp -= 2.0
    if text_len < 300:
        ats_comp -= 6.0
    ats_comp = max(0.0, min(15.0, ats_comp))

    # 2. Resume Structure (Max 15)
    structure = 15.0
    exp = profile_data.get("experience", [])
    edu = profile_data.get("education", [])
    proj = profile_data.get("projects", [])
    if not exp:
        structure -= 4.0
    if not edu:
        structure -= 3.0
    if not proj:
        structure -= 2.0
    if pages > 3:
        structure -= 3.0
    structure = max(0.0, min(15.0, structure))

    # 3. Keyword / Job Relevance (Max 20)
    if jd_match_data and "jd_match_score" in jd_match_data:
        keyword = round((float(jd_match_data["jd_match_score"]) / 100.0) * 20.0, 1)
    else:
        skills_count = len(profile_data.get("skill_profile", {}).get("normalized_skills", []))
        keyword = min(20.0, max(5.0, skills_count * 1.2))

    # 4. Content Quality & Strong Verbs (Max 15)
    action_verbs = [
        "architected", "engineered", "spearheaded", "developed", "optimized",
        "implemented", "designed", "streamlined", "automated", "built", "led"
    ]
    verb_matches = sum(1 for v in action_verbs if v in raw_lower)
    content_quality = min(15.0, max(4.0, verb_matches * 2.5))

    # 5. Skills Representation (Max 10)
    categorized = profile_data.get("skill_profile", {}).get("categorized_skills", {})
    categories_filled = len([c for c, s in categorized.items() if s])
    skills_rep = min(10.0, max(3.0, categories_filled * 2.5))

    # 6. Quantifiable Impact & Metrics (Max 15)
    metric_matches = len(re.findall(r"\b\d+[\%|\+xX]?|\$\d+|\b\d+\s*(?:ms|seconds|users|requests|mb|gb|tb)", raw_lower))
    impact_score = min(15.0, max(3.0, metric_matches * 2.0))

    # 7. Grammar, Length & Formatting (Max 10)
    formatting = 10.0
    if pages == 0 or text_len < 200:
        formatting -= 5.0
    elif pages > 2:
        formatting -= 2.0
    formatting = max(0.0, min(10.0, formatting))

    # 8. Contact Information (Max 5)
    contact = 5.0
    contact_info = profile_data.get("contact", {})
    if not contact_info.get("email"):
        contact -= 2.5
    if not contact_info.get("phone"):
        contact -= 1.5
    if not contact_info.get("linkedin"):
        contact -= 1.0
    contact = max(0.0, min(5.0, contact))

    total_raw = ats_comp + structure + keyword + content_quality + skills_rep + impact_score + formatting + contact
    normalized_score = round((total_raw / 105.0) * 100.0, 1)

    return {
        "overall_score": normalized_score,
        "raw_points": round(total_raw, 1),
        "max_points": 105.0,
        "categories": {
            "ats_compatibility": {"score": round(ats_comp, 1), "max": 15},
            "structure": {"score": round(structure, 1), "max": 15},
            "keyword_relevance": {"score": round(keyword, 1), "max": 20},
            "content_quality": {"score": round(content_quality, 1), "max": 15},
            "skills_representation": {"score": round(skills_rep, 1), "max": 10},
            "quantifiable_impact": {"score": round(impact_score, 1), "max": 15},
            "formatting": {"score": round(formatting, 1), "max": 10},
            "contact_info": {"score": round(contact, 1), "max": 5}
        }
    }


def calculate_overall_readiness(round_scores: Dict[str, float]) -> Dict[str, Any]:
    """
    Computes overall candidate readiness (0-100) using weighted round scores.
    """
    weights = Config.READINESS_WEIGHTS
    weighted_sum = 0.0
    weight_total = 0.0

    breakdown = {}
    for round_name, weight in weights.items():
        score = round_scores.get(round_name)
        if score is not None:
            weighted_sum += float(score) * weight
            weight_total += weight
            breakdown[round_name] = {"score": float(score), "weight": weight}
        else:
            breakdown[round_name] = {"score": None, "weight": weight}

    overall = round(weighted_sum / weight_total, 1) if weight_total > 0 else 0.0
    return {
        "readiness_score": overall,
        "completed_weight": round(weight_total, 2),
        "breakdown": breakdown
    }


def can_progress_to_next_round(current_round: str, score: float) -> Dict[str, Any]:
    """
    Validates whether a candidate passed the cutoff gate for the specified simulation round.
    """
    cutoff = Config.DEFAULT_CUTOFFS.get(current_round, 70)
    passed = float(score) >= float(cutoff)

    order = Config.ROUND_ORDER
    next_round = None
    if passed and current_round in order:
        idx = order.index(current_round)
        if idx + 1 < len(order):
            next_round = order[idx + 1]

    return {
        "current_round": current_round,
        "score": score,
        "cutoff": cutoff,
        "passed": passed,
        "next_round": next_round
    }


def get_round_progression_status(user_id: str, track: str = "default") -> Dict[str, Any]:
    """
    Calculates lock/unlock and completion status for all simulation rounds.
    """
    progress = db_client.get_user_progress(user_id, track)
    round_scores = progress.get("round_scores", {})
    rounds_data = []

    order = Config.ROUND_ORDER
    previous_passed = True

    for idx, round_name in enumerate(order):
        cutoff = Config.DEFAULT_CUTOFFS.get(round_name, 70)
        score = round_scores.get(round_name)
        completed = score is not None
        passed = float(score) >= cutoff if completed else False

        if idx == 0:
            status = "completed" if completed else "unlocked"
        else:
            if completed:
                status = "completed"
            elif previous_passed:
                status = "unlocked"
            else:
                status = "locked"

        rounds_data.append({
            "round_id": round_name,
            "round_index": idx + 1,
            "status": status,
            "score": score,
            "cutoff": cutoff,
            "passed": passed
        })

        if not passed:
            previous_passed = False

    return {
        "user_id": user_id,
        "track": track,
        "rounds": rounds_data
    }
