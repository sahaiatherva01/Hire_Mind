"""
HireMind AI — Unified Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR.parent / "Interview-Simulator" / ".env")
load_dotenv(BASE_DIR.parent / "ResumeLens_AI" / ".env")


class Config:
    # --- Core Flask ---
    SECRET_KEY = os.environ.get("HIREMIND_SECRET_KEY", "hiremind-agentic-rag-secret-key-2026")
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"

    # --- Gemini AI ---
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    # Default model configuration
    PARSER_MODEL = "gemini-2.5-flash-lite"
    DEFAULT_MODEL = "gemini-2.5-flash"
    FALLBACK_MODEL = "gemini-2.5-flash"
    EMBEDDING_MODEL = "text-embedding-004"

    # --- Supabase ---
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

    # --- Storage ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # --- Knowledge Base Collection Paths (for local fallback / seeding) ---
    DATA_DIR = os.path.join(BASE_DIR, "data")
    KB_INTERVIEW_QUESTIONS_PATH = os.path.join(DATA_DIR, "seed_interview_questions.json")
    KB_SKILLS_TAXONOMY_PATH = os.path.join(DATA_DIR, "seed_skills_taxonomy.json")
    KB_JD_CORPUS_PATH = os.path.join(DATA_DIR, "seed_jd_corpus.json")
    KB_RESUME_BEST_PRACTICES_PATH = os.path.join(DATA_DIR, "seed_resume_best_practices.json")
    KB_COMPANY_INTERVIEW_STYLE_PATH = os.path.join(DATA_DIR, "seed_company_interview_style.json")
    LOCAL_DB_PATH = os.path.join(DATA_DIR, "local_db.json")

    # --- Round Progression Order (Simulation Mode) ---
    ROUND_ORDER = [
        "resume_screening",
        "aptitude",
        "dsa",
        "technical",
        "project_defense",
        "hr",
    ]

    # --- Cutoffs per round (0-100) ---
    DEFAULT_CUTOFFS = {
        "resume_screening": 60,
        "aptitude": 70,
        "dsa": 75,
        "technical": 70,
        "project_defense": 75,
        "hr": 70,
    }

    # --- Company-specific Cutoff Tracks ---
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

    # --- Scoring Weights ---
    SCORING_WEIGHTS = {
        "aptitude": {"accuracy": 0.60, "speed": 0.20, "difficulty": 0.20},
        "dsa": {"correctness": 0.50, "complexity": 0.20, "code_quality": 0.15, "speed": 0.15},
        "technical": {"concept_accuracy": 0.45, "depth": 0.25, "followup_handling": 0.20, "communication": 0.10},
        "project_defense": {"architecture": 0.30, "technical_decisions": 0.30, "problem_solving": 0.25, "communication": 0.15},
        "hr": {"relevance": 0.25, "structure": 0.25, "communication": 0.25, "behavioral_fit": 0.25},
    }

    # --- Overall Readiness Weights (0-100 aggregated) ---
    READINESS_WEIGHTS = {
        "resume_screening": 0.15,
        "aptitude": 0.20,
        "dsa": 0.30,
        "technical": 0.15,
        "project_defense": 0.10,
        "hr": 0.10,
    }
