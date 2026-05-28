<div align="center">

<img src="https://capsule-render.vercel.app/api?type=venom&color=0:0f0c29,50:0d1f3c,100:0a0a2e&height=220&section=header&text=AI%20Movie%20Recommendation%20System&fontSize=36&fontColor=ffffff&fontAlignY=42&desc=87%2C000%2B%20Movies%20%E2%80%A2%20TF-IDF%20%E2%80%A2%20Cosine%20Similarity%20%E2%80%A2%20MovieLens%2032M&descAlignY=62&descSize=14&descColor=93c5fd&animation=fadeIn" width="100%"/>

<br/>

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=0f0c29)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white&labelColor=0f0c29)](https://flask.palletsprojects.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white&labelColor=0f0c29)](https://scikit-learn.org)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white&labelColor=0f0c29)](https://sqlite.org)
[![TMDb](https://img.shields.io/badge/TMDb_API-01B4E4?style=for-the-badge&logo=themoviedatabase&logoColor=white&labelColor=0f0c29)](https://themoviedb.org)

<br/>

> **A full-stack AI-powered movie recommendation engine using TF-IDF vectorisation and cosine similarity on the MovieLens 32M dataset — with real-time search, user authentication, watchlists, and TMDb integration.**

</div>

---

## 🎯 Key Stats

<div align="center">

| Metric | Value |
|---|---|
| 🎬 **Movies in database** | **87,000+** |
| 🔍 **Searchable titles** | **45,000+** (FTS5 full-text search) |
| 📦 **Dataset** | MovieLens 32M |
| ⚡ **Avg response time** | **< 200ms** |
| 🔐 **Auth** | Flask Sessions + Werkzeug hashing |
| ☁️ **Deployment** | Render + Gunicorn |

</div>

---

## ✨ Features

- 🤖 **Content-based recommendations** — TF-IDF vectorisation + cosine similarity on movie metadata
- 🔍 **Instant full-text search** — FTS5-powered autocomplete across 45,000+ titles
- 🖼️ **TMDb API integration** — live movie posters, descriptions, and metadata with disk caching (60% fewer API calls)
- 🔐 **Secure authentication** — user registration/login with hashed passwords via Werkzeug
- ❤️ **Personalised watchlists** — save movies per user, stored in SQLite
- ⭐ **Star rating system** — rate movies and improve recommendations
- 📱 **Responsive UI** — works cleanly on mobile and desktop

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Recommendation Engine** | TF-IDF Vectoriser · Cosine Similarity · scikit-learn |
| **Dataset** | MovieLens 32M · Pandas · NumPy |
| **Backend** | Flask · Python · Gunicorn |
| **Database** | SQLite · FTS5 Full-Text Search |
| **External API** | TMDb API (with disk caching) |
| **Auth** | Flask Sessions · Werkzeug |
| **Deployment** | Render |

---

## 🚀 Running Locally

```bash
# 1. Clone the repository
git clone https://github.com/Rabbani34/MovieAI-recommendation-system.git
cd MovieAI-recommendation-system

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your TMDb API key
echo "TMDB_API_KEY=your_api_key_here" > .env

# 5. Run the app
flask run

# 6. Open in browser
# http://localhost:5000
```

---

## 📁 Project Structure

```
MovieAI-recommendation-system/
│
├── app.py                      # Flask app + routes
├── recommender/
│   ├── engine.py               # TF-IDF + cosine similarity pipeline
│   └── cache.py                # TMDb API disk caching
├── database/
│   ├── models.py               # SQLite schema
│   └── fts.py                  # FTS5 full-text search
├── auth/
│   └── routes.py               # Login / register / sessions
├── static/                     # CSS, JS, assets
├── templates/                  # Jinja2 HTML templates
├── requirements.txt
└── README.md
```

---

## 👨‍💻 Author

**Mohammed Rabbani**
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/rabbani-mohammed-57653b333/)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/Rabbani34)
[![Portfolio](https://img.shields.io/badge/Portfolio-7c3aed?style=flat-square&logo=vercel&logoColor=white)](https://portfolio-sigma-seven-x81lwlz28v.vercel.app/?_vercel_share=49IHQNbb2vXxh0Dx10qyqqvCWZpu7VYo)

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f0c29,100:0d1f3c&height=100&section=footer&animation=fadeIn" width="100%"/>
</div>
