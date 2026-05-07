import os
from flask import Flask
from recommender.routes import register_routes

def create_app():
    app = Flask(
        __name__,
        template_folder="recommender/templates",
        static_folder="recommender/static"
    )
    # Use environment variable in production, fallback for dev
    app.secret_key = os.environ.get("SECRET_KEY", "movieai-dev-secret-change-in-prod")
    register_routes(app)
    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
