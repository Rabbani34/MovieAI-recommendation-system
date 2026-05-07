"""
MovieAI — SQLite database helpers
Tables: users, ratings, watchlist
"""
import sqlite3, os
from contextlib import contextmanager

DB_PATH = "movieai.db"

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS ratings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                movie_title TEXT NOT NULL,
                poster      TEXT DEFAULT '',
                genres      TEXT DEFAULT '',
                rating      REAL NOT NULL CHECK(rating BETWEEN 0.5 AND 5.0),
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, movie_title)
            );
            CREATE TABLE IF NOT EXISTS watchlist (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                movie_title TEXT NOT NULL,
                poster      TEXT DEFAULT '',
                genres      TEXT DEFAULT '',
                added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, movie_title)
            );
        """)

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ── User helpers ──────────────────────────────────────────────────────────────
def create_user(username, email, password_hash):
    with get_db() as db:
        db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?,?,?)",
            (username, email, password_hash)
        )

def get_user_by_id(uid):
    with get_db() as db:
        r = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return dict(r) if r else None

def get_user_by_username(u):
    with get_db() as db:
        r = db.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        return dict(r) if r else None

def get_user_by_email(e):
    with get_db() as db:
        r = db.execute("SELECT * FROM users WHERE email=?", (e,)).fetchone()
        return dict(r) if r else None

# ── Rating helpers ────────────────────────────────────────────────────────────
def set_rating(user_id, movie_title, poster, genres, rating):
    with get_db() as db:
        db.execute("""
            INSERT INTO ratings (user_id, movie_title, poster, genres, rating)
            VALUES (?,?,?,?,?)
            ON CONFLICT(user_id, movie_title)
            DO UPDATE SET rating=excluded.rating, created_at=CURRENT_TIMESTAMP
        """, (user_id, movie_title, poster, genres, rating))

def get_user_ratings(user_id):
    with get_db() as db:
        rows = db.execute(
            "SELECT movie_title, poster, genres, rating FROM ratings WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]

def delete_rating(user_id, movie_title):
    with get_db() as db:
        db.execute("DELETE FROM ratings WHERE user_id=? AND movie_title=?", (user_id, movie_title))

# ── Watchlist helpers ─────────────────────────────────────────────────────────
def toggle_watchlist(user_id, movie_title, poster, genres):
    with get_db() as db:
        exists = db.execute(
            "SELECT 1 FROM watchlist WHERE user_id=? AND movie_title=?",
            (user_id, movie_title)
        ).fetchone()
        if exists:
            db.execute("DELETE FROM watchlist WHERE user_id=? AND movie_title=?", (user_id, movie_title))
            return False
        else:
            db.execute(
                "INSERT OR IGNORE INTO watchlist (user_id, movie_title, poster, genres) VALUES (?,?,?,?)",
                (user_id, movie_title, poster, genres)
            )
            return True

def get_watchlist(user_id):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM watchlist WHERE user_id=? ORDER BY added_at DESC",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
