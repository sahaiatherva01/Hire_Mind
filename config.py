import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("HIREMIND_SECRET_KEY") or os.environ.get("SECRET_KEY", "hiremind-secret-key-2026")
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    PORT = int(os.environ.get("PORT", 5001))

    # Gemini AI model pinning (config.py is single source of truth)
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    EMBEDDING_MODEL = "text-embedding-004"

    # Supabase credentials (optional; falls back to local JSON vector store if unset)
    SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("DATABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

    @classmethod
    def log_env_status(cls):
        """Logs environment status on startup without exposing secret values."""
        gemini_ok = bool(cls.GEMINI_API_KEY and not cls.GEMINI_API_KEY.startswith("your_"))
        supabase_url_ok = bool(cls.SUPABASE_URL and not cls.SUPABASE_URL.startswith("your_"))
        supabase_key_ok = bool(cls.SUPABASE_KEY and not cls.SUPABASE_KEY.startswith("your_"))
        print("[Config] Environment Credentials Status:")
        print(f"  • GEMINI_API_KEY: {'LOADED' if gemini_ok else 'NOT CONFIGURED (offline mode)'}")
        print(f"  • GEMINI_MODEL:   {cls.DEFAULT_MODEL}")
        print(f"  • SUPABASE_URL:   {'LOADED' if supabase_url_ok else 'NOT CONFIGURED (local JSON mode)'}")
        print(f"  • SUPABASE_KEY:   {'LOADED' if supabase_key_ok else 'NOT CONFIGURED (local JSON mode)'}")
        print(f"  • FLASK_DEBUG:    {cls.DEBUG}")

    # Storage paths
    DATA_DIR = BASE_DIR / "db" / "data"
    LOCAL_DB_PATH = DATA_DIR / "local_db.json"
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Knowledge Base file sources
    KB_INTERVIEW_QUESTIONS_PATH = DATA_DIR / "seed_interview_questions.json"
    KB_SKILLS_TAXONOMY_PATH = DATA_DIR / "seed_skills_taxonomy.json"
    KB_JD_CORPUS_PATH = DATA_DIR / "seed_jd_corpus.json"
    KB_RESUME_BEST_PRACTICES_PATH = DATA_DIR / "seed_resume_best_practices.json"
    KB_COMPANY_INTERVIEW_STYLE_PATH = DATA_DIR / "seed_company_interview_style.json"

    # Simulation round order
    ROUND_ORDER = [
        "resume_screening",
        "aptitude",
        "dsa",
        "technical",
        "project_defense",
        "hr",
    ]

    # Simulation progression cutoffs (0-100 scale)
    DEFAULT_CUTOFFS = {
        "resume_screening": 70,
        "aptitude": 65,
        "dsa": 70,
        "technical": 70,
        "project_defense": 75,
        "hr": 70,
    }

    # Readiness score aggregation weights
    READINESS_WEIGHTS = {
        "resume_screening": 0.20,
        "aptitude": 0.15,
        "dsa": 0.25,
        "technical": 0.20,
        "project_defense": 0.10,
        "hr": 0.10,
    }
