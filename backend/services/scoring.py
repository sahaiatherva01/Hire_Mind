"""
HireMind AI — Scoring Service
Implements the 105-point ATS+ rubric, per-round weighted scoring, and end-to-end Candidate Readiness calculation.
"""
from typing import Dict, Any, List
from config import Config


# ---------------------------------------------------------
# 1. ATS+ 105-Point Rubric (Normalized to 0-100)
# ---------------------------------------------------------

def calculate_ats_category_scores(
    profile_data: dict,
    parser_metadata: dict,
    raw_text: str,
    jd_match_data: dict = None
) -> Dict[str, Any]:
    """
    Computes transparent, rubric-based ATS+ scores across 8 categories (105 raw points max).
    Returns category breakdown and overall score normalized to 0-100.
    """
    text_len = len(raw_text or "")
    pages = parser_metadata.get("page_count", 1)

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
        # Generic keyword density and breadth
        skills_count = len(profile_data.get("skill_profile", {}).get("normalized_skills", []))
        keyword = min(20.0, max(5.0, skills_count * 1.2))

    # 4. Content Quality & Strong Verbs (Max 15)
    action_verbs = [
        "architected", "engineered", "spearheaded", "developed", "optimized",
        "implemented", "designed", "streamlined", "automated", "built", "led"
    ]
    raw_lower = raw_text.lower()
    verb_matches = sum(1 for v in action_verbs if v in raw_lower)
    content_quality = min(15.0, max(4.0, verb_matches * 2.5))

    # 5. Skills Representation (Max 10)
    categorized = profile_data.get("skill_profile", {}).get("categorized_skills", {})
    categories_filled = len([c for c, s in categorized.items() if s])
    skills_rep = min(10.0, max(3.0, categories_filled * 2.5))

    # 6. Quantified Impact & Metrics (Max 10)
    import re
    metrics_patterns = [
        r'\b\d+%',
        r'\$\d+',
        r'\b\d+x\b',
        r'\b\d+\s*(?:ms|seconds|minutes|hours|days|k|m|users|requests|rpm|qps)\b'
    ]
    total_metrics = sum(len(re.findall(p, raw_text, re.IGNORECASE)) for p in metrics_patterns)
    quantified = min(10.0, max(2.0, total_metrics * 2.0))

    # 7. Section Completeness (Max 10)
    p_info = profile_data.get("personal_info", {})
    has_contact = bool(p_info.get("email") and p_info.get("phone"))
    completeness = 10.0
    if not has_contact:
        completeness -= 3.0
    if not profile_data.get("skills"):
        completeness -= 3.0
    if not exp and not proj:
        completeness -= 4.0
    completeness = max(0.0, min(10.0, completeness))

    # 8. Readability & Consistency (Max 5)
    readability = 5.0
    if text_len > 15000:
        readability -= 1.5
    readability = max(0.0, min(5.0, readability))

    # Total raw score out of 105, normalized to 100
    raw_total = (
        ats_comp + structure + keyword + content_quality +
        skills_rep + quantified + completeness + readability
    )
    overall_score = round(min(100.0, (raw_total / 105.0) * 100.0), 1)

    return {
        "ats_compatibility": round(ats_comp, 1),
        "resume_structure": round(structure, 1),
        "keyword_relevance": round(keyword, 1),
        "content_quality": round(content_quality, 1),
        "skills_representation": round(skills_rep, 1),
        "quantified_impact": round(quantified, 1),
        "completeness": round(completeness, 1),
        "readability_consistency": round(readability, 1),
        "raw_total": round(raw_total, 1),
        "overall_score": overall_score
    }


# ---------------------------------------------------------
# 2. Round-Specific Weighted Scoring Formulas
# ---------------------------------------------------------

