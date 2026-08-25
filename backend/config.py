"""
HireMind — Configuration

All cutoffs, round order, and scoring weights live here so the backend
(not the frontend) is the single source of truth for round-progression logic.
"""
import os


class Config:
    # --- Core Flask ---
    SECRET_KEY = os.environ.get("HIREMIND_SECRET_KEY", "dev-secret-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"

    # --- Supabase ---
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

    # --- Round order (drives lock/unlock progression in Simulation Mode) ---
    ROUND_ORDER = [
        "resume_screening",
        "aptitude",
        "dsa",
        "technical",
        "project_defense",
        "hr",
    ]

    # --- Cutoffs per round (percentage, 0-100). Configurable per "company track" later. ---
    DEFAULT_CUTOFFS = {
        "resume_screening": 60,
        "aptitude": 70,
        "dsa": 75,
        "technical": 70,
        "project_defense": 75,
        "hr": 70,
    }

    # --- Company-specific cutoff tracks (Phase 16 groundwork) ---
    COMPANY_TRACKS = {
        "default": DEFAULT_CUTOFFS,
        "amazon": {
            "resume_screening": 65,
            "aptitude": 75,
            "dsa": 80,
            "technical": 75,
            "project_defense": 75,
            "hr": 70,
        },
        "startup": {
            "resume_screening": 50,
            "aptitude": 60,
            "dsa": 65,
            "technical": 65,
            "project_defense": 70,
            "hr": 65,
        },
    }

    # --- Scoring weights (Section 9 of the spec) ---
    SCORING_WEIGHTS = {
        "aptitude": {"accuracy": 0.60, "speed": 0.20, "difficulty": 0.20},
        "dsa": {"correctness": 0.50, "complexity": 0.20, "code_quality": 0.15, "speed": 0.15},
        "technical": {"concept_accuracy": 0.45, "depth": 0.25, "followup_handling": 0.20, "communication": 0.10},
        "project_defense": {"architecture": 0.30, "technical_decisions": 0.30, "problem_solving": 0.25, "communication": 0.15},
        "hr": {"relevance": 0.25, "structure": 0.25, "communication": 0.25, "behavioral_fit": 0.25},
    }
