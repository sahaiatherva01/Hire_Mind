import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

from config import Config
from db.client import db_client
from core.gemini import get_gemini_client

# Blueprints
from resume.routes import resume_bp
from interview.routes import interview_bp
from recruit.routes import recruit_bp
from dashboard.routes import dashboard_bp
from auth.routes import auth_bp

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


def create_app():
    Config.log_env_status()
    app = Flask(__name__, static_folder=str(STATIC_DIR))
    app.config.from_object(Config)
    CORS(app)

    # Register API Blueprints
    app.register_blueprint(resume_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(recruit_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)

    @app.route("/api/health", methods=["GET"])
    def health():
        supabase_ok = db_client.is_configured()
        gemini_ok = get_gemini_client() is not None
        schema_info = db_client.check_remote_schema()
        return jsonify({
            "status": "healthy",
            "supabase_connected": supabase_ok,
            "gemini_active": gemini_ok,
            "gemini_model": Config.DEFAULT_MODEL,
            "schema_status": schema_info.get("status"),
            "schema_message": schema_info.get("message"),
            "architecture": "multi_agent_rag_orchestrated",
            "modules": {
                "resume": "Module A: Resume Intelligence & ATS+ 105pt",
                "interview": "Module B: IntervAI & DSA Sandbox",
                "recruit": "Module C: Recruiter Semantic Batch & Ranking",
                "readiness": "Module D: Round Cutoff Authority"
            }
        }), 200

    # Static asset routes (/css/... and /js/...)
    @app.route("/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(STATIC_DIR / "css", filename)

    @app.route("/js/<path:filename>")
    def serve_js(filename):
        return send_from_directory(STATIC_DIR / "js", filename)

    # HTML Page Routes
    @app.route("/")
    def index():
        return send_from_directory(TEMPLATES_DIR, "index.html")

    @app.route("/<path:page>")
    def serve_page(page):
        # Direct static file check
        static_file = STATIC_DIR / page
        if static_file.is_file():
            return send_from_directory(STATIC_DIR, page)

        # Template file check
        target = page.rstrip("/")
        candidates = [
            TEMPLATES_DIR / target,
            TEMPLATES_DIR / f"{target}.html",
            TEMPLATES_DIR / f"{target}/index.html"
        ]
        for c in candidates:
            if c.is_file():
                rel_path = c.relative_to(TEMPLATES_DIR)
                return send_from_directory(TEMPLATES_DIR, str(rel_path))

        return send_from_directory(TEMPLATES_DIR, "index.html")

    return app


app = create_app()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
