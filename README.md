---
title: OmniReads
emoji: 📚
colorFrom: purple
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
---

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

Every unrated book receives a **cumulative score** based on its similarity to all the books you've rated. The formula for the score of a candidate book `c` is:

```
score(c) = Σ  cosine_similarity(vec[c], vec[rated_i]) × note_i
           i
```

Where:
- `vec[c]` is the 384-dim embedding of the candidate book
- `vec[rated_i]` is the embedding of each book you've rated
- `note_i` is `+1.0` for a like and `−1.0` for a dislike

#### Step-by-step

1. **Initialize** a score array of zeros, one entry per book in the catalogue (20,000)
2. **For each book you've liked** (`note = +1.0`):
   - Compute cosine similarity between its vector and every other book's vector → produces a similarity array of 20,000 values between −1 and +1
   - **Add** those similarities to the score array → books similar to what you liked get a positive boost
3. **For each book you've disliked** (`note = −1.0`):
   - Same similarity computation, but the values are **subtracted** from the score array → books similar to what you disliked get penalized
4. **Exclude already-rated books** by setting their score to `−10,000` (guarantees they never appear)
5. **Sort** descendingly and return the top 500

#### Concrete example

Suppose you liked *Dune* and disliked *Twilight*:

| Candidate Book | sim(Dune) | sim(Twilight) | Score |
|----------------|-----------|---------------|-------|
| *Foundation* (sci-fi) | 0.82 | 0.10 | `0.82 × (+1) + 0.10 × (−1)` = **+0.72** |
| *Ender's Game* (sci-fi) | 0.78 | 0.12 | `0.78 − 0.12` = **+0.66** |
| *New Moon* (vampire romance) | 0.15 | 0.94 | `0.15 − 0.94` = **−0.79** |
| *The Martian* (sci-fi) | 0.71 | 0.08 | `0.71 − 0.08` = **+0.63** |

*Foundation* ranks highest because it's very similar to *Dune* and dissimilar to *Twilight*. *New Moon* is buried because it's highly similar to the disliked *Twilight*.

#### Why this works

- **Likes attract**: The more books you like in a genre/by an author, the more their neighborhood accumulates positive signal → stronger genre/author affinity
- **Dislikes repel**: A single dislike can push down an entire cluster of similar books, preventing the feed from being dominated by genres you don't enjoy
- **No re-training needed**: The 20,000 × 384 embedding matrix is fixed — only the score computation changes as you interact, making recommendations instant

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

## 🤗 Deploy to Hugging Face Spaces (Free 16 GB RAM)

This project includes a `Dockerfile` pre-configured for **Hugging Face Spaces**. It’s the perfect host if you want to avoid Out-of-Memory crashes during ML training because their free tier offers 16 GB RAM and 2 vCPUs!

1. Push your code to GitHub (make sure `Dockerfile` is included).
2. Create an account on [Hugging Face](https://huggingface.co/)
3. Go to your Profile → **New Space**
4. Set the **Space name** (e.g., `OmniReads`)
5. **License**: MIT
6. **Select the Space SDK**: Choose **Docker** (Blank)
7. **Space Hardware**: Free (16GB RAM)
8. Click **Create Space**
9. Connect inside your new space settings to automatically build from your GitHub repository.

**Important:** Keep your PostgreSQL database on Render. Once the Space is created, go to the Space **Settings** → **Variables and secrets** and add:
- `SECRET_KEY`: any random string
- `DATABASE_URL`: The Internal Connection String of your Render database (since HF is outside Render, you must use the **External Connection String**, not the internal one!).

The `Dockerfile` handles port `7860` automatically.

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
