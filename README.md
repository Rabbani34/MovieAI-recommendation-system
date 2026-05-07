# 🎬 MovieAI — AI-Powered Movie Recommender

A full-stack movie recommendation system built with Flask, scikit-learn, and SQLite.

![MovieAI](https://img.shields.io/badge/Python-3.11-blue) ![Flask](https://img.shields.io/badge/Flask-3.1-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- 🤖 **AI Recommendations** — TF-IDF content-based filtering on 87,000+ movies
- ⭐ **Real Ratings** — Crowd-sourced from 32 million MovieLens reviews
- 🖼️ **Movie Posters** — Real posters via TMDb integration
- 🔍 **Instant Search** — FTS5 full-text search index
- 🎭 **Genre Browsing** — Filter by Action, Drama, Comedy and more
- 👤 **User Accounts** — Register, login, personalized experience
- ❤️ **Watchlist** — Save movies to watch later (synced to DB)
- 📄 **Movie Detail Pages** — Full info, cast, YouTube trailers
- 🌙 **Dark/Light Mode** — Theme toggle
- 📱 **Responsive UI** — Works on mobile and desktop

## 🗂️ Project Structure

```
movie_recommender/
├── run.py                  # Flask app entry point
├── requirements.txt        # Python dependencies
├── Procfile               # Deployment config
├── build_db_full.py       # Database builder script
├── recommender/
│   ├── __init__.py
│   ├── model.py           # ML model + DB queries
│   ├── routes.py          # Flask routes
│   ├── database.py        # SQLite user/ratings/watchlist
│   ├── templates/
│   │   ├── base.html
│   │   ├── recommend.html
│   │   ├── movie_detail.html
│   │   ├── login.html
│   │   └── profile.html
│   └── static/
│       ├── style.css
│       └── script.js
└── ml-32m/                # MovieLens dataset (not in repo)
    ├── movies.csv
    ├── ratings.csv
    └── links.csv
```

## 🚀 Local Setup

### 1. Clone & install
```bash
git clone https://github.com/YOUR_USERNAME/movieai.git
cd movieai
pip install -r requirements.txt
```

### 2. Download datasets
- **MovieLens 32M**: https://grouplens.org/datasets/movielens/32m/
  - Extract to `ml-32m/` folder
- **Kaggle TMDb metadata** *(optional, for posters)*: 
  - https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset
  - Download `movies_metadata.csv` to project root

### 3. Build the database
```bash
python build_db_full.py
```

### 4. Run
```bash
python run.py
```
Open http://127.0.0.1:5000

## 🌐 Deploy to Railway

1. Push to GitHub
2. Go to [railway.app](https://railway.app)
3. New Project → Deploy from GitHub repo
4. Add environment variable: `SECRET_KEY=your-secret-key`
5. Done — auto-deploys on every push!

> **Note**: The ML datasets are too large for GitHub (~1GB).  
> On Railway, upload `tmdb_movies.db` as a volume or use the API fallback.

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| ML | scikit-learn (TF-IDF, cosine similarity) |
| Database | SQLite (FTS5 full-text search) |
| Ratings Data | MovieLens 32M dataset |
| Movie Metadata | TMDb API + Kaggle dataset |
| Frontend | HTML, CSS (custom), Vanilla JS |
| Auth | Flask sessions, Werkzeug password hashing |
| Deployment | Railway / Gunicorn |

## 📊 Dataset Credits

- [MovieLens 32M](https://grouplens.org/datasets/movielens/32m/) — GroupLens Research
- [TMDb](https://www.themoviedb.org/) — Movie metadata and posters
- [Kaggle TMDb Dataset](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset) — Rounak Banik

## 📄 License

MIT License — free to use, modify and distribute.
