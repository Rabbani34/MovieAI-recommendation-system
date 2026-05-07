"""
MovieAI — Full Dataset Integration
====================================
Joins ALL local datasets into one fast SQLite DB:

  ml-32m/movies.csv          → 87k movie titles + genres
  ml-32m/ratings.csv         → 32M ratings → real avg scores per movie
  ml-32m/links.csv           → movieId ↔ tmdbId mapping
  movies_metadata.csv        → poster paths, overviews, budgets (Kaggle)

Result: tmdb_movies.db with 45k+ movies, real ratings, real posters.
Zero API calls. Runs in ~2 minutes.

Download movies_metadata.csv from:
  https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset
Put it in the same folder as run.py, then:
  python build_db_full.py
"""

import sqlite3, os, ast, re, sys
import pandas as pd
import numpy as np

DB_PATH       = "tmdb_movies.db"
POSTER_BASE   = "https://image.tmdb.org/t/p/w342"
BACKDROP_BASE = "https://image.tmdb.org/t/p/w1280"

ML_MOVIES  = "ml-32m/movies.csv"
ML_RATINGS = "ml-32m/ratings.csv"
ML_LINKS   = "ml-32m/links.csv"
KAGGLE_META= "movies_metadata.csv"

# ── DB setup ──────────────────────────────────────────────────────────────────
def init_db(conn):
    conn.execute("DROP TABLE IF EXISTS movies")
    conn.execute("DROP TABLE IF EXISTS movies_fts")
    conn.execute("""
        CREATE TABLE movies (
            id              INTEGER PRIMARY KEY,
            movielens_id    INTEGER DEFAULT 0,
            title           TEXT NOT NULL DEFAULT '',
            original_title  TEXT DEFAULT '',
            overview        TEXT DEFAULT '',
            genres          TEXT DEFAULT '',
            release_year    INTEGER DEFAULT 0,
            vote_average    REAL DEFAULT 0,
            vote_count      INTEGER DEFAULT 0,
            ml_avg_rating   REAL DEFAULT 0,
            ml_rating_count INTEGER DEFAULT 0,
            popularity      REAL DEFAULT 0,
            poster_url      TEXT DEFAULT '',
            backdrop_url    TEXT DEFAULT '',
            imdb_id         TEXT DEFAULT '',
            language        TEXT DEFAULT '',
            runtime         INTEGER DEFAULT 0,
            tagline         TEXT DEFAULT '',
            enriched        INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    for sql in [
        "CREATE INDEX idx_title    ON movies(title)",
        "CREATE INDEX idx_genres   ON movies(genres)",
        "CREATE INDEX idx_vote     ON movies(vote_average)",
        "CREATE INDEX idx_mlrating ON movies(ml_avg_rating)",
        "CREATE INDEX idx_pop      ON movies(popularity)",
        "CREATE INDEX idx_year     ON movies(release_year)",
        "CREATE INDEX idx_mlid     ON movies(movielens_id)",
    ]:
        conn.execute(sql)
    conn.commit()
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE movies_fts
            USING fts5(title, original_title, content='movies', content_rowid='id')
        """)
        conn.commit()
    except Exception as e:
        print(f"  FTS: {e}")
    print("DB schema ready ✓")

# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_genres_json(g):
    try:
        items = ast.literal_eval(str(g))
        return "|".join(i["name"] for i in items if i.get("name"))
    except Exception:
        return ""

def clean_ml_title(t):
    """'Toy Story (1995)' → 'Toy Story'"""
    return re.sub(r"\s*\(\d{4}\)\s*$", "", str(t)).strip()

def extract_year(t):
    m = re.search(r"\((\d{4})\)$", str(t))
    return int(m.group(1)) if m else 0

# ── Step 1: Load MovieLens movies ─────────────────────────────────────────────
def load_movielens_movies():
    print("\n[1/6] Loading ml-32m/movies.csv ...")
    df = pd.read_csv(ML_MOVIES)
    df.drop_duplicates(subset="movieId", inplace=True)
    df["clean_title"] = df["title"].apply(clean_ml_title)
    df["year"]        = df["title"].apply(extract_year)
    df["genres_pipe"] = df["genres"].str.replace("|","|").str.replace("(no genres listed)","")
    print(f"  {len(df):,} movies loaded")
    return df

