"""
MovieAI model.py — DB-first, zero API calls for search/genre
All hot paths hit SQLite (microseconds). TMDb API only for
movie detail page (cast, trailer) and poster fallback.
"""
import os, re, json, threading, sqlite3, time
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from concurrent.futures import ThreadPoolExecutor
import requests

API_KEY      = "e547e17d4e91f3e62a571655cd1ccaff"
CACHE_FILE   = "poster_cache.json"
TMDB_DB      = "tmdb_movies.db"
BASE_URL     = "https://api.themoviedb.org/3"

_session = requests.Session()
_session.headers.update({"Accept": "application/json"})

GENRE_IDS = {
    "action":28,"adventure":12,"animation":16,"comedy":35,"crime":80,
    "documentary":99,"drama":18,"fantasy":14,"horror":27,"mystery":9648,
    "romance":10749,"sci-fi":878,"thriller":53,"western":37,
}

# ── Result cache (1 hr TTL) ───────────────────────────────────────────────────
_rcache: dict = {}
_rlock        = threading.Lock()
RESULT_TTL    = 3600

def _rget(k):
    with _rlock:
        e = _rcache.get(k)
        if e and time.time() - e["ts"] < RESULT_TTL:
            return e["d"]
    return None

def _rset(k, d):
    with _rlock:
        _rcache[k] = {"ts": time.time(), "d": d}
        if len(_rcache) > 300:
            old = sorted(_rcache, key=lambda x: _rcache[x]["ts"])
            for x in old[:60]: _rcache.pop(x, None)

# ── Poster cache ──────────────────────────────────────────────────────────────
_pcache: dict = {}
_plock        = threading.Lock()

def _load_pcache():
    global _pcache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                _pcache = json.load(f)
            print(f"Poster cache: {len(_pcache)} entries")
        except Exception: _pcache = {}
_load_pcache()

def _save_pcache():
    try:
        with _plock:
            with open(CACHE_FILE, "w") as f:
                json.dump(_pcache, f, ensure_ascii=False)
    except Exception: pass

def clean_title(t):
    return re.sub(r"\s*\(\d{4}\)\s*$", "", t).strip()

# ── DB helpers ────────────────────────────────────────────────────────────────
def _db_ok():
    return os.path.exists(TMDB_DB)

def _db_con():
    conn = sqlite3.connect(TMDB_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def _db_q(sql, params=()):
    if not _db_ok(): return []
    try:
        conn = _db_con()
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"DB: {e}"); return []

def _row_to_movie(r):
    # Use real ML crowd rating if available, else TMDb rating
    ml_rating   = float(r.get("ml_avg_rating",0) or 0)
    tmdb_rating = float(r.get("vote_average",0) or 0)
    best_rating = round(ml_rating if ml_rating > 0 else tmdb_rating, 1)
    imdb_id = r.get("imdb_id","") or ""
    return {
        "title":       r["title"],
        "genres":      r.get("genres",""),
        "rating":      best_rating,
        "year":        r.get("release_year",0),
        "imdb_link":   f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else "#",
        "poster":      r.get("poster_url",""),
        "backdrop":    r.get("backdrop_url",""),
        "overview":    r.get("overview",""),
        "similar":     [],
        "tmdb_rating": round(tmdb_rating,1),
        "ml_rating":   round(ml_rating,1),
        "ml_count":    r.get("ml_rating_count",0),
        "tmdb_id":     r.get("id",""),
        "director":    r.get("director",""),
        "runtime":     r.get("runtime",0),
        "tagline":     r.get("tagline",""),
        "trailer_key": r.get("trailer_key",""),
    }

# ── Poster fetch (only for MovieLens fallback) ────────────────────────────────
def get_movie_poster(title):
    with _plock:
        if title in _pcache: return _pcache[title]
    rows = _db_q("SELECT poster_url FROM movies WHERE LOWER(title)=? AND poster_url!=''",
                 (clean_title(title).lower(),))
    if rows:
        poster = rows[0]["poster_url"]
        with _plock: _pcache[title] = poster
        return poster
    poster = ""
    try:
        r = _session.get(f"{BASE_URL}/search/movie",
                         params={"api_key":API_KEY,"query":clean_title(title)},
                         timeout=5).json()
        if r.get("results"):
            p = r["results"][0].get("poster_path")
            if p: poster = f"https://image.tmdb.org/t/p/w342{p}"
    except Exception: pass
    if not poster:
        poster = f"https://placehold.co/300x450/111/555?text={requests.utils.quote(clean_title(title)[:14])}"
    with _plock: _pcache[title] = poster
    if len(_pcache) % 20 == 0:
        threading.Thread(target=_save_pcache, daemon=True).start()
    return poster

