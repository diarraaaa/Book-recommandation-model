import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
# SentenceTransformer is imported lazily inside process_and_train_dataset()
# to avoid slow startup on deployment platforms
import sqlite3
import os
import re

# ─── Configuration ───
DATABASE_URL = os.environ.get('DATABASE_URL', '')
USE_POSTGRES = DATABASE_URL.startswith('postgres')

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

DB_PATH = 'interactions.db'  # SQLite fallback path

# ─── Text Sanitization ───

def sanitize_text(text):
    """Repair double-encoded UTF-8 text (mojibake) and normalise quotes/dashes."""
    if not isinstance(text, str) or not text:
        return text
    try:
        repaired = text.encode('latin1').decode('utf-8')
        return repaired
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    replacements = {
        '\u00c3\u00a2\x80\x99': "'", '\u00c3\u00a2\x80\x9c': '"', '\u00c3\u00a2\x80\x9d': '"',
        '\u00c3\u00a2\x80\x93': '\u2013', '\u00c3\u00a2\x80\x94': '\u2014', '\u00c3\u00a2\x80\x98': "'",
        '\u00c3\u00a2\x80\u00a6': '\u2026', '\u00c3\u00a9': '\u00e9', '\u00c3\u00a8': '\u00e8', '\u00c3\u00bc': '\u00fc',
        '\u00c3\u00b6': '\u00f6', '\u00c3\u00a4': '\u00e4', '\u00c3 ': '\u00e0', '\u00c3\xaf': '\u00ef',
        '\xc3\xa9': '\u00e9', '\xc3\xa8': '\u00e8',
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    return text

def sanitize_df_text_columns(df):
    """Apply sanitize_text to common text columns of a DataFrame."""
    for col in ['title', 'author', 'description']:
        if col in df.columns:
            df[col] = df[col].apply(sanitize_text)
    return df


# ─── Database Abstraction ───

def get_db_connection():
    """Return a DB connection — PostgreSQL if DATABASE_URL is set, else SQLite."""
    if USE_POSTGRES:
        # Render uses postgres:// but psycopg2 needs postgresql://
        url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        conn = psycopg2.connect(url)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

def _ph(name=None):
    """Return the placeholder string for the current DB engine."""
    return '%s' if USE_POSTGRES else '?'

def _serial():
    """Return the auto-increment primary key type."""
    return 'SERIAL' if USE_POSTGRES else 'INTEGER'

def _upsert_interaction():
    """Return the upsert SQL for the current DB engine."""
    if USE_POSTGRES:
        return f"""
            INSERT INTO interactions (user_id, book_id, note)
            VALUES (%s, %s, %s)
            ON CONFLICT (book_id, user_id) DO UPDATE SET note = EXCLUDED.note
        """
    else:
        return 'INSERT OR REPLACE INTO interactions (user_id, book_id, note) VALUES (?, ?, ?)'

def _insert_ignore_book():
    if USE_POSTGRES:
        return 'INSERT INTO books_rated (book_id, title, author) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING'
    else:
        return 'INSERT OR IGNORE INTO books_rated (book_id, title, author) VALUES (?, ?, ?)'

def init_db():
    """Create tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                session_id TEXT UNIQUE NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                book_id INTEGER,
                note REAL,
                UNIQUE(book_id, user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books_rated (
                book_id INTEGER PRIMARY KEY,
                title TEXT,
                author TEXT
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                book_id INTEGER,
                note REAL,
                UNIQUE(book_id, user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books_rated (
                book_id INTEGER PRIMARY KEY,
                title TEXT,
                author TEXT
            )
        ''')

    conn.commit()
    conn.close()


# ─── User Management ───

def get_or_create_user(session_id):
    """Map a session UUID to a persistent integer user_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = '%s' if USE_POSTGRES else '?'

    # Try to find existing user
    cursor.execute(f'SELECT id FROM users WHERE session_id = {ph}', (session_id,))
    row = cursor.fetchone()
    if row:
        user_id = row[0]
        conn.close()
        return user_id

    # Create new user
    if USE_POSTGRES:
        cursor.execute(f'INSERT INTO users (session_id) VALUES ({ph}) RETURNING id', (session_id,))
        user_id = cursor.fetchone()[0]
    else:
        cursor.execute(f'INSERT INTO users (session_id) VALUES ({ph})', (session_id,))
        user_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return user_id


# ─── Caches ───

_books_dict_cache = []
_genres_cache = {}
_books_df_cache = None
_vec_matrix_cache = None


# ─── Training ───

def process_and_train_dataset(filepath):
    """Reads the CSV, trains SentenceTransformer (or TF-IDF fallback), and saves matrices."""
    books = pd.read_csv(filepath, on_bad_lines='skip', encoding='utf-8', engine='python').head(20000)
    books = sanitize_df_text_columns(books)

    books['content'] = (
        books['title'].fillna('') + ' ' +
        books.get('author', pd.Series([''] * len(books))).fillna('') + ' ' +
        books.get('author', pd.Series([''] * len(books))).fillna('') + ' ' +
        books.get('description', pd.Series([''] * len(books))).fillna('') + ' ' +
        books.get('main_genre', pd.Series([''] * len(books))).fillna('') + ' ' +
        books.get('main_genre', pd.Series([''] * len(books))).fillna('') + ' ' +
        books.get('second_genre', pd.Series([''] * len(books))).fillna('') + ' ' +
        books.get('series', pd.Series([''] * len(books))).fillna('') + ' ' +
        books.get('series', pd.Series([''] * len(books))).fillna('') + ' ' +
        books.get('publisher', pd.Series([''] * len(books))).fillna('')
    )

    books.to_csv('books_with_content.csv', index=False, encoding='utf-8')

    try:
        print(f"Starting to encode {len(books)} books using SentenceTransformer. This may take several minutes...")
        from sentence_transformers import SentenceTransformer
        st_model = SentenceTransformer('all-MiniLM-L6-v2')
        vec_matrix = st_model.encode(books['content'].tolist(), show_progress_bar=True)
        np.save('vec_matrix.npy', vec_matrix)
        print("Successfully saved vec_matrix.npy!")
    except Exception as e:
        print(f"Failed to use sentence-transformers, falling back to TF-IDF. Error: {e}")
        convector = TfidfVectorizer(stop_words='english')
        matrix = convector.fit_transform(books['content']).toarray()
        np.save('vec_matrix.npy', matrix)

    init_db()

    global _books_dict_cache, _genres_cache, _books_df_cache, _vec_matrix_cache
    _books_dict_cache = []
    _genres_cache = {}
    _books_df_cache = None
    _vec_matrix_cache = None

    return {"message": "Model trained and dataset processed successfully.", "books_count": len(books)}


# ─── Book Retrieval ───

def get_books():
    """Retrieve all books from cache or CSV."""
    global _books_dict_cache
    if _books_dict_cache:
        return _books_dict_cache
    if not os.path.exists('books_with_content.csv'):
        return []
    books = pd.read_csv('books_with_content.csv', encoding='utf-8')
    books = sanitize_df_text_columns(books)
    _books_dict_cache = books[['id', 'title', 'author', 'description', 'main_genre', 'cover_link']].fillna('').to_dict('records')
    return _books_dict_cache

def get_books_by_genres():
    global _genres_cache
    if _genres_cache:
        return _genres_cache
    if not os.path.exists('books_with_content.csv'):
        return {}
    books = pd.read_csv('books_with_content.csv', encoding='utf-8')
    books = sanitize_df_text_columns(books)
    books = books[books['main_genre'].notna() & (books['main_genre'] != '') & (books['main_genre'] != ' ')]
    top_genres = books['main_genre'].value_counts().head(10).index.tolist()

    result = {}
    for genre in top_genres:
        genre_books = books[books['main_genre'] == genre].head(15)
        result[genre] = genre_books[['id', 'title', 'author', 'description', 'main_genre', 'cover_link']].fillna('').to_dict('records')

    _genres_cache = result
    return result


# ─── Recommendations ───

def get_recommendations_for_user(user_id, n=10):
    """Content-based hybrid recommendations."""
    global _books_df_cache, _vec_matrix_cache
    if not os.path.exists('books_with_content.csv') or not os.path.exists('vec_matrix.npy'):
        return []

    if _books_df_cache is None:
        _books_df_cache = pd.read_csv('books_with_content.csv', encoding='utf-8')
        _books_df_cache = sanitize_df_text_columns(_books_df_cache)
    if _vec_matrix_cache is None:
        _vec_matrix_cache = np.load('vec_matrix.npy')

    books = _books_df_cache
    vec_matrix = _vec_matrix_cache
    ph = '%s' if USE_POSTGRES else '?'

    conn = get_db_connection()
    df_interactions = pd.read_sql(f"SELECT * FROM interactions WHERE user_id={ph}", conn, params=(user_id,))

    if df_interactions.empty:
        conn.close()
        return books.head(n)[['id', 'title', 'author', 'description', 'cover_link']].fillna('').to_dict('records')

    interactions = dict(zip(df_interactions['book_id'].astype(int), df_interactions['note']))

    books = books.copy()
    books['id'] = pd.to_numeric(books['id'], errors='coerce').astype('Int64')

    score = np.zeros(len(books))
    for book_id, note in interactions.items():
        realindex_df = books[books['id'] == int(book_id)]
        if realindex_df.empty:
            continue
        realindex = realindex_df.index[0]
        similarity = cosine_similarity(vec_matrix[realindex].reshape(1, -1), vec_matrix).flatten()
        score += similarity * note
        score[realindex] = -10000

    try:
        matrice_df = pd.read_sql("SELECT * FROM interactions", conn)
        if len(matrice_df['user_id'].unique()) > 1:
            matrice = matrice_df.pivot_table(index='user_id', columns='book_id', values='note', fill_value=0)
            if user_id in matrice.index:
                user_sims = cosine_similarity(matrice.loc[[user_id]], matrice).flatten()
    except:
        pass

    conn.close()

    score_enumerated = list(enumerate(score))
    score_sorted = sorted(score_enumerated, key=lambda x: x[1], reverse=True)
    recommended_indices = [idx for idx, scr in score_sorted[:n]]

    res = books.iloc[recommended_indices][['id', 'title', 'author', 'description', 'main_genre', 'cover_link']].fillna('')
    return res.to_dict('records')


# ─── User Interactions ───

def get_user_ratings(user_id):
    if not os.path.exists('books_with_content.csv'):
        return []
    books = pd.read_csv('books_with_content.csv', encoding='utf-8')
    books = sanitize_df_text_columns(books)
    ph = '%s' if USE_POSTGRES else '?'

    conn = get_db_connection()
    df_interactions = pd.read_sql(
        f"SELECT * FROM interactions WHERE user_id={ph} ORDER BY id DESC",
        conn, params=(user_id,)
    )
    conn.close()
    if df_interactions.empty:
        return []

    rated_books = []
    for _, row in df_interactions.iterrows():
        book_id = row['book_id']
        note = row['note']
        b_df = books[books['id'] == book_id]
        if not b_df.empty:
            b_dict = b_df.iloc[0][['id', 'title', 'author', 'description', 'main_genre', 'cover_link']].fillna('').to_dict()
            b_dict['user_note'] = note
            rated_books.append(b_dict)

    return rated_books

def add_interaction(user_id, book_id, note, title, author):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(_upsert_interaction(), (user_id, book_id, note))
    cursor.execute(_insert_ignore_book(), (book_id, title, author))
    conn.commit()
    conn.close()

def remove_interaction(user_id, book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = '%s' if USE_POSTGRES else '?'
    cursor.execute(f'DELETE FROM interactions WHERE user_id={ph} AND book_id={ph}', (user_id, book_id))
    conn.commit()
    conn.close()

# NOTE: init_db() is called from app.py on first request, not here,
# so the server port opens immediately on deploy.