# ── Step 2: Compute real ratings from 32M rows ────────────────────────────────
def load_ratings():
    print("\n[2/6] Computing ratings from ml-32m/ratings.csv ...")
    print("  (reading 32M rows — takes ~30 seconds)")

    # Read in chunks to avoid memory issues
    chunks = []
    chunk_size = 2_000_000
    total = 0
    for chunk in pd.read_csv(ML_RATINGS, chunksize=chunk_size,
                              usecols=["movieId","rating"]):
        # Only keep rating per movie — aggregate immediately
        agg = chunk.groupby("movieId")["rating"].agg(["sum","count"])
        chunks.append(agg)
        total += len(chunk)
        print(f"  Read {total:,} ratings...", end="\r")

    print(f"\n  Aggregating {total:,} ratings...")
    combined = pd.concat(chunks).groupby(level=0).sum()
    combined["avg_rating"]   = (combined["sum"] / combined["count"]).round(2)
    combined["rating_count"] = combined["count"].astype(int)
    combined = combined[["avg_rating","rating_count"]].reset_index()
    combined.columns = ["movieId","avg_rating","rating_count"]
    print(f"  Computed ratings for {len(combined):,} movies")
    return combined

# ── Step 3: Load links (movieId ↔ tmdbId) ─────────────────────────────────────
def load_links():
    print("\n[3/6] Loading ml-32m/links.csv ...")
    df = pd.read_csv(ML_LINKS)
    df["tmdbId"]  = pd.to_numeric(df["tmdbId"],  errors="coerce")
    df["movieId"] = pd.to_numeric(df["movieId"], errors="coerce")
    df["imdbId"]  = pd.to_numeric(df["imdbId"],  errors="coerce")
    df = df.dropna(subset=["movieId"])
    df["tmdbId"]  = df["tmdbId"].fillna(0).astype(int)
    df["movieId"] = df["movieId"].astype(int)
    print(f"  {len(df):,} links loaded")
    return df

# ── Step 4: Load Kaggle metadata ──────────────────────────────────────────────
def load_kaggle_meta():
    if not os.path.exists(KAGGLE_META):
        print(f"\n⚠️  {KAGGLE_META} not found — posters/overviews will be missing")
        print("   Download from: https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset")
        return None

    print(f"\n[4/6] Loading {KAGGLE_META} ...")
    df = pd.read_csv(KAGGLE_META, low_memory=False)

    # Clean up — some rows have corrupt IDs
    df = df[df["id"].apply(lambda x: str(x).strip().isdigit())]
    df["id"] = df["id"].astype(int)

    # Parse genres from JSON string
    df["genres_parsed"] = df["genres"].apply(parse_genres_json)

    # Build poster/backdrop URLs
    df["poster_url"]   = df["poster_path"].apply(
        lambda p: f"{POSTER_BASE}{p}" if pd.notna(p) and str(p).startswith("/") else ""
    )
    df["backdrop_url"] = df["backdrop_path"].apply(
        lambda p: f"{BACKDROP_BASE}{p}" if pd.notna(p) and str(p).startswith("/") else ""
    )

    df["release_year"] = df["release_date"].apply(
        lambda d: int(str(d)[:4]) if pd.notna(d) and len(str(d)) >= 4 and str(d)[:4].isdigit() else 0
    )
    df["vote_average"] = pd.to_numeric(df["vote_average"], errors="coerce").fillna(0)
    df["vote_count"]   = pd.to_numeric(df["vote_count"],   errors="coerce").fillna(0).astype(int)
    df["popularity"]   = pd.to_numeric(df["popularity"],   errors="coerce").fillna(0)
    df["runtime"]      = pd.to_numeric(df["runtime"],      errors="coerce").fillna(0).astype(int)

    keep = ["id","title","original_title","overview","genres_parsed",
            "release_year","vote_average","vote_count","popularity",
            "poster_url","backdrop_url","original_language",
            "runtime","tagline","imdb_id"]
    df = df[[c for c in keep if c in df.columns]]
    print(f"  {len(df):,} Kaggle movies loaded")
    return df