def score_aptitude_round(correct_count: int, total_questions: int, time_taken_sec: int, max_time_sec: int = 900) -> Dict[str, Any]:
    weights = Config.SCORING_WEIGHTS["aptitude"]
    accuracy = (correct_count / max(1, total_questions)) * 100.0
    speed = max(0.0, min(100.0, (1.0 - (time_taken_sec / max(1, max_time_sec))) * 100.0 + 20.0))
    difficulty_score = min(100.0, accuracy * 1.05)

    final_score = round(
        (accuracy * weights["accuracy"]) +
        (speed * weights["speed"]) +
        (difficulty_score * weights["difficulty"]),
        1
    )
    return {
        "score": min(100.0, max(0.0, final_score)),
        "accuracy": round(accuracy, 1),
        "speed": round(speed, 1),
        "difficulty": round(difficulty_score, 1),
        "passed": final_score >= Config.DEFAULT_CUTOFFS["aptitude"]
    }


def score_dsa_round(tests_passed: int, total_tests: int, runtime_ms: float, code_lines: int, time_taken_sec: int, max_time_sec: int = 1500) -> Dict[str, Any]:
    weights = Config.SCORING_WEIGHTS["dsa"]
    correctness = (tests_passed / max(1, total_tests)) * 100.0
    complexity = 90.0 if runtime_ms < 50 else (75.0 if runtime_ms < 200 else 60.0)
    code_quality = 90.0 if (10 <= code_lines <= 80) else 70.0
    speed = max(0.0, min(100.0, (1.0 - (time_taken_sec / max(1, max_time_sec))) * 100.0 + 10.0))

    final_score = round(
        (correctness * weights["correctness"]) +
        (complexity * weights["complexity"]) +
        (code_quality * weights["code_quality"]) +
        (speed * weights["speed"]),
        1
    )
    return {
        "score": min(100.0, max(0.0, final_score)),
        "correctness": round(correctness, 1),
        "complexity": round(complexity, 1),
        "code_quality": round(code_quality, 1),
        "speed": round(speed, 1),
        "passed": final_score >= Config.DEFAULT_CUTOFFS["dsa"]
    }


def score_interview_round(round_type: str, subscores: Dict[str, float]) -> Dict[str, Any]:
    weights = Config.SCORING_WEIGHTS.get(round_type, {
        "concept_accuracy": 0.45, "depth": 0.25, "followup_handling": 0.20, "communication": 0.10
    })
    total = sum(subscores.get(k, 70.0) * w for k, w in weights.items())
    final_score = round(total, 1)
    cutoff = Config.DEFAULT_CUTOFFS.get(round_type, 70)
    return {
        "score": min(100.0, max(0.0, final_score)),
        "breakdown": subscores,
        "cutoff": cutoff,
        "passed": final_score >= cutoff
    }


# ---------------------------------------------------------
# 3. Overall Readiness Calculation
# ---------------------------------------------------------

def calculate_readiness_score(round_scores: Dict[str, float]) -> Dict[str, Any]:
    """
    Calculates overall candidate readiness score (0-100) aggregating across all module performances.
    """
    weights = Config.READINESS_WEIGHTS
    total_score = 0.0
    weight_sum = 0.0

    breakdown = {}
    for round_name, weight in weights.items():
        score = round_scores.get(round_name)
        if score is not None:
            total_score += float(score) * weight
            weight_sum += weight
            breakdown[round_name] = round(float(score), 1)
        else:
            breakdown[round_name] = None

    if weight_sum > 0:
        normalized_readiness = round(total_score / weight_sum, 1)
    else:
        normalized_readiness = 0.0

    # Categorize readiness level
    if normalized_readiness >= 80:
        tier = "Ready for Top Tech (Tier 1 / FAANG)"
        status_color = "var(--color-green)"
    elif normalized_readiness >= 65:
        tier = "Competent / Near Ready (Fast-Growth Tech)"
        status_color = "var(--color-amber)"
    else:
        tier = "Developing / Needs Practice"
        status_color = "var(--color-red)"

    return {
        "overall_readiness": normalized_readiness,
        "tier": tier,
        "status_color": status_color,
        "breakdown": breakdown
    }
