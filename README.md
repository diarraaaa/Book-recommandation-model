# OmniReads — AI-Powered Book Recommendation Engine

A full-stack book recommendation platform with a warm, cozy independent bookshop aesthetic. Built with Python, Flask, Sentence Transformers, and a production-ready PostgreSQL backend.

> **20,000 books · Personalized AI recommendations · Session-based multi-user support · One-click Render deploy**

---

## Features

- **Personalized Home Feed** — 500 books ranked by your taste profile using content-based cosine similarity
- **Genre Browsing** — Horizontal scrollable shelves organized by the top 10 genres
- **Live Search** — Multi-keyword search across title, author, and genre with 400ms debounce
- **Like / Dislike** — Rate books to shape your recommendations — no page reload needed
- **Book Detail Modal** — Full metadata overlay with blurred cover background
- **My Library** — Complete rating history with the ability to remove any rating
- **Session-based Users** — Each visitor gets a unique identity via browser cookie (no signup required)
- **Dual Database** — PostgreSQL in production, SQLite fallback for local development

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python · Flask · Waitress (WSGI) |
| **ML / AI** | Sentence Transformers (`all-MiniLM-L6-v2`) · scikit-learn · NumPy |
| **Database** | PostgreSQL (production) · SQLite (local fallback) |
| **Data** | Pandas · psycopg2 |
| **Frontend** | Vanilla HTML/CSS/JS · EB Garamond typography · Font Awesome |
| **Deploy** | Render (Blueprint via `render.yaml`) |

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/diarraaaa/Book-recommandation-model.git
cd Book-recommandation-model
pip install -r requirements.txt
```

### 2. Add Your Dataset

Place `books_cleaned.csv` in the project root.

**Required columns:** `id`, `title`, `author`, `description`, `main_genre`, `second_genre`, `series`, `cover_link`, `publisher`

### 3. Run

```bash
python app.py
```

Open **http://localhost:5000**. On first launch, click **"Open the Shelves"** to build the embeddings. This runs once and takes ~20 minutes for 20,000 books on CPU. Results are saved to disk and reused on every subsequent start.

---

## How It Works

### Embedding Generation

Every book is encoded into a **384-dimensional vector** using `all-MiniLM-L6-v2`. The input text is a weighted concatenation of metadata fields:

| Field | Weight | Rationale |
|-------|--------|-----------|
| title | 1× | Core identity |
| author | 2× | Strong taste signal |
| description | 1× | Thematic content |
| main_genre | 2× | Primary categorization |
| second_genre | 1× | Cross-genre discovery |
| series | 2× | Series loyalty |
| publisher | 1× | Mild editorial style signal |

Doubling a field pushes the model to cluster books sharing that attribute more tightly, making same-author and same-series recommendations significantly stronger.

### Recommendation Scoring

1. For each book you've rated, the engine computes **cosine similarity** between its vector and every other book
2. Scores are accumulated: `+similarity` for likes, `−similarity` for dislikes
3. Already-rated books are excluded (score = −10,000)
4. The top **500** results are returned, sorted by score

**No re-training needed.** The embedding matrix is fixed — only the scoring changes as you interact.

### User Identification

- Each visitor is assigned a **UUID** stored in a session cookie
- The UUID maps to an integer `user_id` in the `users` table
- All interactions are stored server-side in PostgreSQL (or SQLite locally)
- Sessions persist for **31 days** across browser restarts

---

## Project Structure

```
├── app.py                  # Flask API, routing, session management
├── model.py                # Embedding logic, scoring, DB abstraction
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deploy blueprint
├── .env                    # Local environment config (gitignored)
├── .gitignore
├── books_cleaned.csv       # Source dataset (you provide this)
├── books_with_content.csv  # Processed dataset (auto-generated)
├── vec_matrix.npy          # Embedding matrix (auto-generated, ~250MB)
├── interactions.db         # SQLite DB (auto-generated, local only)
├── templates/
│   └── index.html          # Main page template
└── static/
    ├── style.css           # Bookshop aesthetic stylesheet
    └── script.js           # Frontend logic and animations
```

---

## API Reference

All user-specific endpoints use **session cookies** for identification — no `user_id` parameter needed.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Check if the model is trained and ready |
| `/api/train` | POST | Trigger initial embedding generation |
| `/api/home` | GET | Personalized feed (500 books) |
| `/api/search?q=` | GET | Search by title, author, or genre |
| `/api/genres` | GET | Top 10 genres with 15 books each |
| `/api/my_ratings` | GET | Current user's rating history |
| `/api/recommend?n=10` | GET | Get top N recommendations |
| `/api/interact` | POST | Save a like (`note: 1.0`) or dislike (`note: -1.0`) |
| `/api/remove_interact` | POST | Remove a rating |

---

## Security

- **SQL injection protection** — All queries use parameterized placeholders
- **Session cookies** — `HttpOnly`, `SameSite=Lax`, signed with `SECRET_KEY`
- **No client-side user_id** — User identification is entirely server-side
- **`.env` gitignored** — Secrets never reach your repository

---

## Perspectives & Roadmap

### Short-term Improvements

- [ ] **User authentication** — Add email/password login so users keep their library across devices and browsers
- [ ] **Pagination & lazy loading** — Replace the 500-book dump with infinite scroll for faster initial loads
- [ ] **Collaborative filtering** — Leverage cross-user interaction data to surface "users who liked X also liked Y" recommendations
- [ ] **Reading lists / bookmarks** — Let users save books to custom shelves ("To Read", "Favorites", etc.)

### Medium-term Features

- [ ] **Book reviews & notes** — Allow users to write short reviews visible to the community
- [ ] **Social features** — Follow other readers, see what friends are reading, share recommendations
- [ ] **Advanced search** — Filter by rating, publication year, page count, series completion status
- [ ] **Admin dashboard** — Monitor user engagement, popular books, recommendation accuracy metrics
- [ ] **Dark / light theme toggle** — Let users switch between the bookshop aesthetic and a lighter reading mode

### Long-term Vision

- [ ] **Multi-language support** — Serve recommendations in French, Spanish, Arabic, etc.
- [ ] **Mobile app** — React Native or Flutter wrapper for iOS/Android
- [ ] **Real-time recommendations** — WebSocket-powered feed updates as users interact
- [ ] **External API integrations** — Pull metadata from Google Books, Open Library, or Goodreads
- [ ] **A/B testing framework** — Compare recommendation algorithms (content-based vs. collaborative vs. hybrid) with real user engagement data
- [ ] **Fine-tuned embeddings** — Train a custom Sentence Transformer on book-specific data for domain-optimized vectors

---

## License

MIT — Use it, fork it, build your own bookshop.