# ── Step 5: Merge everything ──────────────────────────────────────────────────
def merge_all(ml_movies, ratings, links, kaggle):
    print("\n[5/6] Merging all datasets ...")

    # Start with MovieLens as base (87k movies)
    base = ml_movies.merge(ratings, on="movieId", how="left")
    base = base.merge(links,  on="movieId", how="left")
    base["avg_rating"]   = base["avg_rating"].fillna(7.0)
    base["rating_count"] = base["rating_count"].fillna(0).astype(int)
    base["tmdbId"]       = base["tmdbId"].fillna(0).astype(int)
    print(f"  MovieLens base: {len(base):,} movies")

    if kaggle is not None:
        # Merge Kaggle on tmdbId
        merged = base.merge(
            kaggle, left_on="tmdbId", right_on="id", how="left"
        )

        # For movies matched to Kaggle, use Kaggle data; else use ML data
        def pick(row, kaggle_col, ml_col, default=""):
            val = row.get(kaggle_col)
            if pd.notna(val) and str(val).strip() not in ("","0","nan"):
                return val
            val2 = row.get(ml_col)
            if pd.notna(val2): return val2
            return default

        rows = []
        matched = 0
        for _, row in merged.iterrows():
            has_kaggle = pd.notna(row.get("id")) and row.get("poster_url","") != ""
            if has_kaggle: matched += 1

            # Use real tmdb ID if available, else use movieId as negative
            tmdb_id = int(row.get("id",0) or row.get("tmdbId",0) or 0)
            if tmdb_id == 0:
                tmdb_id = int(row["movieId"]) + 1_000_000  # avoid collision

            # Prefer Kaggle genres (cleaner), fall back to MovieLens
            genres = ""
            if has_kaggle and row.get("genres_parsed",""):
                genres = str(row["genres_parsed"])
            if not genres:
                genres = str(row.get("genres_pipe",""))

            # Best rating: if 1000+ ML ratings, use ML avg; else use TMDb
            ml_count = int(row.get("rating_count",0) or 0)
            ml_avg   = float(row.get("avg_rating",0) or 0)
            tmdb_avg = float(row.get("vote_average",0) or 0)
            best_rating = round(ml_avg if ml_count >= 1000 else (tmdb_avg or ml_avg), 2)

            rows.append({
                "id":              tmdb_id,
                "movielens_id":    int(row["movieId"]),
                "title":           str(row.get("title_y") or row.get("clean_title") or row.get("title_x","")),
                "original_title":  str(row.get("original_title","") or ""),
                "overview":        str(row.get("overview","") or ""),
                "genres":          genres,
                "release_year":    int(row.get("release_year",0) or row.get("year",0) or 0),
                "vote_average":    best_rating,
                "vote_count":      int(row.get("vote_count",0) or 0),
                "ml_avg_rating":   round(ml_avg,2),
                "ml_rating_count": ml_count,
                "popularity":      float(row.get("popularity",0) or 0),
                "poster_url":      str(row.get("poster_url","") or ""),
                "backdrop_url":    str(row.get("backdrop_url","") or ""),
                "imdb_id":         str(row.get("imdb_id","") or ""),
                "language":        str(row.get("original_language","") or ""),
                "runtime":         int(row.get("runtime",0) or 0),
                "tagline":         str(row.get("tagline","") or ""),
                "enriched":        1,
            })
        print(f"  Merged: {len(rows):,} movies ({matched:,} with Kaggle posters)")
        return rows

    else:
        # No Kaggle data — use MovieLens only
        rows = []
        for _, row in base.iterrows():
            tmdb_id = int(row.get("tmdbId",0) or 0)
            if tmdb_id == 0:
                tmdb_id = int(row["movieId"]) + 1_000_000
            rows.append({
                "id":              tmdb_id,
                "movielens_id":    int(row["movieId"]),
                "title":           str(row.get("clean_title","")),
                "original_title":  "",
                "overview":        "",
                "genres":          str(row.get("genres_pipe","")),
                "release_year":    int(row.get("year",0)),
                "vote_average":    round(float(row.get("avg_rating",7.0)),2),
                "vote_count":      0,
                "ml_avg_rating":   round(float(row.get("avg_rating",7.0)),2),
                "ml_rating_count": int(row.get("rating_count",0)),
                "popularity":      0.0,
                "poster_url":      "",
                "backdrop_url":    "",
                "imdb_id":         "",
                "language":        "",
                "runtime":         0,
                "tagline":         "",
                "enriched":        1,
            })
        print(f"  MovieLens only: {len(rows):,} movies (no posters)")
        return rows

