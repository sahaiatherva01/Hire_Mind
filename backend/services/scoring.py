"""
Scoring Engine — each round gets its own formula (spec section 9).
Only Aptitude and DSA are fully wired for MVP1; the interview-round
scorers (technical/project/HR) are stubbed for the voice-interview phase.
"""
from config import Config


def score_aptitude(questions, answers, time_taken_seconds, time_limit_seconds):
    """
    accuracy 60% | speed 20% | difficulty 20%
    - accuracy: % of questions answered correctly
    - speed: reward for finishing under time, scaled 0-100 (no penalty for using full time)
    - difficulty: average difficulty weight of correctly-answered questions
    """
    weights = Config.SCORING_WEIGHTS["aptitude"]
    total = len(questions)
    if total == 0:
        return _empty_result()

    correct = 0
    difficulty_points = 0
    difficulty_map = {"easy": 1, "medium": 2, "hard": 3}
    max_difficulty = 3
    per_question = []

    for q in questions:
        qid = q["id"]
        given = answers.get(str(qid))
        is_correct = given is not None and given == q["correct_option"]
        if is_correct:
            correct += 1
            difficulty_points += difficulty_map.get(q.get("difficulty", "medium"), 2)
        per_question.append({
            "id": qid,
            "correct": is_correct,
            "given_answer": given,
            "correct_answer": q["correct_option"],
            "explanation": q.get("explanation", ""),
            "topic": q.get("topic", ""),
        })

    accuracy_pct = (correct / total) * 100

    time_ratio = min(time_taken_seconds / time_limit_seconds, 1.0) if time_limit_seconds else 1.0
    speed_pct = max(0, (1 - time_ratio)) * 100 + (30 if time_ratio < 1 else 0)
    speed_pct = min(speed_pct, 100)

    difficulty_pct = (difficulty_points / (correct * max_difficulty) * 100) if correct else 0

    final_score = (
        accuracy_pct * weights["accuracy"]
        + speed_pct * weights["speed"]
        + difficulty_pct * weights["difficulty"]
    )

    weak_topics = _weak_topics(per_question)

    return {
        "score": round(final_score, 1),
        "accuracy": round(accuracy_pct, 1),
        "speed": round(speed_pct, 1),
        "difficulty": round(difficulty_pct, 1),
        "correct_count": correct,
        "total_questions": total,
        "time_taken_seconds": time_taken_seconds,
        "per_question": per_question,
        "weak_topics": weak_topics,
    }


def _weak_topics(per_question):
    topic_stats = {}
    for pq in per_question:
        t = pq["topic"] or "general"
        topic_stats.setdefault(t, {"correct": 0, "total": 0})
        topic_stats[t]["total"] += 1
        if pq["correct"]:
            topic_stats[t]["correct"] += 1
    weak = [
        t for t, s in topic_stats.items()
        if s["total"] > 0 and (s["correct"] / s["total"]) < 0.6
    ]
    return weak


def score_dsa(test_results, complexity_rating, code_quality_rating, time_taken_seconds, time_limit_seconds):
    """
    correctness 50% | complexity 20% | code_quality 15% | speed 15%
    test_results: list of {passed: bool, hidden: bool}
    complexity_rating / code_quality_rating: 0-100, from static heuristics or AI review
    """
    weights = Config.SCORING_WEIGHTS["dsa"]
    total_tests = len(test_results)
    passed = sum(1 for t in test_results if t["passed"])
    correctness_pct = (passed / total_tests * 100) if total_tests else 0

    time_ratio = min(time_taken_seconds / time_limit_seconds, 1.0) if time_limit_seconds else 1.0
    speed_pct = max(0, (1 - time_ratio)) * 100

    final_score = (
        correctness_pct * weights["correctness"]
        + complexity_rating * weights["complexity"]
        + code_quality_rating * weights["code_quality"]
        + speed_pct * weights["speed"]
    )

    return {
        "score": round(final_score, 1),
        "correctness": round(correctness_pct, 1),
        "complexity": round(complexity_rating, 1),
        "code_quality": round(code_quality_rating, 1),
        "speed": round(speed_pct, 1),
        "tests_passed": passed,
        "tests_total": total_tests,
    }


def _empty_result():
    return {
        "score": 0, "accuracy": 0, "speed": 0, "difficulty": 0,
        "correct_count": 0, "total_questions": 0, "time_taken_seconds": 0,
        "per_question": [], "weak_topics": [],
    }
