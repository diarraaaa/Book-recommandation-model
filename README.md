# Book Recommendation System

A hybrid book recommendation engine built from scratch using NLP and collaborative filtering techniques on a dataset of 50,000+ books.

## What it does

Given a user's reading history — likes, dislikes, and ratings — the system recommends books they are likely to enjoy. It combines two complementary approaches:

- **Content-based filtering** — finds books similar to what the user has liked, based on descriptions, genres, authors, and series
- **User-based collaborative filtering** — finds users with similar taste and surfaces books they loved that the user hasn't read yet

## Dataset

Sourced from Kaggle. ~50,000 books with the following fields used for modeling:

| Field | Role |
|---|---|
| `title`, `author` | Identity |
| `description` | Primary content signal |
| `genre_and_votes` | Genre extraction |
| `series` | Series-level similarity |
| `characters`, `settings` | Universe-level similarity |
| `average_rating`, `rating_count` | Quality weighting |

## How it works

### Content-Based

Each book is represented as a single embedding vector built from its combined text fields (`title + author + description + genre + series + characters + settings`).

Two vectorization approaches were explored:

**TF-IDF + Cosine Similarity**
Fast and interpretable. Works well for same-author and same-series recommendations. Struggles with semantic similarity across different vocabularies.

**Sentence Transformers (`all-MiniLM-L6-v2`)**
Encodes full sentences into dense 384-dimensional vectors. Captures semantic meaning — recommending Nietzsche and Sartre when a user likes Camus, not just books with similar words. Significantly better results than TF-IDF for cross-genre discovery.

Recommendations are scored using a weighted formula:

```
final_score = 0.75 × similarity + 0.15 × (avg_rating / 5) + 0.10 × (rating_count / max_rating_count)
```

### User-Based Collaborative Filtering

User interactions (like = +1, dislike = −1, rating = normalized between −1 and +1) are stored in a SQLite database and used to build a user × book matrix.

Cosine similarity between user vectors identifies neighbors with similar taste. Books rated positively by similar users — and not yet seen by the target user — are surfaced as recommendations, weighted by neighbor similarity.

### Hybrid

The final recommendation list merges results from both approaches, deduplicates, and returns book IDs with titles.

## Stack

```
Python · Pandas · NumPy · Scikit-learn · Sentence Transformers · SQLite
```

## Results

| Query | Top result |
|---|---|
| Like: Harry Potter | Harry Potter Boxed Set, The Hogwarts Library, James Potter |
| Like: White Nights (Dostoevsky) | The Dream of a Ridiculous Man, The Eternal Husband, Demons |
| Like: Hamlet | Richard II, Henry IV, Coriolanus, Titus Andronicus |
| Like: A Happy Death (Camus) | The Denial of Death, The Birth of Tragedy, The Reprieve (Sartre) |

The model performs well for same-author and same-series retrieval. The Sentence Transformers approach shows meaningful cross-author semantic connections (Camus → Sartre → Nietzsche).

## Limitations

- No genre column in the original dataset — genre was extracted from vote-weighted strings and may be noisy
- Collaborative filtering uses simulated interaction data — real user behavior would significantly improve results
- Cold start problem — new users with no interactions fall back to content-based only
- Some titles contain encoding artifacts from the original CSV

## Future Work

- REST API with Flask for real-time recommendations
- Web interface with like/dislike/rating interactions stored in SQLite
- Replace simulated interactions with real user data
- Evaluate recommendations against the `recommended_books` column present in the dataset
- Explore Matrix Factorization (SVD) as a third approach