# ── Step 6: Insert & index ────────────────────────────────────────────────────
def insert_rows(conn, rows):
    print(f"\n[6/6] Inserting {len(rows):,} rows into DB ...")
    batch_size = 5000
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        conn.executemany("""
            INSERT OR REPLACE INTO movies
            (id,movielens_id,title,original_title,overview,genres,release_year,
             vote_average,vote_count,ml_avg_rating,ml_rating_count,popularity,
             poster_url,backdrop_url,imdb_id,language,runtime,tagline,enriched)
            VALUES
            (:id,:movielens_id,:title,:original_title,:overview,:genres,:release_year,
             :vote_average,:vote_count,:ml_avg_rating,:ml_rating_count,:popularity,
             :poster_url,:backdrop_url,:imdb_id,:language,:runtime,:tagline,:enriched)
        """, batch)
        conn.commit()
        print(f"  {min(i+batch_size,len(rows)):,}/{len(rows):,}", end="\r")
    print()

    print("  Building FTS search index...")
    try:
        conn.execute("INSERT INTO movies_fts(movies_fts) VALUES('rebuild')")
        conn.commit()
        print("  FTS index ready ✓")
    except Exception as e:
        print(f"  FTS: {e}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("="*60)
    print("  MovieAI — Full Dataset Integration")
    print("  Merging: MovieLens 32M + Kaggle TMDb metadata")
    print("="*60)

    # Check required files
    missing = [f for f in [ML_MOVIES, ML_RATINGS, ML_LINKS] if not os.path.exists(f)]
    if missing:
        print(f"\n❌ Missing files: {missing}")
        print("   Make sure ml-32m/ folder is in your project root.")
        sys.exit(1)

    # Load all data
    ml_movies = load_movielens_movies()
    ratings   = load_ratings()
    links     = load_links()
    kaggle    = load_kaggle_meta()

    # Merge
    rows = merge_all(ml_movies, ratings, links, kaggle)

    # Build DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"\nDeleted old {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=50000")
    init_db(conn)
    insert_rows(conn, rows)

    # Stats
    total    = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    posters  = conn.execute("SELECT COUNT(*) FROM movies WHERE poster_url!=''").fetchone()[0]
    rated    = conn.execute("SELECT COUNT(*) FROM movies WHERE ml_rating_count > 0").fetchone()[0]
    top_row  = conn.execute("SELECT title, ml_avg_rating, ml_rating_count FROM movies ORDER BY ml_rating_count DESC LIMIT 1").fetchone()
    conn.close()

    print(f"""
{'='*60}
  ✅ Database complete!

  📽️  Total movies         : {total:,}
  🖼️  With real posters    : {posters:,}
  ⭐  With ML ratings      : {rated:,}
  🏆  Most-rated movie     : {top_row[0]} ({top_row[2]:,} ratings, avg {top_row[1]})
  💾  File                 : {DB_PATH} ({os.path.getsize(DB_PATH)//1024//1024}MB)

  Now restart Flask:  python run.py

  Features now active:
  ✓ Real crowd-sourced ratings from 32M reviews
  ✓ Posters for all matched movies (no API)
  ✓ Instant search via FTS5 index
  ✓ Genre filter with real ratings
  ✓ Recommendations based on actual viewing patterns
{'='*60}
    """)

if __name__ == "__main__":
    main()