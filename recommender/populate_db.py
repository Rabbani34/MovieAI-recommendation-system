"""
Run this ONCE to pre-populate the movie cache with TMDb's top movies.
Usage:  python populate_db.py
It fetches ~5000 movies (popular + top-rated + by genre) and saves them to
tmdb_movies.db so the app never needs to re-fetch them.
"""
import sqlite3, requests, time, os

API_KEY  = "e547e17d4e91f3e62a571655cd1ccaff"
DB_PATH  = "tmdb_movies.db"
BASE_URL = "https://api.themoviedb.org/3"

GENRE_IDS = {
    "Action":28,"Adventure":12,"Animation":16,"Comedy":35,
    "Crime":80,"Documentary":99,"Drama":18,"Fantasy":14,
    "Horror":27,"Mystery":9648,"Romance":10749,
    "Sci-Fi":878,"Thriller":53,"Western":37,
}

def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS movies (
            id            INTEGER PRIMARY KEY,
            title         TEXT NOT NULL,
            overview      TEXT DEFAULT '',
            genres        TEXT DEFAULT '',
            release_year  INTEGER DEFAULT 0,
            vote_average  REAL DEFAULT 0,
            popularity    REAL DEFAULT 0,
            poster_url    TEXT DEFAULT '',
            backdrop_url  TEXT DEFAULT '',
            imdb_id       TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_title  ON movies(title);
        CREATE INDEX IF NOT EXISTS idx_genres ON movies(genres);
        CREATE INDEX IF NOT EXISTS idx_vote   ON movies(vote_average DESC);
    """)
    conn.commit()

def upsert_movie(conn, m):
    poster   = f"https://image.tmdb.org/t/p/w342{m['poster_path']}"   if m.get("poster_path")   else ""
    backdrop = f"https://image.tmdb.org/t/p/w1280{m['backdrop_path']}" if m.get("backdrop_path") else ""
    year     = int((m.get("release_date") or "0")[:4] or 0)
    genres   = "|".join(m.get("genre_names", []))
    conn.execute("""
        INSERT INTO movies (id,title,overview,genres,release_year,vote_average,popularity,poster_url,backdrop_url)
        VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title, overview=excluded.overview,
            genres=excluded.genres, release_year=excluded.release_year,
            vote_average=excluded.vote_average, popularity=excluded.popularity,
            poster_url=excluded.poster_url, backdrop_url=excluded.backdrop_url
    """, (m["id"], m["title"], m.get("overview",""), genres,
          year, m.get("vote_average",0), m.get("popularity",0), poster, backdrop))

def fetch_genre_names(sess):
    r = sess.get(f"{BASE_URL}/genre/movie/list?api_key={API_KEY}").json()
    return {g["id"]: g["name"] for g in r.get("genres",[])}

def fetch_pages(sess, endpoint, pages, genre_map):
    movies = {}
    for page in range(1, pages+1):
        try:
            r = sess.get(f"{BASE_URL}/{endpoint}?api_key={API_KEY}&page={page}&language=en-US").json()
            for m in r.get("results", []):
                if m.get("poster_path") and m.get("vote_count",0) > 20:
                    m["genre_names"] = [genre_map.get(gid,"") for gid in m.get("genre_ids",[])]
                    movies[m["id"]] = m
            print(f"  {endpoint} page {page}/{pages} — {len(movies)} total", end="\r")
            time.sleep(0.12)
        except Exception as e:
            print(f"\n  Error page {page}: {e}")
    print()
    return movies

def fetch_by_genre(sess, genre_id, genre_name, pages, genre_map):
    movies = {}
    for page in range(1, pages+1):
        try:
            r = sess.get(
                f"{BASE_URL}/discover/movie?api_key={API_KEY}"
                f"&with_genres={genre_id}&sort_by=vote_average.desc"
                f"&vote_count.gte=100&page={page}&language=en-US"
            ).json()
            for m in r.get("results", []):
                if m.get("poster_path"):
                    m["genre_names"] = [genre_map.get(gid,"") for gid in m.get("genre_ids",[])]
                    movies[m["id"]] = m
            print(f"  genre={genre_name} page {page}/{pages} — {len(movies)}", end="\r")
            time.sleep(0.12)
        except Exception as e:
            print(f"\n  Error: {e}")
    print()
    return movies

def main():
    print("=" * 55)
    print("  MovieAI TMDb Pre-populator")
    print("=" * 55)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    sess = requests.Session()
    sess.headers.update({"Accept": "application/json"})

    print("\n[1/4] Fetching genre list...")
    genre_map = fetch_genre_names(sess)

    all_movies = {}

    print("\n[2/4] Fetching popular movies (50 pages = ~1000 movies)...")
    all_movies.update(fetch_pages(sess, "movie/popular", 50, genre_map))

    print("\n[3/4] Fetching top-rated movies (50 pages = ~1000 movies)...")
    all_movies.update(fetch_pages(sess, "movie/top_rated", 50, genre_map))

    print("\n[4/4] Fetching movies by genre (15 pages each)...")
    for gname, gid in GENRE_IDS.items():
        print(f"  → {gname}")
        all_movies.update(fetch_by_genre(sess, gid, gname, 15, genre_map))

    print(f"\nInserting {len(all_movies)} unique movies into {DB_PATH}...")
    for m in all_movies.values():
        upsert_movie(conn, m)
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    print(f"\n✅ Done! {total} movies with posters stored in '{DB_PATH}'")
    print("   Restart your Flask app — genre browsing and search now use this DB.")
    conn.close()

if __name__ == "__main__":
    main()
