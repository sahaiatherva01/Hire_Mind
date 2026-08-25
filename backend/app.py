import os

from flask import Flask, send_from_directory

from config import Config
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.aptitude import aptitude_bp
from routes.dsa import dsa_bp

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(aptitude_bp)
    app.register_blueprint(dsa_bp)

    # --- Serve the plain HTML/CSS/JS frontend (no build step, per spec: no React) ---
    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/<path:path>")
    def static_files(path):
        full_path = os.path.join(FRONTEND_DIR, path)
        if os.path.isfile(full_path):
            return send_from_directory(FRONTEND_DIR, path)
        # Fallback for clean routes like /dashboard -> /dashboard.html
        if os.path.isfile(full_path + ".html"):
            return send_from_directory(FRONTEND_DIR, path + ".html")
        return send_from_directory(FRONTEND_DIR, "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
