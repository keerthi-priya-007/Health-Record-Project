"""Flask application factory."""
import os
from flask import Flask
from config import Config
from .database import init_db
from .routes import main_bp, api_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    init_db(app)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.errorhandler(413)
    def file_too_large(_error):
        from flask import jsonify
        return jsonify({"error": "File is too large. Maximum size is 10 MB."}), 413

    return app
