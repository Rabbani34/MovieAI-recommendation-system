from flask import (render_template, request, jsonify,
                   session, redirect, url_for, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from .model import MovieRecommender, get_movie_poster
from .database import (init_db, get_user_by_username, get_user_by_email,
                        create_user, get_user_by_id, set_rating,
                        get_user_ratings, delete_rating,
                        toggle_watchlist, get_watchlist)

recommender = MovieRecommender()
init_db()

# ── Auth helpers ──────────────────────────────────────────────────────────────
def current_user():
    uid = session.get("user_id")
    return get_user_by_id(uid) if uid else None

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def register_routes(app):

    # ── inject current_user into every template ───────────────────────────────
    @app.context_processor
    def inject_user():
        return {"current_user": current_user()}

    # ══════════════════════════════════════════════════════════════════════════
    #   HOME
    # ══════════════════════════════════════════════════════════════════════════
    @app.route("/", methods=["GET", "POST"])
    def home():
        recommendations  = []
        genre_results    = []
        for_you          = []
        query            = ""
        genre_query      = ""
        min_year         = request.args.get("min_year") or request.form.get("min_year")
        max_year         = request.args.get("max_year") or request.form.get("max_year")
        min_rating_filter= request.args.get("min_rating") or request.form.get("min_rating")

        if request.method == "POST":
            query       = request.form.get("movie_title", "").strip()
            genre_query = request.form.get("genre_name",  "").strip()
        else:
            genre_query = (request.args.get("genre_name","") or request.args.get("genre","")).strip()

        if query:
            recommendations = recommender.recommend(query)

        if genre_query:
            genre_results = recommender.search_by_genre(
                genre_query,
                min_year=min_year, max_year=max_year, min_rating=min_rating_filter
            )

        # Personalised section for logged-in users
        user = current_user()
        if user and not query and not genre_query:
            ratings = get_user_ratings(user["id"])
            for_you = recommender.get_personalized_recommendations(ratings, top_n=12)

        # Get user's rating dict for rendering stars
        user_rating_map = {}
        if user:
            for r in get_user_ratings(user["id"]):
                user_rating_map[r["movie_title"]] = r["rating"]

        top_movies = recommender.get_top_movies(n=20)

        return render_template(
            "recommend.html",
            recommendations=recommendations,
            query=query,
            genre_results=genre_results,
            genre_query=genre_query,
            top_movies=top_movies,
            for_you=for_you,
            user_rating_map=user_rating_map,
            min_year=min_year or 1900,
            max_year=max_year or 2024,
        )

    # ══════════════════════════════════════════════════════════════════════════
    #   MOVIE DETAIL PAGE
    # ══════════════════════════════════════════════════════════════════════════
    @app.route("/movie")
    def movie_detail():
        title = request.args.get("title", "").strip()
        if not title:
            return redirect(url_for("home"))
        movie = recommender.get_movie_detail(title)
        if not movie:
            flash(f'Movie "{title}" not found.', "error")
            return redirect(url_for("home"))
        user = current_user()
        user_rating = 0
        if user:
            for r in get_user_ratings(user["id"]):
                if r["movie_title"] == movie["title"]:
                    user_rating = r["rating"]
                    break
        return render_template("movie_detail.html", movie=movie, user_rating=user_rating)

    # ══════════════════════════════════════════════════════════════════════════
    #   AUTH ROUTES
    # ══════════════════════════════════════════════════════════════════════════
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user():
            return redirect(url_for("home"))
        error = None
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user     = get_user_by_username(username)
            if not user or not check_password_hash(user["password_hash"], password):
                error = "Invalid username or password."
            else:
                session["user_id"] = user["id"]
                flash(f"Welcome back, {user['username']}! 🎬", "success")
                return redirect(url_for("home"))
        return render_template("login.html", mode="login", error=error)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user():
            return redirect(url_for("home"))
        error = None
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email    = request.form.get("email",    "").strip()
            password = request.form.get("password", "")
            confirm  = request.form.get("confirm",  "")
            if len(username) < 3:
                error = "Username must be at least 3 characters."
            elif password != confirm:
                error = "Passwords do not match."
            elif len(password) < 6:
                error = "Password must be at least 6 characters."
            elif get_user_by_username(username):
                error = "Username already taken."
            elif get_user_by_email(email):
                error = "Email already registered."
            else:
                create_user(username, email, generate_password_hash(password))
                user = get_user_by_username(username)
                session["user_id"] = user["id"]
                flash(f"Account created! Welcome, {username} 🎉", "success")
                return redirect(url_for("home"))
        return render_template("login.html", mode="register", error=error)

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You've been logged out.", "info")
        return redirect(url_for("home"))

    # ══════════════════════════════════════════════════════════════════════════
    #   PROFILE
    # ══════════════════════════════════════════════════════════════════════════
    @app.route("/profile")
    @login_required
    def profile():
        user     = current_user()
        ratings  = get_user_ratings(user["id"])
        watchlist= get_watchlist(user["id"])
        return render_template("profile.html", user=user, ratings=ratings, watchlist=watchlist)

    # ══════════════════════════════════════════════════════════════════════════
    #   JSON APIs
    # ══════════════════════════════════════════════════════════════════════════
    @app.route("/api/autocomplete")
    def autocomplete():
        q = request.args.get("q", "").strip()
        return jsonify(recommender.autocomplete(q, top_n=8))

    @app.route("/api/poster")
    def poster_api():
        title = request.args.get("title", "")
        return jsonify({"url": get_movie_poster(title)})

    @app.route("/api/rate", methods=["POST"])
    def rate_movie():
        user = current_user()
        if not user:
            return jsonify({"error": "login_required"}), 401
        data   = request.get_json()
        title  = (data.get("title")  or "").strip()
        poster = (data.get("poster") or "")
        genres = (data.get("genres") or "")
        rating = float(data.get("rating", 0))
        if not title or not (0.5 <= rating <= 5.0):
            return jsonify({"error": "invalid"}), 400
        set_rating(user["id"], title, poster, genres, rating)
        return jsonify({"ok": True, "rating": rating})

    @app.route("/api/rate/delete", methods=["POST"])
    def delete_rating_api():
        user = current_user()
        if not user:
            return jsonify({"error": "login_required"}), 401
        data  = request.get_json()
        title = (data.get("title") or "").strip()
        delete_rating(user["id"], title)
        return jsonify({"ok": True})

    @app.route("/api/watchlist/toggle", methods=["POST"])
    def toggle_wl_api():
        user = current_user()
        if not user:
            return jsonify({"error": "login_required"}), 401
        data   = request.get_json()
        title  = (data.get("title")  or "").strip()
        poster = (data.get("poster") or "")
        genres = (data.get("genres") or "")
        added  = toggle_watchlist(user["id"], title, poster, genres)
        return jsonify({"ok": True, "added": added})

    @app.route("/api/watchlist")
    def get_wl_api():
        user = current_user()
        if not user:
            return jsonify([])
        return jsonify(get_watchlist(user["id"]))
