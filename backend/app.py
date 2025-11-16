from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# Blueprints
from routes.sanitize import sanitize_bp
from routes.context import context_bp
from routes.llm import llm_bp
from routes.output_filter import output_filter_bp
from routes.final import final_bp
from utils.logger import logs_bp


def create_app():
    app = Flask(__name__)
    # Allow Vite dev server
    CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"], "supports_credentials": True}})

    # Health
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    # Register blueprints
    app.register_blueprint(sanitize_bp)
    app.register_blueprint(context_bp)
    app.register_blueprint(llm_bp)
    app.register_blueprint(output_filter_bp)
    app.register_blueprint(final_bp)
    app.register_blueprint(logs_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
