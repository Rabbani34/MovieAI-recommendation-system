# 🎬 MovieAI — AI-Powered Movie Recommender

A full-stack movie recommendation system built with Flask, scikit-learn, and SQLite.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![Flask](https://img.shields.io/badge/Flask-3.1-green) ![License](https://img.shields.io/badge/License-MIT-yellow) ![Deploy](https://img.shields.io/badge/Deployed-PythonAnywhere-brightgreen)

## 🌐 Live Demo
👉 **https://YOUR_USERNAME.pythonanywhere.com**

---

## ✨ Features

- 🤖 **AI Recommendations** — TF-IDF content-based filtering on 87,000+ movies
- ⭐ **Real Ratings** — Crowd-sourced from 32 million MovieLens reviews
- 🖼️ **Movie Posters** — Real posters via TMDb integration
- 🔍 **Instant Search** — FTS5 full-text search index
- 🎭 **Genre Browsing** — Filter by Action, Drama, Comedy and more
- 🔎 **Advanced Filters** — Filter by year range and minimum rating
- 👤 **User Accounts** — Register, login, personalised experience
- ❤️ **Watchlist** — Save movies to watch later (synced to DB)
- 📄 **Movie Detail Pages** — Full info, cast, YouTube trailers
- 🎯 **For You** — Personalised picks based on your ratings
- 🌙 **Dark/Light Mode** — Theme toggle
- 📱 **Responsive UI** — Works on mobile and desktop

---

## 🗂️ Project Structure

```
movieai/
├── run.py                    # Flask app entry point
├── wsgi.py                   # PythonAnywhere WSGI config
├── requirements.txt          # Python dependencies
├── build_db_full.py          # Full dataset integration script
├── build_db_kaggle.py        # Kaggle-only DB builder
├── README.md
├── recommender/
│   ├── __init__.py
│   ├── model.py              # ML model + DB queries
│   ├── routes.py             # Flask routes + API endpoints
│   ├── database.py           # SQLite user/ratings/watchlist
│   ├── templates/
│   │   ├── base.html         # Base layout + navbar
│   │   ├── recommend.html    # Home + search results
│   │   ├── movie_detail.html # Full movie detail page
│   │   ├── login.html        # Login + register
│   │   └── profile.html      # User profile + ratings
│   └── static/
│       ├── style.css         # Cinematic dark UI
│       └── script.js         # Watchlist, modals, autocomplete
└── ml-32m/                   # MovieLens dataset (NOT in repo — too large)
    ├── movies.csv
    ├── ratings.csv
    └── links.csv
```

---

## 🚀 Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/movieai.git
cd movieai
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Download datasets

**MovieLens 32M** (required):
- Download from: https://grouplens.org/datasets/movielens/32m/
- Extract the `ml-32m/` folder into your project root

**Kaggle TMDb metadata** (recommended — adds posters + overviews):
- Download from: https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset
- Download `movies_metadata.csv` and place in project root

### 4. Build the database
```bash
python build_db_full.py
```
Takes ~2 minutes. Creates `tmdb_movies.db` with 45k+ movies, real ratings and posters.

### 5. Run locally
```bash
python run.py
```
Open http://127.0.0.1:5000

---

## 🌐 Deployment — PythonAnywhere (Free Forever)

This app is deployed on **PythonAnywhere** — free forever, never sleeps, persistent storage.

### Quick Deploy Steps

**1. Push to GitHub**
```bash
git add .
git commit -m "Deploy MovieAI"
git push
```

**2. On PythonAnywhere (pythonanywhere.com)**
```bash
# In PythonAnywhere Bash console:
git clone https://github.com/YOUR_USERNAME/movieai.git
cd movieai
python3.11 -m venv venv
source venv/bin/activate
pip install flask werkzeug scikit-learn pandas numpy requests
```

**3. Configure Web App**
- Dashboard → Web → Add new web app → Manual config → Python 3.11
- WSGI file: paste contents of `wsgi.py` (update YOUR_USERNAME)
- Virtualenv: `/home/YOUR_USERNAME/movieai/venv`
- Hit Reload → visit `YOUR_USERNAME.pythonanywhere.com`

**4. Upload database** (optional)
- Files tab → navigate to `~/movieai/` → upload `tmdb_movies.db`

> Full step-by-step guide in `DEPLOY_GUIDE.md`

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask 3.1 |
| ML Engine | scikit-learn (TF-IDF, cosine similarity) |
| Database | SQLite with FTS5 full-text search |
| Ratings Data | MovieLens 32M dataset (32 million reviews) |
| Movie Metadata | TMDb API + Kaggle TMDb dataset |
| Frontend | HTML5, CSS3 (custom cinematic UI), Vanilla JS |
| Auth | Flask sessions, Werkzeug password hashing |
| Deployment | PythonAnywhere (free tier) |

---

## 📊 Dataset Credits

- [MovieLens 32M](https://grouplens.org/datasets/movielens/32m/) — GroupLens Research, University of Minnesota
- [TMDb](https://www.themoviedb.org/) — The Movie Database (API + metadata)
- [Kaggle TMDb Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) — Rounak Banik

---

## 📄 License

MIT License — free to use, modify and distribute.

---

## 👨‍💻 Author

Built as a college project — contributions welcome!
