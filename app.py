from flask import Flask, request, jsonify, render_template, session
from dotenv import load_dotenv
import os
import uuid
import model

load_dotenv()  # Load .env file if present

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True


# ─── Session-based user identification ───

@app.before_request
def ensure_user_session():
    """Assign a unique session ID to every visitor on first visit."""
    if 'sid' not in session:
        session['sid'] = str(uuid.uuid4())
        session.permanent = True  # persists after browser close (default 31 days)


def get_current_user_id():
    """Get (or create) the integer user_id for the current session."""
    return model.get_or_create_user(session['sid'])


# ─── Routes ───

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def status():
    is_ready = os.path.exists('vec_matrix.npy') and os.path.exists('books_with_content.csv')
    return jsonify({"ready": is_ready})

@app.route('/api/train', methods=['POST'])
def train_model():
    if os.path.exists('vec_matrix.npy') and os.path.exists('books_with_content.csv'):
        return jsonify({"message": "Already trained"}), 200

    filepath = 'books_cleaned.csv'
    if not os.path.exists(filepath):
        return jsonify({"error": "books_cleaned.csv not found"}), 404

    try:
        res = model.process_and_train_dataset(filepath)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/books', methods=['GET'])
def get_books():
    books = model.get_books()
    return jsonify(books[:100])

@app.route('/api/search', methods=['GET'])
def search_books():
    query = request.args.get('q', '').lower().strip()
    books = model.get_books()
    if not query:
        return jsonify(books[:80])

    query_terms = query.split()
    results = []

    for b in books:
        search_target = f"{b.get('title', '')} {b.get('author', '')} {b.get('main_genre', '')}".lower()
        if all(term in search_target for term in query_terms):
            results.append(b)
            if len(results) >= 80:
                break

    return jsonify(results)

@app.route('/api/home', methods=['GET'])
def get_home():
    user_id = get_current_user_id()
    recs = model.get_recommendations_for_user(user_id, n=500)
    return jsonify(recs)

@app.route('/api/genres', methods=['GET'])
def get_genres():
    genres = model.get_books_by_genres()
    return jsonify(genres)

@app.route('/api/my_ratings', methods=['GET'])
def get_my_ratings():
    user_id = get_current_user_id()
    ratings = model.get_user_ratings(user_id)
    return jsonify(ratings)

@app.route('/api/recommend', methods=['GET'])
def get_recommendations():
    user_id = get_current_user_id()
    n = request.args.get('n', default=10, type=int)
    recs = model.get_recommendations_for_user(user_id, n)
    return jsonify(recs)

@app.route('/api/interact', methods=['POST'])
def interact():
    try:
        data = request.json
        user_id = get_current_user_id()
        book_id = data.get('book_id')
        note = data.get('note')  # 1.0 = like, -1.0 = dislike
        title = data.get('title', '')
        author = data.get('author', '')

        if book_id is None or note is None:
            return jsonify({"error": "Missing book_id or note parameter"}), 400

        model.add_interaction(user_id, int(book_id), float(note), title, author)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/remove_interact', methods=['POST'])
def remove_interact():
    try:
        data = request.json
        user_id = get_current_user_id()
        book_id = data.get('book_id')
        if not book_id:
            return jsonify({"error": "Missing book_id parameter"}), 400

        model.remove_interaction(user_id, book_id)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 5000))
    print(f"Serving on http://localhost:{port}")
    serve(app, host="0.0.0.0", port=port)
