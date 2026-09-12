"""
HireMind AI — Unified Backend Application
"""
import os
import sys
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import Config
from services.supabase_client import supabase_service
from services.rag_service import get_gemini_client

# Import Blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.resume import resume_bp
from routes.interview import interview_bp
from routes.aptitude import aptitude_bp
from routes.dsa import dsa_bp
from routes.recruit import recruit_bp

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)
    CORS(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(aptitude_bp)
    app.register_blueprint(dsa_bp)
    app.register_blueprint(recruit_bp)

    @app.route("/api/health", methods=["GET"])
    def health_check():
        supabase_ok = supabase_service.is_configured()
        gemini_ok = get_gemini_client() is not None
        return jsonify({
            "status": "healthy",
            "supabase_configured": supabase_ok,
            "gemini_configured": gemini_ok,
            "vector_rag_active": True,
            "architecture": "multi_agent_rag_orchestrated",
            "modules": ["Module A: Resume Intelligence", "Module B: Interview Simulator", "Module C: Recruiter Batch", "Module D: Unified Readiness"]
        }), 200

    # --- Serve Frontend SPA & Static Files ---
    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/<path:path>")
    def serve_static(path):
        full_path = os.path.join(FRONTEND_DIR, path)
        if os.path.isfile(full_path):
            return send_from_directory(FRONTEND_DIR, path)
        # Fallback for clean routes e.g. /dashboard -> /dashboard.html, /resume -> /resume.html
        if os.path.isfile(full_path + ".html"):
            return send_from_directory(FRONTEND_DIR, path + ".html")
        return send_from_directory(FRONTEND_DIR, "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"=================================================")
    print(f"🚀 HireMind AI Platform running on http://127.0.0.1:{port}")
    print(f"=================================================")
    app.run(host="0.0.0.0", port=port, debug=Config.DEBUG)