def fetch_posters_parallel(titles, max_workers=10):
    cached, uncached = {}, []
    with _plock:
        for t in titles:
            if t in _pcache: cached[t] = _pcache[t]
            else: uncached.append(t)
    if not uncached: return cached
    with ThreadPoolExecutor(max_workers=min(len(uncached), max_workers)) as ex:
        results = list(ex.map(get_movie_poster, uncached))
    threading.Thread(target=_save_pcache, daemon=True).start()
    return {**cached, **dict(zip(uncached, results))}

# ══════════════════════════════════════════════════════════════════════════════
class MovieRecommender:

    def __init__(self):
        print("Loading movies.csv ...")
        self.movies = pd.read_csv("ml-32m/movies.csv")
        self.movies.dropna(subset=["genres"], inplace=True)
        self.movies.drop_duplicates(subset="movieId", inplace=True)
        self.movies["genres"] = self.movies["genres"].replace("(no genres listed)","")
        self.movies["movieId"] = self.movies["movieId"].astype(int)
        self.movies["imdb_rating"] = 7.5
        self.movies["year"] = (
            self.movies["title"].str.extract(r"\((\d{4})\)$")[0]
            .fillna("0").astype(int)
        )
        print(f"MovieLens: {len(self.movies):,} movies")

        if _db_ok():
            c = _db_q("SELECT COUNT(*) as c FROM movies WHERE enriched=1")[0]["c"]
            p = _db_q("SELECT COUNT(*) as c FROM movies WHERE poster_url!=''")[0]["c"]
            print(f"TMDb DB  : {c:,} enriched | {p:,} with posters")
        else:
            print("⚠️  TMDb DB not found — run build_db.py for best results")

        print("Building TF-IDF ...")
        self.tfidf = TfidfVectorizer(stop_words="english")
        self.tfidf_matrix = self.tfidf.fit_transform(self.movies["genres"])

        print("Loading links.csv ...")
        self.links = pd.read_csv("ml-32m/links.csv")
        self.links["imdbId"]  = pd.to_numeric(self.links["imdbId"],  errors="coerce")
        self.links["movieId"] = pd.to_numeric(self.links["movieId"], errors="coerce")
        self.links = self.links.dropna(subset=["imdbId"]).set_index("movieId")
        print("Ready ✓")

    def _imdb(self, movieId):
        if movieId in self.links.index:
            return f"https://www.imdb.com/title/tt{int(self.links.loc[movieId,'imdbId']):07d}/"
        return "#"

    # ── Autocomplete: FTS if available, else LIKE ─────────────────────────────
    def autocomplete(self, query, top_n=8):
        q = query.strip().lower()
        if not q: return []
        if _db_ok():
            # Try FTS first (very fast)
            try:
                rows = _db_q(
                    "SELECT title FROM movies_fts WHERE movies_fts MATCH ? "
                    "ORDER BY rank LIMIT ?",
                    (f"{q}*", top_n)
                )
                if rows: return [r["title"] for r in rows]
            except Exception: pass
            # Fallback to LIKE
            rows = _db_q(
                "SELECT title FROM movies WHERE LOWER(title) LIKE ? "
                "OR LOWER(original_title) LIKE ? "
                "ORDER BY popularity DESC LIMIT ?",
                (f"%{q}%", f"%{q}%", top_n)
            )
            if rows: return [r["title"] for r in rows]
        # MovieLens fallback
        return self.movies[
            self.movies["title"].str.lower().str.contains(q, na=False)
        ].head(top_n)["title"].tolist()

    # ── Top movies ────────────────────────────────────────────────────────────
    def get_top_movies(self, n=20):
        k = f"top::{n}"
        if hit := _rget(k): return hit
        if _db_ok():
            rows = _db_q(
                "SELECT * FROM movies WHERE poster_url!='' AND enriched=1 "
                "ORDER BY vote_average DESC, popularity DESC LIMIT ?", (n,)
            )
            if rows:
                r = [_row_to_movie(x) for x in rows]
                _rset(k, r); return r
        results = []
        for _, row in self.movies.head(n).iterrows():
            with _plock: poster = _pcache.get(row["title"], "")
            results.append({
                "title":row["title"],"genres":row["genres"],"rating":row["imdb_rating"],
                "year":int(row["year"]),"imdb_link":self._imdb(row["movieId"]),
                "poster":poster,"overview":"","similar":[],"tmdb_rating":7.5,"backdrop":"",
            })
        _rset(k, results); return results

    # ── Search / Recommend ────────────────────────────────────────────────────
    def recommend(self, title: str, top_n=12) -> list:
        k = f"rec::{title.lower().strip()}"
        if hit := _rget(k): return hit

        # ── DB path: FTS search → similar genres → pure SQL, zero API ─────────
        if _db_ok():
            # Find the searched movie in DB
            seed_rows = _db_q(
                "SELECT * FROM movies WHERE (LOWER(title) LIKE ? OR LOWER(original_title) LIKE ?) "
                "AND enriched=1 ORDER BY popularity DESC LIMIT 1",
                (f"%{clean_title(title).lower()}%", f"%{title.lower().strip()}%")
            )
            if seed_rows:
                seed = seed_rows[0]
                seed_genres = seed.get("genres","")
                seed_year   = seed.get("release_year", 2000)

                # Find movies with overlapping genres, similar era, good rating
                genre_parts = [g.strip() for g in seed_genres.replace("|",",").split(",") if g.strip()]
                if genre_parts:
                    like_clauses = " OR ".join(["genres LIKE ?"] * len(genre_parts))
                    params = [f"%{g}%" for g in genre_parts]
                    rows = _db_q(
                        f"SELECT * FROM movies WHERE ({like_clauses}) "
                        f"AND id != ? AND poster_url != '' AND enriched=1 "
                        f"AND release_year BETWEEN ? AND ? "
                        f"ORDER BY vote_average DESC, popularity DESC LIMIT ?",
                        params + [seed["id"], max(1900, seed_year-15),
                                  seed_year+15, top_n]
                    )
                    if len(rows) < top_n // 2:
                        # Broaden year range
                        rows = _db_q(
                            f"SELECT * FROM movies WHERE ({like_clauses}) "
                            f"AND id != ? AND poster_url != '' AND enriched=1 "
                            f"ORDER BY vote_average DESC, popularity DESC LIMIT ?",
                            params + [seed["id"], top_n]
                        )
                    if rows:
                        results = [_row_to_movie(r) for r in rows[:top_n]]
                        _rset(k, results); return results

        # ── API path: TMDb search + recommendations (2 calls only) ────────────
        try:
            sr = _session.get(f"{BASE_URL}/search/movie",
                              params={"api_key":API_KEY,"query":title},
                              timeout=5).json()
            hits = [m for m in sr.get("results",[]) if m.get("poster_path")]
            if hits:
                tmdb_id = hits[0]["id"]
                rr = _session.get(f"{BASE_URL}/movie/{tmdb_id}/recommendations",
                                  params={"api_key":API_KEY,"language":"en-US"},
                                  timeout=5).json()
                results = []
                for m in rr.get("results",[]):
                    if not m.get("poster_path"): continue
                    poster = f"https://image.tmdb.org/t/p/w342{m['poster_path']}"
                    with _plock: _pcache[m["title"]] = poster
                    results.append({
                        "title":       m["title"],
                        "genres":      "",
                        "rating":      round(float(m.get("vote_average",0)),1),
                        "year":        int((m.get("release_date","0")or"0")[:4]),
                        "imdb_link":   "#",
                        "poster":      poster,
                        "backdrop":    f"https://image.tmdb.org/t/p/w1280{m['backdrop_path']}" if m.get("backdrop_path") else "",
                        "overview":    m.get("overview",""),
                        "similar":     [],
                        "tmdb_rating": round(float(m.get("vote_average",0)),1),
                    })
                if results:
                    _rset(k, results[:top_n]); return results[:top_n]
        except Exception as e:
            print(f"API fallback error: {e}")

        # ── MovieLens TF-IDF (last resort) ────────────────────────────────────
        tc = title.strip().lower()
        m  = self.movies[self.movies["title"].str.lower().str.contains(tc, na=False)]
        if m.empty: return []
        idx    = m.index[0]
        scores = cosine_similarity(self.tfidf_matrix[idx], self.tfidf_matrix).flatten()
        top_i  = scores.argsort()[-top_n-1:-1][::-1]
        rows   = self.movies.iloc[top_i]
        titles = rows["title"].tolist()
        posters = fetch_posters_parallel(titles)
        results = [{
            "title":t,"genres":row["genres"],"rating":row["imdb_rating"],
            "year":int(row["year"]),"imdb_link":self._imdb(row["movieId"]),
            "poster":posters.get(t,""),"similar":[],"overview":"",
            "tmdb_rating":7.5,"backdrop":"",
        } for t,(_, row) in zip(titles, rows.iterrows())]
        _rset(k, results); return results

    # ── Genre search ──────────────────────────────────────────────────────────
    def search_by_genre(self, genre, top_n=24,
                        min_year=None, max_year=None, min_rating=None):
        k = f"genre::{genre.lower()}::{min_year}::{max_year}::{min_rating}"
        if hit := _rget(k): return hit

        if _db_ok():
            conds  = ["LOWER(genres) LIKE ?","poster_url != ''","enriched=1"]
            params = [f"%{genre.lower()}%"]
            if min_year   and str(min_year)   not in ("","1900"):
                conds.append("release_year >= ?"); params.append(int(min_year))
            if max_year   and str(max_year)   not in ("","2024","2025"):
                conds.append("release_year <= ?"); params.append(int(max_year))
            if min_rating and str(min_rating) != "":
                conds.append("vote_average >= ?"); params.append(float(min_rating))
            sql  = "SELECT * FROM movies WHERE " + " AND ".join(conds)
            sql += " ORDER BY vote_average DESC, popularity DESC LIMIT ?"
            rows = _db_q(sql, params + [top_n])
            if rows:
                results = [_row_to_movie(r) for r in rows]
                _rset(k, results); return results

        # TMDb Discover API fallback
        gid = GENRE_IDS.get(genre.lower())
        if gid:
            try:
                p = {"api_key":API_KEY,"with_genres":gid,
                     "sort_by":"popularity.desc","vote_count.gte":30,
                     "language":"en-US","page":1}
                if min_year   and str(min_year)   not in ("","1900"):
                    p["primary_release_date.gte"] = f"{min_year}-01-01"
                if max_year   and str(max_year)   not in ("","2024","2025"):
                    p["primary_release_date.lte"] = f"{max_year}-12-31"
                if min_rating and str(min_rating) != "":
                    p["vote_average.gte"] = float(min_rating)
                r = _session.get(f"{BASE_URL}/discover/movie", params=p, timeout=8).json()
                results = []
                for m in r.get("results",[]):
                    if not m.get("poster_path"): continue
                    poster = f"https://image.tmdb.org/t/p/w342{m['poster_path']}"
                    with _plock: _pcache[m["title"]] = poster
                    results.append({
                        "title":m["title"],"genres":genre.title(),
                        "rating":round(float(m.get("vote_average",0)),1),
                        "year":int((m.get("release_date","0")or"0")[:4]),
                        "imdb_link":"#",
                        "poster":poster,
                        "backdrop":f"https://image.tmdb.org/t/p/w1280{m['backdrop_path']}" if m.get("backdrop_path") else "",
                        "overview":m.get("overview",""),"similar":[],
                        "tmdb_rating":round(float(m.get("vote_average",0)),1),
                    })
                if results:
                    _rset(k, results[:top_n]); return results[:top_n]
            except Exception as e:
                print(f"Discover error: {e}")

        # MovieLens fallback
        mask = self.movies["genres"].str.contains(genre, case=False, na=False)
        df   = self.movies[mask].head(top_n)
        posters = fetch_posters_parallel(df["title"].tolist())
        return [{
            "title":row["title"],"genres":row["genres"],
            "rating":row["imdb_rating"],"year":int(row["year"]),
            "imdb_link":self._imdb(row["movieId"]),
            "poster":posters.get(row["title"],""),
            "similar":[],"overview":"","tmdb_rating":7.5,"backdrop":"",
        } for _, row in df.iterrows()]

    def get_personalized_recommendations(self, user_ratings, top_n=12):
        liked = [(r["movie_title"],r["rating"]) for r in user_ratings if r["rating"]>=3.5]
        if len(liked)<2: return []
        pref = np.zeros(self.tfidf_matrix.shape[1]); tw=0.0
        for title,rating in liked:
            m = self.movies[self.movies["title"].str.lower()==title.lower()]
            if not m.empty:
                w=rating/5.0; pref+=w*self.tfidf_matrix[m.index[0]].toarray().flatten(); tw+=w
        if tw==0: return []
        pref/=tw
        scores=cosine_similarity([pref],self.tfidf_matrix).flatten()
        rated={r["movie_title"].lower() for r in user_ratings}
        results=[]
        for i in scores.argsort()[::-1]:
            if len(results)>=top_n: break
            row=self.movies.iloc[i]
            if row["title"].lower() not in rated: results.append(row)
        if not results: return []
        df=pd.DataFrame(results); posters=fetch_posters_parallel(df["title"].tolist())
        return [{
            "title":row["title"],"genres":row["genres"],"rating":row["imdb_rating"],
            "year":int(row["year"]),"imdb_link":self._imdb(row["movieId"]),
            "poster":posters.get(row["title"],""),
            "similar":[],"overview":"","tmdb_rating":7.5,"backdrop":"",
        } for _,row in df.iterrows()]

    def get_movie_detail(self, title):
        k = f"detail::{title.lower().strip()}"
        if hit := _rget(k): return hit

        # DB-first: if fully enriched, no API call needed
        if _db_ok():
            rows = _db_q(
                "SELECT * FROM movies WHERE (LOWER(title) LIKE ? OR LOWER(original_title) LIKE ?) "
                "AND enriched=1 ORDER BY popularity DESC LIMIT 1",
                (f"%{clean_title(title).lower()}%", f"%{title.lower().strip()}%")
            )
            if rows and rows[0].get("poster_url"):
                r = _row_to_movie(rows[0])
                # Parse cast string into list for template
                r["cast"] = [{"name":n.strip(),"character":"","photo":""}
                             for n in (rows[0].get("cast_names","") or "").split(",") if n.strip()]
                _rset(k,r); return r

        # API fallback for detail page
        try:
            sr = _session.get(f"{BASE_URL}/search/movie",
                              params={"api_key":API_KEY,"query":title},timeout=5).json()
            hits=[m for m in sr.get("results",[]) if m.get("poster_path")]
            if not hits: return None
            tmdb_id=hits[0]["id"]
            d = _session.get(f"{BASE_URL}/movie/{tmdb_id}",
                             params={"api_key":API_KEY,"append_to_response":"credits,videos"},
                             timeout=6).json()
            poster   = f"https://image.tmdb.org/t/p/w342{d['poster_path']}"   if d.get("poster_path")   else ""
            backdrop = f"https://image.tmdb.org/t/p/w1280{d['backdrop_path']}" if d.get("backdrop_path") else ""
            cast=[{"name":c["name"],"character":c["character"],
                   "photo":f"https://image.tmdb.org/t/p/w185{c['profile_path']}" if c.get("profile_path") else ""}
                  for c in d.get("credits",{}).get("cast",[])[:8]]
            director=next((c["name"] for c in d.get("credits",{}).get("crew",[]) if c["job"]=="Director"),"")
            trailer_key=next((v["key"] for v in d.get("videos",{}).get("results",[])
                              if v["type"]=="Trailer" and v["site"]=="YouTube"),"")
            ml=self.movies[self.movies["title"].str.lower().str.contains(clean_title(title).lower(),na=False)]
            result={
                "title":d.get("title",title),
                "genres":"|".join(g["name"] for g in d.get("genres",[])),
                "rating":round(float(d.get("vote_average",0)),1),
                "year":(d.get("release_date","")or"")[:4],
                "imdb_link":self._imdb(ml.iloc[0]["movieId"]) if not ml.empty else "#",
                "poster":poster,"backdrop":backdrop,"overview":d.get("overview",""),
                "tagline":d.get("tagline",""),"runtime":d.get("runtime",0),
                "vote_average":round(float(d.get("vote_average",0)),1),
                "tmdb_rating":round(float(d.get("vote_average",0)),1),
                "cast":cast,"director":director,"trailer_key":trailer_key,
                "similar":[],"imdb_id":d.get("imdb_id",""),
            }
            _rset(k,result); return result
        except Exception as e:
            print(f"Detail error: {e}"); return None