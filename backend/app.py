from flask import Flask, jsonify, request, send_from_directory
import requests
# --- CSV Sync from Render (if configured) ---
#RENDER_CSV_URL = os.environ.get('RENDER_CSV_URL')  # e.g. 'https://your-render-app.onrender.com/api/admin/download-csv'
#def sync_csv_from_render():
##      return
#  try:
#     print(f"[CSV SYNC] Downloading latest CSV from {RENDER_CSV_URL} ...")
#    resp = requests.get(RENDER_CSV_URL, timeout=30)
#   resp.raise_for_status()
#  with open(DATA_FILE, 'wb') as f:
#     f.write(resp.content)
# print("[CSV SYNC] Local CSV updated from Render.")
# except Exception as e:
#   print(f"[CSV SYNC] Failed to sync CSV from Render: {e}")

# Call sync before app starts
#sync_csv_from_render()
from flask_cors import CORS
import pandas as pd
import random
import sqlite3
from datetime import datetime
import os
import hashlib
from question_generator import QuestionGenerator

# Get the port from environment (Replit uses dynamic ports)
PORT = int(os.environ.get('PORT', 5002))

# Update CORS to allow Replit domain
app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'MCQ_Quesbank.csv')
DB_FILE = os.path.join(BASE_DIR, 'data', 'history.db')
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = bool(DATABASE_URL)
NO_REPEAT_TESTS = 10

class DbCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        if USE_POSTGRES:
            query = query.replace('?', '%s')
        if params is None:
            return self._cursor.execute(query)
        return self._cursor.execute(query, params)

    def executemany(self, query, params):
        if USE_POSTGRES:
            query = query.replace('?', '%s')
        return self._cursor.executemany(query, params)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __getattr__(self, name):
        return getattr(self._cursor, name)

class DbConnection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return DbCursor(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)

def get_db_connection(*_args, **_kwargs):
    if USE_POSTGRES:
        import psycopg2
        return DbConnection(psycopg2.connect(DATABASE_URL))
    return sqlite3.connect(DB_FILE)

if USE_POSTGRES:
    sqlite3.connect = get_db_connection

def normalize_text(value):
    text = str(value or '')
    text = ' '.join(text.strip().split())
    return text.lower()

def compute_question_uid(subject, question, options):
    parts = [normalize_text(subject), normalize_text(question)]
    parts.extend([normalize_text(opt) for opt in (options or [])])
    signature = '|'.join(parts)
    return hashlib.sha256(signature.encode('utf-8')).hexdigest()

def get_recent_question_uids(user_id, subject, limit_tests):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id
        FROM test_history
        WHERE user_id = ? AND subject = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (user_id, subject, limit_tests))

    test_ids = [row[0] for row in cursor.fetchall()]
    if not test_ids:
        conn.close()
        return set()

    placeholders = ','.join(['?'] * len(test_ids))
    cursor.execute(f'''
        SELECT question_uid
        FROM question_history
        WHERE test_id IN ({placeholders}) AND question_uid IS NOT NULL
    ''', test_ids)

    uids = {row[0] for row in cursor.fetchall() if row[0]}
    conn.close()
    return uids

def format_timestamp(ts_value):
    if isinstance(ts_value, datetime):
        return ts_value
    try:
        return datetime.strptime(ts_value, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return datetime.fromisoformat(str(ts_value))

# Initialize database
def init_db():
    data_dir = os.path.join(BASE_DIR, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    conn = get_db_connection()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_history (
                id SERIAL PRIMARY KEY,
                subject TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                correct_answers INTEGER NOT NULL,
                score DOUBLE PRECISION NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                user_name TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_history (
                id SERIAL PRIMARY KEY,
                test_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                user_answer TEXT,
                correct_answer TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                question_uid TEXT,
                FOREIGN KEY (test_id) REFERENCES test_history(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visitor_logs (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_name TEXT,
                visit_type TEXT NOT NULL,
                page_visited TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                user_name TEXT NOT NULL,
                first_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_visits INTEGER DEFAULT 1,
                total_tests INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_attempts (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                test_id INTEGER NOT NULL,
                score DOUBLE PRECISION NOT NULL,
                duration_seconds INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_id) REFERENCES test_history(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS newly_updated_questions (
                id SERIAL PRIMARY KEY,
                subject TEXT NOT NULL,
                question TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                question_type TEXT DEFAULT 'Standard',
                chapter_name TEXT DEFAULT 'General',
                explanation TEXT,
                status TEXT DEFAULT 'pending_review',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                review_notes TEXT,
                source TEXT DEFAULT 'ai'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_actions (
                id SERIAL PRIMARY KEY,
                action_type TEXT NOT NULL,
                target_id INTEGER,
                details TEXT,
                admin_user TEXT DEFAULT 'admin',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                correct_answers INTEGER NOT NULL,
                score REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT DEFAULT NULL,
                user_name TEXT DEFAULT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                user_answer TEXT,
                correct_answer TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                question_uid TEXT,
                FOREIGN KEY (test_id) REFERENCES test_history(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visitor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT DEFAULT NULL,
                visit_type TEXT NOT NULL,
                page_visited TEXT NOT NULL,
                ip_address TEXT DEFAULT NULL,
                user_agent TEXT DEFAULT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL UNIQUE,
                user_name TEXT NOT NULL,
                first_visit DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_visit DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_visits INTEGER DEFAULT 1,
                total_tests INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                test_id INTEGER NOT NULL,
                score REAL NOT NULL,
                duration_seconds INTEGER DEFAULT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_id) REFERENCES test_history(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS newly_updated_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                question TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                question_type TEXT DEFAULT 'Standard',
                chapter_name TEXT DEFAULT 'General',
                explanation TEXT,
                status TEXT DEFAULT 'pending_review',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                reviewed_at DATETIME DEFAULT NULL,
                reviewed_by TEXT DEFAULT NULL,
                is_active BOOLEAN DEFAULT 1,
                review_notes TEXT DEFAULT NULL,
                source TEXT DEFAULT 'ai'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                target_id INTEGER,
                details TEXT,
                admin_user TEXT DEFAULT 'admin',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    if USE_POSTGRES:
        cursor.execute('''
            ALTER TABLE question_history
            ADD COLUMN IF NOT EXISTS question_uid TEXT
        ''')
    else:
        cursor.execute("PRAGMA table_info(question_history)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        if 'question_uid' not in existing_columns:
            cursor.execute('ALTER TABLE question_history ADD COLUMN question_uid TEXT')

    conn.commit()
    conn.close()

init_db()

# User Tracking Function

def get_client_ip():
    """Get client IP address"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr or 'Unknown'

def get_user_agent():
    """Get user agent string"""
    return request.headers.get('User-Agent', 'Unknown')

def log_visitor(user_id, user_name, visit_type, page_visited):
    """Log visitor activity"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        
        cursor.execute('''
            INSERT INTO visitor_logs (user_id, user_name, visit_type, page_visited, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, visit_type, page_visited, ip_address, user_agent))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error logging visitor: {e}")

def update_user_session(user_id, user_name):
    """Update or create user session"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT id, total_visits FROM user_sessions WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result:
            # Update existing user
            cursor.execute('''
                UPDATE user_sessions
                SET user_name = ?, last_visit = CURRENT_TIMESTAMP, total_visits = total_visits + 1
                WHERE user_id = ?
            ''', (user_name, user_id))
        else:
            # Create new user
            cursor.execute('''
                INSERT INTO user_sessions (user_id, user_name)
                VALUES (?, ?)
            ''', (user_id, user_name))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error updating user session: {e}")

def log_test_attempt(user_id, user_name, subject, test_id, score, duration_seconds=None):
    """Log test attempt"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO test_attempts (user_id, user_name, subject, test_id, score, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, subject, test_id, score, duration_seconds))
        
        # Update user session test count
        cursor.execute('''
            UPDATE user_sessions
            SET total_tests = total_tests + 1
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error logging test attempt: {e}")

# Fix encoding issues in text
def fix_encoding(text):
    """Fix common UTF-8 encoding issues caused by double-encoding"""
    if not isinstance(text, str):
        return text
    
    replacements = [
        ('\u00c2\u00b2', '\u00b2'),  # Â² -> ²
        ('\u00c2\u00b3', '\u00b3'),  # Â³ -> ³
        ('\u00e2\u0088\u0092', '-'),  # âˆ' -> -
        ('\u00e2\u0080\u0094', '\u2014'),  # â€" -> —
        ('\u00e2\u0080\u0093', '\u2013'),  # â€" -> –
        ('\u00e2\u0080\u0099', "'"),  # â€™ -> '
        ('\u00e2\u0080\u009c', '"'),  # â€œ -> "
        ('\u00e2\u0080\u009d', '"'),  # â€ -> "
        ('\u00e2\u0082\u0082', '\u2082'),  # â‚‚ -> ₂
        ('\u00e2\u0082\u0080', '\u2080'),  # â‚€ -> ₀
        ('\u00e2\u0082\u0081', '\u2081'),  # â‚ -> ₁
        ('\u00e2\u0082\u0083', '\u2083'),  # â‚ƒ -> ₃
        ('\u00e2\u0082\u0084', '\u2084'),  # â‚„ -> ₄
        ('\u00e2\u0082\u0085', '\u2085'),  # â‚… -> ₅
        ('\u00c3\u0097', '\u00d7'),  # Ã— -> ×
        ('\u00c3\u00b7', '\u00f7'),  # Ã· -> ÷
        ('\u00e2\u0089\u00a4', '\u2264'),  # â‰¤ -> ≤
        ('\u00e2\u0089\u00a5', '\u2265'),  # â‰¥ -> ≥
        ('\u00e2\u0088\u009a', '\u221a'),  # âˆš -> √
        ('\u00cf\u0080', '\u03c0'),  # Ï€ -> π
        ('\u00ce\u00b1', '\u03b1'),  # Î± -> α
        ('\u00ce\u00b2', '\u03b2'),  # Î² -> β
        ('\u00ce\u00b3', '\u03b3'),  # Î³ -> γ
        ('\u00ce\u00b4', '\u03b4'),  # Î´ -> δ
        ('\u00ce\u00b8', '\u03b8'),  # Î¸ -> θ
        ('\u00c2', ''),  # Remove standalone Â
    ]
    
    for wrong, correct in replacements:
        text = text.replace(wrong, correct)
    
    return text

# Load questions from CSV
def load_questions(subject):
    """Load questions from CSV file for a given subject"""
    try:
        if not os.path.exists(DATA_FILE):
            print(f"❌ CSV file not found: {DATA_FILE}")
            return []
        
        print(f"📂 Reading CSV: {DATA_FILE}")
        
        # Read CSV with all columns as strings to prevent fractions (e.g. 1/4) 
        # from being misinterpreted as dates or numbers
        df = pd.read_csv(
            DATA_FILE,
            encoding='utf-8',
            on_bad_lines='warn',
            dtype=str
        )
        
        print(f"📊 Total rows in CSV: {len(df)}")
        print(f"📊 Columns: {list(df.columns)}")
        
        # Clean column names
        df.columns = df.columns.str.strip()
        
        # Check Subject column exists
        if 'Subject' not in df.columns:
            print(f"❌ 'Subject' column not found")
            return []
        
        # Show available subjects
        print(f"📚 Subjects in CSV:")
        for subj, count in df['Subject'].value_counts().items():
            print(f"   {subj}: {count} questions")
        
        # Filter by subject (case-insensitive)
        df['Subject'] = df['Subject'].str.strip()
        subject_df = df[df['Subject'].str.lower() == subject.lower().strip()]
        
        if len(subject_df) == 0:
            print(f"⚠️  No questions found for subject: '{subject}'")
            return []
        
        print(f"✅ Found {len(subject_df)} questions for {subject}")
        
        # Convert to list of dictionaries
        questions = subject_df.to_dict('records')
        
        return questions
        
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        import traceback
        traceback.print_exc()
        return []

def log_admin_action(action_type, target_id, details, admin_user='admin'):
    """Log admin actions"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO admin_actions (action_type, target_id, details, admin_user)
            VALUES (?, ?, ?, ?)
        ''', (action_type, target_id, details, admin_user))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging admin action: {e}")

# ============================================================================
# PUBLIC API ENDPOINTS (for students)
# ============================================================================

@app.route('/api/subjects', methods=['GET'])
def get_subjects():
    """Get list of available subjects from the CSV file"""
    try:
        df = pd.read_csv(DATA_FILE, encoding='utf-8', dtype=str)
        # Fix typo in Physics
        df['Subject'] = df['Subject'].str.replace('Physcis', 'Physics', case=False)
        # Fix encoding in subject names
        df['Subject'] = df['Subject'].apply(lambda x: fix_encoding(str(x)) if pd.notna(x) else x)
        subjects = sorted(df['Subject'].unique().tolist())
        return jsonify({'subjects': subjects})
    except Exception as e:
        return jsonify({'subjects': []})

@app.route('/api/ai/<subject>', methods=['GET'])
def get_ai_alias(subject):
    """Alias for /api/questions/ai-live/<subject>"""
    return get_ai_live_questions(subject)

@app.route('/api/questions/ai-live/<subject>', methods=['GET'])
def get_ai_live_questions(subject):
    """Generate 10 fresh questions using AI and return directly for user test"""
    try:
        print(f"\n========================================")
        print(f"🤖 User requested live AI questions for: {subject}")
        print(f"========================================")
        
        generator = QuestionGenerator()
        # Generate 10 questions for speed (user experience)
        raw_questions = generator.generate_questions(subject, count=10)
        
        if not raw_questions:
            print(f"❌ Generation failed: generator.generate_questions returned empty list")
            return jsonify({'error': 'AI failed to generate questions. This might be due to a JSON parsing error or API limit. Please check the terminal logs.'}), 500
        
        # --- NEW: Automatically back up these questions to the DB for later review ---
        try:
            generator.save_questions_to_db(raw_questions, status='pending_review')
        except Exception as save_err:
            print(f"⚠️ Could not backup questions to DB: {save_err}")
        # ----------------------------------------------------------------------------

        formatted_questions = []
        for i, q in enumerate(raw_questions):
            # Create the options array that the frontend expects
            options = [
                q.get('Option A', '').strip(),
                q.get('Option B', '').strip(),
                q.get('Option C', '').strip(),
                q.get('Option D', '').strip()
            ]
            
            # Get the correct answer text
            correct_letter = q.get('Correct Option', 'A').strip().upper()
            letter_to_index = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
            correct_index = letter_to_index.get(correct_letter, 0)
            correct_text = options[correct_index]

            formatted_questions.append({
                'id': i + 1,
                'question': q.get('Question', '').strip(),
                'options': options,
                'option_a': options[0],
                'option_b': options[1],
                'option_c': options[2],
                'option_d': options[3],
                'correct_option': correct_letter,
                'correct_answer': correct_text,
                'explanation': q.get('Explanation', ''),
                'chapter_name': q.get('Chapter Name', 'General'),
                'subject': subject,
                'type': q.get('Type', 'Standard'),
                'source': 'ai_live'
            })
            
        print(f"✅ Successfully generated and returned {len(formatted_questions)} live questions")
        return jsonify({
            'questions': formatted_questions,
            'source': 'ai_live_generation'
        })
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error in live AI generation: {error_msg}")
        
        # Handle specific known errors
        if "Quota Exceeded" in error_msg:
            return jsonify({
                'error': "AI Daily Quota Exceeded. You have used all available AI generations for today. Please wait for the daily reset or try a different subject later.",
                'is_quota_error': True
            }), 429
            
        return jsonify({'error': f"AI Error: {error_msg}"}), 500

@app.route('/api/check')
def check_api():
    return jsonify({'status': 'ok', 'message': 'API is working'})

@app.route('/api/<subject>', methods=['GET'])
def get_questions_alias(subject):
    """Alias for /api/questions/<subject> to make it easier for users"""
    # Redirect if it's not a known standard API route like 'subjects' or 'check'
    if subject in ['subjects', 'check', 'analytics', 'history', 'track']:
        # Let the actual routes handle it if they exist
        return jsonify({'error': f'Route /api/{subject} not found directly'}), 404
        
    return get_questions(subject)

@app.route('/api/questions/<subject>', methods=['GET'])
def get_questions(subject):
    """Get 20 random questions for a subject from CSV Question Bank"""
    try:
        print(f"\n{'='*60}")
        print(f"📚 Loading questions for: {subject}")
        print(f"{'='*60}")
        user_id = request.args.get('user_id')
        recent_uids = set()
        if user_id:
            recent_uids = get_recent_question_uids(user_id, subject, NO_REPEAT_TESTS)

        questions = load_questions(subject)
        
        if not questions:
            print(f"❌ No questions found for subject: {subject}")
            return jsonify({'error': 'No questions found for this subject'}), 404
        
        print(f"✅ Loaded {len(questions)} raw questions from CSV")
        
        import random
        def normalize_option(value, fallback):
            text = str(value or '').strip()
            if not text or text.lower() == 'nan':
                return fallback
            return text

        questions_with_uid = []
        for q in questions:
            question_text = str(q.get('Question', '')).strip()
            option_a = normalize_option(q.get('Option A', ''), 'Option A')
            option_b = normalize_option(q.get('Option B', ''), 'Option B')
            option_c = normalize_option(q.get('Option C', ''), 'Option C')
            option_d = normalize_option(q.get('Option D', ''), 'Option D')
            options = [option_a, option_b, option_c, option_d]
            question_uid = compute_question_uid(subject, question_text, options)
            questions_with_uid.append((question_uid, q))

        eligible_questions = [item for item in questions_with_uid if item[0] not in recent_uids]
        pool = eligible_questions if len(eligible_questions) >= 10 else questions_with_uid
        selected_questions = random.sample(pool, min(20, len(pool)))
        
        formatted_questions = []
        
        for i, item in enumerate(selected_questions):
            try:
                question_uid, q = item
                # Extract fields
                question_text = str(q.get('Question', '')).strip()
                option_a = str(q.get('Option A', '')).strip()
                option_b = str(q.get('Option B', '')).strip()
                option_c = str(q.get('Option C', '')).strip()
                option_d = str(q.get('Option D', '')).strip()
                
                # Now using "Correct Answer" column
                correct_answer_raw = str(q.get('Correct Answer', '')).strip().upper()
                
                # Difficulty column exists but we'll ignore it for now
                # difficulty = str(q.get('Difficulty', '')).strip()
                
                # Debug first question
                if i == 0:
                    print(f"\n📝 Sample question:")
                    print(f"   Question: {question_text[:60]}...")
                    print(f"   Option A: {option_a[:40]}...")
                    print(f"   Option B: {option_b[:40]}...")
                    print(f"   Option C: {option_c[:40]}...")
                    print(f"   Option D: {option_d[:40]}...")
                    print(f"   Correct Answer (raw): '{correct_answer_raw}'")
                
                # Skip if essential data is missing
                if not question_text or question_text.lower() == 'nan':
                    print(f"⚠️  Skipping Q{i+1}: Missing question text")
                    continue
                
                if not correct_answer_raw or correct_answer_raw == 'NAN':
                    print(f"⚠️  Skipping Q{i+1}: Missing correct answer")
                    continue
                
                # Handle empty options
                if not option_a or option_a.lower() == 'nan':
                    option_a = 'Option A'
                if not option_b or option_b.lower() == 'nan':
                    option_b = 'Option B'
                if not option_c or option_c.lower() == 'nan':
                    option_c = 'Option C'
                if not option_d or option_d.lower() == 'nan':
                    option_d = 'Option D'
                
                # Create options array
                options = [option_a, option_b, option_c, option_d]
                
                # Normalize correct answer (handle space before letter: " A" -> "A")
                correct_letter = correct_answer_raw.strip()
                
                # Validate it's A, B, C, or D
                if correct_letter not in ['A', 'B', 'C', 'D']:
                    print(f"⚠️  Skipping Q{i+1}: Invalid correct answer '{correct_answer_raw}' (after strip: '{correct_letter}')")
                    continue
                
                # Get full text of correct answer
                letter_to_index = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                correct_index = letter_to_index[correct_letter]
                correct_text = options[correct_index]
                
                formatted_question = {
                    'id': i,
                    'question': question_text,
                    'options': options,
                    'correct_answer': correct_text,  # Full text for backend comparison
                    'correct_answer_letter': correct_letter,  # Letter for reference
                    'question_type': 'Standard',  # Default type since we're not using Difficulty
                    'question_uid': question_uid
                }
                
                formatted_questions.append(formatted_question)
                
            except Exception as e:
                print(f"⚠️  Error formatting Q{i+1}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n📊 Results:")
        print(f"   Formatted: {len(formatted_questions)} questions")
        print(f"   Skipped: {len(selected_questions) - len(formatted_questions)} questions")
        print(f"{'='*60}\n")
        
        if len(formatted_questions) < 10:
            error_msg = f'Not enough valid questions (found {len(formatted_questions)}, need at least 10)'
            print(f"❌ {error_msg}")
            return jsonify({'error': error_msg}), 404
        
        return jsonify({
            'questions': formatted_questions,
            'source': 'csv_question_bank'
        })
        
    except Exception as e:
        print(f"❌ Error loading questions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/questions/genai/<subject>', methods=['GET'])
def get_genai_questions(subject):
    """Generate 20 questions using GenAI and save for admin review"""
    try:
        generator = QuestionGenerator()
        questions = generator.generate_questions(subject)
        
        if not questions:
            return jsonify({'error': 'Failed to generate questions'}), 500
        
        # Use the generator's robust save method
        success = generator.save_questions_to_db(questions, status='pending_review')
        
        if success:
            saved_count = len(questions)
            log_admin_action('ai_generation', None, 
                            f'Generated {saved_count} questions for {subject}', 'system')
            
            return jsonify({
                'message': f'Successfully generated {saved_count} questions',
                'status': 'pending_review',
                'note': 'Questions are pending admin review before being added to question bank',
                'question_count': saved_count,
                'subject': subject,
                'instruction': 'Go to Admin Panel to review and approve these questions'
            })
        else:
            return jsonify({'error': 'Failed to save generated questions to database'}), 500
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error in GenAI generation: {error_msg}")
        
        if 'quota' in error_msg.lower() or 'RESOURCE_EXHAUSTED' in error_msg:
            return jsonify({
                'error': 'Gemini API rate limit exceeded',
                'message': 'Please wait 1-2 minutes and try again, or use Question Bank mode instead.',
                'suggestion': 'Switch to Question Bank (📚) for immediate access to 2000+ questions'
            }), 429
        else:
            return jsonify({'error': error_msg}), 500

@app.route('/api/submit', methods=['POST'])
def submit_test():
    """Submit test and calculate results"""
    print("\n" + "="*50)
    print("📥 TEST SUBMISSION RECEIVED")
    print("="*50)
    try:
        data = request.json
        if not data:
            print("❌ Error: No JSON data received")
            return jsonify({'error': 'No data received'}), 400
            
        subject = data.get('subject')
        answers = data.get('answers')
        user_id = data.get('user_id', 'anonymous')
        user_name = data.get('user_name', 'Anonymous')
        duration_seconds = data.get('duration_seconds')
        
        print(f"👤 User: {user_name} ({user_id})")
        print(f"📚 Subject: {subject}")
        print(f"⏱️ Duration: {duration_seconds}s")
        print(f"📝 Questions: {len(answers) if answers else 0}")
        
        if not subject or not answers:
            print("❌ Invalid request: missing subject or answers")
            return jsonify({'error': 'Invalid request'}), 400
        
        total_questions = len(answers)
        correct_count = 0
        results = []
        
        for i, answer in enumerate(answers):
            user_answer_letter = str(answer.get('user_answer', 'Not Answered')).strip().upper()
            correct_answer_text = str(answer.get('correct_answer', '')).strip()
            
            # Get the options for this question
            question_data = answer.get('question_data', {})
            options = question_data.get('options', [])
            
            # Map letters to options
            letter_to_index = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
            
            # --- AI Mode Fix: Map correct_option to correct_answer_text if missing ---
            if not correct_answer_text:
                correct_letter_ai = question_data.get('correct_option', 'A').strip().upper()
                idx_ai = letter_to_index.get(correct_letter_ai, 0)
                if idx_ai < len(options):
                    correct_answer_text = options[idx_ai].strip()
            # -----------------------------------------------------------------------

            # Convert user's letter to actual option text
            user_answer_text = user_answer_letter
            if user_answer_letter in ['A', 'B', 'C', 'D'] and options:
                option_index = letter_to_index.get(user_answer_letter)
                if option_index is not None and option_index < len(options):
                    user_answer_text = options[option_index].strip()
            
            # Find which letter corresponds to the correct answer
            correct_answer_letter = None
            for letter, index in letter_to_index.items():
                if index < len(options):
                    if options[index].strip().lower() == correct_answer_text.lower():
                        correct_answer_letter = letter
                        break
            
            # If correct answer wasn't found in options, check if it's already a letter
            if not correct_answer_letter and correct_answer_text.upper() in ['A', 'B', 'C', 'D']:
                correct_answer_letter = correct_answer_text.upper()
                option_index = letter_to_index.get(correct_answer_letter)
                if option_index is not None and option_index < len(options):
                    correct_answer_text = options[option_index].strip()
            
            print(f"\nQ{i+1}:")
            print(f"  User: {user_answer_letter} → {user_answer_text}")
            print(f"  Correct: {correct_answer_letter} → {correct_answer_text}")
            
            # Compare the actual text (case-insensitive)
            is_correct = user_answer_text.lower().strip() == correct_answer_text.lower().strip()
            print(f"  Match: {is_correct}")

            question_uid = question_data.get('question_uid')
            if not question_uid:
                question_uid = compute_question_uid(subject, answer.get('question', ''), options)
            
            if is_correct:
                correct_count += 1
            
            results.append({
                'question': answer['question'],
                'user_answer_letter': user_answer_letter,  # A, B, C, D or Not Answered
                'user_answer_text': user_answer_text,      # Full text of option
                'correct_answer_letter': correct_answer_letter or '?',  # A, B, C, D
                'correct_answer_text': correct_answer_text,  # Full text
                'is_correct': is_correct,
                'all_options': options,  # Include all options for reference
                'question_uid': question_uid
            })
        
        score = (correct_count / total_questions) * 100
        print(f"\n✅ Final Score: {correct_count}/{total_questions} = {score}%\n")
        
        # Save to database
        print(f"💾 Saving to DB: {DB_FILE}")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("📝 Inserting into test_history...")
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO test_history (subject, total_questions, correct_answers, score, user_id, user_name)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id
            ''', (subject, total_questions, correct_count, score, user_id, user_name))
            test_id = cursor.fetchone()[0]
        else:
            cursor.execute('''
                INSERT INTO test_history (subject, total_questions, correct_answers, score, user_id, user_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (subject, total_questions, correct_count, score, user_id, user_name))
            test_id = cursor.lastrowid
        print(f"✅ Generated Test ID: {test_id}")
        
        # Save individual question results
        print("📝 Inserting question results...")
        for result in results:
            cursor.execute('''
                INSERT INTO question_history (test_id, question, user_answer, correct_answer, is_correct, question_uid)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                test_id, 
                result['question'], 
                f"{result['user_answer_letter']}) {result['user_answer_text']}", 
                f"{result['correct_answer_letter']}) {result['correct_answer_text']}", 
                result['is_correct'],
                result.get('question_uid')
            ))
        
        conn.commit()
        conn.close()
        print("✅ Database commit successful")
        
        # Try to log tracking
        try:
            if user_id and user_id != 'anonymous':
                log_test_attempt(user_id, user_name, subject, test_id, score, duration_seconds)
                log_visitor(user_id, user_name, 'test_completed', f'test-{subject}')
        except Exception as tracking_error:
            print(f"⚠️ Tracking failed: {tracking_error}")
        
        return jsonify({
            'test_id': test_id,
            'total_questions': total_questions,
            'correct_answers': correct_count,
            'score': score,
            'results': results,
            'source': data.get('source') # Include source in response
        })
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get test history"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, subject, total_questions, correct_answers, score, timestamp
        FROM test_history
        WHERE user_id = ?
        ORDER BY timestamp DESC
    ''', (user_id,))
    
    history = []
    for idx, row in enumerate(cursor.fetchall(), 1):
        timestamp = format_timestamp(row[5])
        history.append({
            'test_no': idx,
            'date': timestamp.strftime('%d-%b-%Y'),
            'time': timestamp.strftime('%I:%M %p'),
            'subject': row[1],
            'score': f"{row[4]:.1f}%",
            'id': row[0],
            'total_questions': row[2],
            'correct_answers': row[3]
        })
    
    conn.close()
    return jsonify({'history': history})

@app.route('/api/admin/history', methods=['GET'])
def get_admin_history():
    """Get test history for all users (admin)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, subject, total_questions, correct_answers, score, timestamp, user_id, user_name
        FROM test_history
        ORDER BY timestamp DESC
    ''')

    history = []
    for idx, row in enumerate(cursor.fetchall(), 1):
        timestamp = format_timestamp(row[5])
        history.append({
            'test_no': idx,
            'date': timestamp.strftime('%d-%b-%Y'),
            'time': timestamp.strftime('%I:%M %p'),
            'subject': row[1],
            'score': f"{row[4]:.1f}%",
            'id': row[0],
            'total_questions': row[2],
            'correct_answers': row[3],
            'user_id': row[6],
            'user_name': row[7]
        })

    conn.close()
    return jsonify({'history': history})

@app.route('/api/history/<int:test_id>', methods=['GET'])
def get_test_details(test_id):
    """Get detailed results for a specific test"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get test info
    cursor.execute('''
        SELECT subject, total_questions, correct_answers, score, timestamp
        FROM test_history
        WHERE id = ? AND user_id = ?
    ''', (test_id, user_id))
    
    test_info = cursor.fetchone()
    if not test_info:
        conn.close()
        return jsonify({'error': 'Test not found'}), 404
    
    # Get question details
    cursor.execute('''
        SELECT question, user_answer, correct_answer, is_correct
        FROM question_history
        WHERE test_id = ?
    ''', (test_id,))
    
    questions = []
    for row in cursor.fetchall():
        questions.append({
            'question': row[0],
            'user_answer': row[1],
            'correct_answer': row[2],
            'is_correct': bool(row[3])
        })
    
    conn.close()
    
    return jsonify({
        'test_info': {
            'subject': test_info[0],
            'total_questions': test_info[1],
            'correct_answers': test_info[2],
            'score': test_info[3],
            'timestamp': test_info[4]
        },
        'questions': questions
    })
@app.route('/api/track/visit', methods=['POST'])
def track_visit():
    """Track page visit"""
    data = request.json
    user_id = data.get('user_id')
    user_name = data.get('user_name', 'Anonymous')
    page = data.get('page', 'unknown')
    
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    
    # Log the visit
    log_visitor(user_id, user_name, 'page_visit', page)
    
    # Update session
    update_user_session(user_id, user_name)
    
    return jsonify({
        'message': 'Visit tracked',
        'user_id': user_id,
        'page': page,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/track/test-start', methods=['POST'])
def track_test_start():
    """Track when user starts a test"""
    data = request.json
    user_id = data.get('user_id')
    user_name = data.get('user_name', 'Anonymous')
    subject = data.get('subject')
    
    if not user_id or not subject:
        return jsonify({'error': 'user_id and subject required'}), 400
    
    log_visitor(user_id, user_name, 'test_start', f'test-{subject}')
    
    return jsonify({
        'message': 'Test start tracked',
        'user_id': user_id,
        'subject': subject,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/admin/users', methods=['GET'])
def get_all_users():
    """Get all tracked users"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, user_name, first_visit, last_visit, total_visits, total_tests, is_active
        FROM user_sessions
        ORDER BY last_visit DESC
    ''')
    
    users = []
    for row in cursor.fetchall():
        users.append({
            'user_id': row[0],
            'user_name': row[1],
            'first_visit': row[2],
            'last_visit': row[3],
            'total_visits': row[4],
            'total_tests': row[5],
            'is_active': bool(row[6])
        })
    
    conn.close()
    return jsonify({'users': users, 'count': len(users)})

@app.route('/api/admin/visitor-logs', methods=['GET'])
def get_visitor_logs():
    """Get all visitor logs"""
    limit = request.args.get('limit', 100, type=int)
    user_id = request.args.get('user_id', None)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute('''
            SELECT id, user_id, user_name, visit_type, page_visited, ip_address, timestamp
            FROM visitor_logs
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
    else:
        cursor.execute('''
            SELECT id, user_id, user_name, visit_type, page_visited, ip_address, timestamp
            FROM visitor_logs
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
    
    logs = []
    for row in cursor.fetchall():
        logs.append({
            'id': row[0],
            'user_id': row[1],
            'user_name': row[2],
            'visit_type': row[3],
            'page_visited': row[4],
            'ip_address': row[5],
            'timestamp': row[6]
        })
    
    conn.close()
    return jsonify({'logs': logs, 'count': len(logs)})

@app.route('/api/admin/test-attempts', methods=['GET'])
def get_test_attempts():
    """Get all test attempts"""
    user_id = request.args.get('user_id', None)
    subject = request.args.get('subject', None)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    query = '''
        SELECT id, user_id, user_name, subject, test_id, score, duration_seconds, timestamp
        FROM test_attempts
        WHERE 1=1
    '''
    params = []
    
    if user_id:
        query += ' AND user_id = ?'
        params.append(user_id)
    
    if subject:
        query += ' AND subject = ?'
        params.append(subject)
    
    query += ' ORDER BY timestamp DESC'
    
    cursor.execute(query, params)
    
    attempts = []
    for row in cursor.fetchall():
        attempts.append({
            'id': row[0],
            'user_id': row[1],
            'user_name': row[2],
            'subject': row[3],
            'test_id': row[4],
            'score': row[5],
            'duration_seconds': row[6],
            'timestamp': row[7]
        })
    
    conn.close()
    return jsonify({'attempts': attempts, 'count': len(attempts)})

@app.route('/api/admin/user-stats/<user_id>', methods=['GET'])
def get_user_stats(user_id):
    """Get detailed stats for a specific user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get user info
    cursor.execute('SELECT * FROM user_sessions WHERE user_id = ?', (user_id,))
    user_row = cursor.fetchone()
    
    if not user_row:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    # Get test attempts
    cursor.execute('''
        SELECT subject, AVG(score) as avg_score, COUNT(*) as attempts, MAX(score) as best_score
        FROM test_attempts
        WHERE user_id = ?
        GROUP BY subject
    ''', (user_id,))
    
    subject_stats = []
    for row in cursor.fetchall():
        subject_stats.append({
            'subject': row[0],
            'avg_score': round(row[1], 2),
            'attempts': row[2],
            'best_score': row[3]
        })
    
    # Get recent activity
    cursor.execute('''
        SELECT visit_type, page_visited, timestamp
        FROM visitor_logs
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT 10
    ''', (user_id,))
    
    recent_activity = []
    for row in cursor.fetchall():
        recent_activity.append({
            'visit_type': row[0],
            'page_visited': row[1],
            'timestamp': row[2]
        })
    
    conn.close()
    
    return jsonify({
        'user_info': {
            'user_id': user_row[1],
            'user_name': user_row[2],
            'first_visit': user_row[3],
            'last_visit': user_row[4],
            'total_visits': user_row[5],
            'total_tests': user_row[6]
        },
        'subject_stats': subject_stats,
        'recent_activity': recent_activity
    })

@app.route('/api/admin/analytics', methods=['GET'])
def get_analytics():
    """Get overall analytics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Total users
    cursor.execute('SELECT COUNT(*) FROM user_sessions')
    total_users = cursor.fetchone()[0]
    
    # Total visits
    cursor.execute('SELECT COUNT(*) FROM visitor_logs')
    total_visits = cursor.fetchone()[0]
    
    # Total tests
    cursor.execute('SELECT COUNT(*) FROM test_attempts')
    total_tests = cursor.fetchone()[0]
    
    # Average score
    cursor.execute('SELECT AVG(score) FROM test_attempts')
    avg_score = cursor.fetchone()[0] or 0
    
    # Tests by subject
    cursor.execute('''
        SELECT subject, COUNT(*) as count, AVG(score) as avg_score
        FROM test_attempts
        GROUP BY subject
    ''')
    
    subject_breakdown = []
    for row in cursor.fetchall():
        subject_breakdown.append({
            'subject': row[0],
            'total_tests': row[1],
            'avg_score': round(row[2], 2)
        })
    
    # Recent users (last 24 hours)
    if USE_POSTGRES:
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id)
            FROM visitor_logs
            WHERE timestamp >= NOW() - INTERVAL '1 day'
        ''')
    else:
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id)
            FROM visitor_logs
            WHERE timestamp >= datetime('now', '-1 day')
        ''')
    active_users_24h = cursor.fetchone()[0]
    
    # Top performers
    cursor.execute('''
        SELECT user_id, user_name, AVG(score) as avg_score, COUNT(*) as tests
        FROM test_attempts
        GROUP BY user_id, user_name
        ORDER BY avg_score DESC
        LIMIT 5
    ''')
    
    top_performers = []
    for row in cursor.fetchall():
        top_performers.append({
            'user_id': row[0],
            'user_name': row[1],
            'avg_score': round(row[2], 2),
            'total_tests': row[3]
        })
    
    conn.close()
    
    return jsonify({
        'overview': {
            'total_users': total_users,
            'total_visits': total_visits,
            'total_tests': total_tests,
            'avg_score': round(avg_score, 2),
            'active_users_24h': active_users_24h
        },
        'subject_breakdown': subject_breakdown,
        'top_performers': top_performers
    })
# ============================================================================
# ADMIN API ENDPOINTS (for question review)
# ============================================================================

@app.route('/api/admin/generate/<subject>', methods=['POST'])
def admin_generate_questions(subject):
    """Admin endpoint to trigger AI generation"""
    try:
        generator = QuestionGenerator()
        questions = generator.generate_questions(subject)
        
        if not questions:
            return jsonify({'error': 'Failed to generate questions'}), 500
        
        # Use the generator's robust save method
        success = generator.save_questions_to_db(questions, status='pending_review')
        
        if success:
            saved_count = len(questions)
            log_admin_action('admin_generation', None, 
                            f'Admin generated {saved_count} questions for {subject}')
            
            return jsonify({
                'message': f'Generated {saved_count} questions for review',
                'question_count': saved_count,
                'status': 'pending_review'
            })
        else:
            return jsonify({'error': 'Failed to save questions to review bank'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/pending-questions', methods=['GET'])
def get_pending_questions():
    """Get all pending review questions"""
    subject = request.args.get('subject', None)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if subject:
        cursor.execute('''
            SELECT id, subject, question, option_a, option_b, option_c, option_d, 
                   correct_option, question_type, created_at, status, chapter_name, explanation
            FROM newly_updated_questions
            WHERE status = 'pending_review' AND subject = ? AND is_active = 1
            ORDER BY created_at DESC
        ''', (subject,))
    else:
        cursor.execute('''
            SELECT id, subject, question, option_a, option_b, option_c, option_d, 
                   correct_option, question_type, created_at, status, chapter_name, explanation
            FROM newly_updated_questions
            WHERE status = 'pending_review' AND is_active = 1
            ORDER BY created_at DESC
        ''')
    
    questions = []
    for row in cursor.fetchall():
        questions.append({
            'id': row[0],
            'subject': row[1],
            'question': row[2],
            'option_a': row[3],
            'option_b': row[4],
            'option_c': row[5],
            'option_d': row[6],
            'correct_option': row[7],
            'question_type': row[8],
            'created_at': row[9],
            'status': row[10],
            'chapter_name': row[11] if len(row) > 11 else 'General',
            'explanation': row[12] if len(row) > 12 else ''
        })
    
    conn.close()
    return jsonify({'pending_questions': questions, 'count': len(questions)})

@app.route('/api/admin/approve-question/<int:question_id>', methods=['POST'])
def approve_question(question_id):
    """Approve a single question and add to CSV Question Bank"""
    data = request.json
    admin_user = data.get('admin_user', 'admin')
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get the question
    cursor.execute('''
        SELECT subject, question, option_a, option_b, option_c, option_d, correct_option
        FROM newly_updated_questions
        WHERE id = ? AND status = 'pending_review'
    ''', (question_id,))
    
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error': 'Question not found or already processed'}), 404
    
    # Update status in database
    cursor.execute('''
        UPDATE newly_updated_questions
        SET status = 'approved',
            reviewed_at = CURRENT_TIMESTAMP,
            reviewed_by = ?
        WHERE id = ?
    ''', (admin_user, question_id))
    
    conn.commit()
    conn.close()
    
    # Add to main CSV file
    try:
        df = pd.read_csv(DATA_FILE, encoding='utf-8', dtype=str)
        
        new_question = pd.DataFrame([{
            'Subject': row[0],
            'Question': row[1],
            'Option A': row[2],
            'Option B': row[3],
            'Option C': row[4],
            'Option D': row[5],
            'Correct Option': row[6]
        }])
        
        df = pd.concat([df, new_question], ignore_index=True)
        df.to_csv(DATA_FILE, index=False, encoding='utf-8')
        
        log_admin_action('approve_question', question_id, 
                        f'Approved and added to CSV by {admin_user}', admin_user)
        
        print(f"✅ Question {question_id} approved and added to CSV by {admin_user}")
        
        return jsonify({
            'message': 'Question approved and added to main question bank (CSV)',
            'question_id': question_id
        })
        
    except Exception as e:
        print(f"❌ Error adding to CSV: {e}")
        return jsonify({'error': f'Failed to add to CSV: {str(e)}'}), 500

@app.route('/api/admin/approve-bulk', methods=['POST'])
def approve_bulk_questions():
    """Approve multiple questions at once"""
    data = request.json
    question_ids = data.get('question_ids', [])
    admin_user = data.get('admin_user', 'admin')
    
    if not question_ids:
        return jsonify({'error': 'No question IDs provided'}), 400
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    approved_questions = []
    
    for qid in question_ids:
        # Get the question
        cursor.execute('''
            SELECT subject, question, option_a, option_b, option_c, option_d, correct_option
            FROM newly_updated_questions
            WHERE id = ? AND status = 'pending_review'
        ''', (qid,))
        
        row = cursor.fetchone()
        
        if row:
            # Update status
            cursor.execute('''
                UPDATE newly_updated_questions
                SET status = 'approved',
                    reviewed_at = CURRENT_TIMESTAMP,
                    reviewed_by = ?
                WHERE id = ?
            ''', (admin_user, qid))
            
            approved_questions.append({
                'Subject': row[0],
                'Question': row[1],
                'Option A': row[2],
                'Option B': row[3],
                'Option C': row[4],
                'Option D': row[5],
                'Correct Option': row[6]
            })
    
    conn.commit()
    conn.close()
    
    # Add all approved questions to CSV
    if approved_questions:
        try:
            df = pd.read_csv(DATA_FILE, encoding='utf-8', dtype=str)
            new_df = pd.DataFrame(approved_questions)
            df = pd.concat([df, new_df], ignore_index=True)
            df.to_csv(DATA_FILE, index=False, encoding='utf-8')
            
            log_admin_action('bulk_approve', None, 
                            f'Bulk approved {len(approved_questions)} questions by {admin_user}', 
                            admin_user)
            
            print(f"✅ Bulk approved {len(approved_questions)} questions")
            
            return jsonify({
                'message': f'Successfully approved {len(approved_questions)} questions',
                'approved_count': len(approved_questions)
            })
        except Exception as e:
            return jsonify({'error': f'Failed to add to CSV: {str(e)}'}), 500
    else:
        return jsonify({'error': 'No valid questions to approve'}), 400

@app.route('/api/admin/upload-csv', methods=['POST'])
def upload_csv_questions():
    """Upload a CSV file and append questions to the main question bank"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    upload_file = request.files['file']
    if not upload_file or upload_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    admin_user = request.form.get('admin_user', 'admin')

    try:
        try:
            df_upload = pd.read_csv(upload_file, dtype=str, encoding='utf-8')
        except UnicodeDecodeError:
            df_upload = pd.read_csv(upload_file, dtype=str, encoding='utf-8-sig')

        if df_upload.empty:
            return jsonify({'error': 'Uploaded CSV is empty'}), 400

        def normalize_col(name):
            import re
            text = str(name).strip().lower()
            text = text.replace('_', '').replace(' ', '')
            return re.sub(r'[^a-z0-9]', '', text)

        col_map = {normalize_col(col): col for col in df_upload.columns}
        required = {
            'subject': 'Subject',
            'question': 'Question',
            'optiona': 'Option A',
            'optionb': 'Option B',
            'optionc': 'Option C',
            'optiond': 'Option D',
            'correctoption': 'Correct Option'
        }

        missing = [name for key, name in required.items() if key not in col_map]
        if missing:
            return jsonify({
                'error': f"Missing required columns: {', '.join(missing)}"
            }), 400

        df_normalized = df_upload[[
            col_map['subject'],
            col_map['question'],
            col_map['optiona'],
            col_map['optionb'],
            col_map['optionc'],
            col_map['optiond'],
            col_map['correctoption']
        ]].copy()

        df_normalized.columns = [
            'Subject',
            'Question',
            'Option A',
            'Option B',
            'Option C',
            'Option D',
            'Correct Option'
        ]

        for col in df_normalized.columns:
            df_normalized[col] = df_normalized[col].fillna('').astype(str).str.strip()

        df_normalized = df_normalized[
            (df_normalized['Subject'] != '') & (df_normalized['Question'] != '')
        ]

        if df_normalized.empty:
            return jsonify({'error': 'No valid rows found after cleaning'}), 400

        # Insert each question into newly_updated_questions with status 'pending_review'
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        inserted = 0
        for _, row in df_normalized.iterrows():
            try:
                cursor.execute('''
                    INSERT INTO newly_updated_questions
                    (subject, question, option_a, option_b, option_c, option_d, correct_option, question_type, status, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['Subject'],
                    row['Question'],
                    row['Option A'],
                    row['Option B'],
                    row['Option C'],
                    row['Option D'],
                    row['Correct Option'],
                    'Standard',
                    'pending_review',
                    'csv'
                ))
                inserted += 1
            except Exception as e:
                print(f"Error inserting question from CSV: {e}")
        conn.commit()
        conn.close()

        log_admin_action('csv_upload', None,
                         f'Uploaded {inserted} questions to pending review', admin_user)

        return jsonify({
            'message': 'CSV uploaded. All questions are now pending for review.',
            'added_count': inserted
        })
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/admin/reject-question/<int:question_id>', methods=['POST'])
def reject_question(question_id):
    """Reject a question (soft delete)"""
    data = request.json
    admin_user = data.get('admin_user', 'admin')
    reason = data.get('reason', 'No reason provided')
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE newly_updated_questions
        SET status = 'rejected',
            is_active = 0,
            reviewed_at = CURRENT_TIMESTAMP,
            reviewed_by = ?,
            review_notes = ?
        WHERE id = ?
    ''', (admin_user, reason, question_id))
    
    conn.commit()
    conn.close()
    
    log_admin_action('reject_question', question_id, 
                    f'Rejected by {admin_user}: {reason}', admin_user)
    
    return jsonify({
        'message': 'Question rejected',
        'question_id': question_id
    })

@app.route('/api/admin/edit-question/<int:question_id>', methods=['PUT'])
def edit_question(question_id):
    """Edit a question before approval"""
    data = request.json
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE newly_updated_questions
        SET question = ?,
            option_a = ?,
            option_b = ?,
            option_c = ?,
            option_d = ?,
            correct_option = ?,
            question_type = ?
        WHERE id = ?
    ''', (
        data.get('question'),
        data.get('option_a'),
        data.get('option_b'),
        data.get('option_c'),
        data.get('option_d'),
        data.get('correct_option'),
        data.get('question_type'),
        question_id
    ))
    
    conn.commit()
    conn.close()
    
    log_admin_action('edit_question', question_id, 
                    'Question edited before approval', 
                    data.get('admin_user', 'admin'))
    
    return jsonify({
        'message': 'Question updated successfully',
        'question_id': question_id
    })

@app.route('/api/admin/approved-questions', methods=['GET'])
def get_approved_questions():
    """Get all approved questions that were added to CSV"""
    subject = request.args.get('subject', None)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if subject:
        cursor.execute('''
            SELECT id, subject, question, option_a, option_b, option_c, option_d,
                   correct_option, question_type, reviewed_at, reviewed_by
            FROM newly_updated_questions
            WHERE status = 'approved' AND subject = ? AND is_active = 1
            ORDER BY reviewed_at DESC
        ''', (subject,))
    else:
        cursor.execute('''
            SELECT id, subject, question, option_a, option_b, option_c, option_d,
                   correct_option, question_type, reviewed_at, reviewed_by
            FROM newly_updated_questions
            WHERE status = 'approved' AND is_active = 1
            ORDER BY reviewed_at DESC
        ''')
    
    questions = []
    for row in cursor.fetchall():
        questions.append({
            'id': row[0],
            'subject': row[1],
            'question': row[2],
            'option_a': row[3],
            'option_b': row[4],
            'option_c': row[5],
            'option_d': row[6],
            'correct_option': row[7],
            'question_type': row[8],
            'reviewed_at': row[9],
            'reviewed_by': row[10]
        })
    
    conn.close()
    return jsonify({'approved_questions': questions, 'count': len(questions)})

@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """Get statistics for admin dashboard"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get subjects from CSV
    def normalize_subject_key(value):
        import re
        text = str(value or '')
        text = text.replace('\ufeff', '').replace('\u200b', '').replace('\u00a0', ' ')
        text = re.sub(r'\s+', '', text.strip().lower())
        text = re.sub(r'[^a-z0-9]', '', text)
        return text

    subject_labels = {}
    try:
        df = pd.read_csv(DATA_FILE, encoding='utf-8', dtype=str)
        df['Subject'] = df['Subject'].str.replace('Physcis', 'Physics', case=False)
        df['Subject'] = df['Subject'].fillna('').astype(str)

        for subject in df['Subject'].tolist():
            if not subject:
                continue
            cleaned = subject.replace('\ufeff', '').replace('\u200b', '').replace('\u00a0', ' ').strip()
            key = normalize_subject_key(cleaned)
            if key and key not in subject_labels:
                subject_labels[key] = cleaned
    except Exception:
        subject_labels = {
            'physics': 'Physics',
            'chemistry': 'Chemistry',
            'maths': 'Maths',
            'biology': 'Biology'
        }

    cursor.execute('''
        SELECT subject, status, COUNT(*)
        FROM newly_updated_questions
        WHERE is_active = 1
        GROUP BY subject, status
    ''')

    stats_by_key = {}
    for row in cursor.fetchall():
        subject_raw = row[0]
        status = row[1]
        count = row[2]
        key = normalize_subject_key(subject_raw)
        if not key:
            continue
        if key not in stats_by_key:
            stats_by_key[key] = {'pending': 0, 'approved': 0, 'rejected': 0}
        if status == 'pending_review':
            stats_by_key[key]['pending'] += count
        elif status == 'approved':
            stats_by_key[key]['approved'] += count
        elif status == 'rejected':
            stats_by_key[key]['rejected'] += count

    # Ensure every CSV subject shows up at least once
    for key in subject_labels.keys():
        stats_by_key.setdefault(key, {'pending': 0, 'approved': 0, 'rejected': 0})

    canonical_labels = {
        key: (label or '').replace('\ufeff', '').replace('\u200b', '').replace('\u00a0', ' ').strip()
        for key, label in subject_labels.items()
        if key
    }

    stats = {}
    for key in sorted(stats_by_key.keys()):
        label = canonical_labels.get(key) or key.title()
        counts = stats_by_key.get(key, {'pending': 0, 'approved': 0, 'rejected': 0})
        if label not in stats:
            stats[label] = {
                'pending': counts['pending'],
                'approved': counts['approved'],
                'rejected': counts['rejected'],
                'total': counts['pending'] + counts['approved']
            }
        else:
            stats[label]['pending'] += counts['pending']
            stats[label]['approved'] += counts['approved']
            stats[label]['rejected'] += counts['rejected']
            stats[label]['total'] = stats[label]['pending'] + stats[label]['approved']

    # Final cleanup: merge by trimmed label and drop zero-total entries
    merged_stats = {}
    for label, counts in stats.items():
        clean_label = str(label).replace('\ufeff', '').replace('\u200b', '').replace('\u00a0', ' ').strip()
        if counts.get('total', 0) == 0 and counts.get('pending', 0) == 0 and counts.get('approved', 0) == 0:
            continue
        if clean_label not in merged_stats:
            merged_stats[clean_label] = counts
        else:
            merged_stats[clean_label]['pending'] += counts.get('pending', 0)
            merged_stats[clean_label]['approved'] += counts.get('approved', 0)
            merged_stats[clean_label]['rejected'] += counts.get('rejected', 0)
            merged_stats[clean_label]['total'] = (
                merged_stats[clean_label]['pending'] + merged_stats[clean_label]['approved']
            )
    
    conn.close()
    return jsonify({'stats': merged_stats})

@app.route('/api/admin/actions', methods=['GET'])
def get_admin_actions():
    """Get recent admin actions log"""
    limit = request.args.get('limit', 50, type=int)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT action_type, target_id, details, admin_user, timestamp
        FROM admin_actions
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    
    actions = []
    for row in cursor.fetchall():
        actions.append({
            'action_type': row[0],
            'target_id': row[1],
            'details': row[2],
            'admin_user': row[3],
            'timestamp': row[4]
        })
    
    conn.close()
    return jsonify({'actions': actions, 'count': len(actions)})

@app.before_request
def log_request_info():
    print(f"📡 Incoming Request: {request.method} {request.path}")

@app.route('/api/admin/verify-with-ai', methods=['POST'])
def verify_with_ai():
    """Verify a question's answer using Gemini AI"""
    print("\n" + "!"*40)
    print("🔥 DEBUG: VERIFY_WITH_AI CALLED!")
    print(f"📦 Data: {request.data}")
    print("!"*40 + "\n")
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No input data provided'}), 200
            
        print(f"🔍 AI Verification Request Received")
        question_text = data.get('question')
        options = data.get('options')
        suggested_answer = data.get('suggested_answer')
        
        if not question_text or not options:
            return jsonify({'success': False, 'error': 'Missing question or options'}), 200
            
        generator = QuestionGenerator()
        ai_result = generator.verify_answer(question_text, options, suggested_answer)
        
        if not ai_result:
            return jsonify({
                'success': False,
                'status': 'error',
                'error': 'AI verification failed to return analysis'
            }), 200
            
        # Success response
        return jsonify({
            'success': True,
            'status': 'success',
            'analysis': {
                'is_correct': ai_result.get('is_correct', False),
                'correct_option': ai_result.get('correct_option', 'A'),
                'explanation': ai_result.get('explanation', 'No explanation provided')
            },
            # Backwards compatibility for older frontend versions
            'is_correct': ai_result.get('is_correct', False),
            'ai_correct_option': ai_result.get('correct_option', 'A'),
            'explanation': ai_result.get('explanation', 'No explanation provided')
        })
    except Exception as e:
        import traceback
        error_msg = f"❌ Verification error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({
            'success': False,
            'status': 'error',
            'error': str(e)
        }), 200

# ============================================================================
# FRONTEND ROUTES
# ============================================================================

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.errorhandler(404)
def page_not_found(e):
    # Log the requested path to help debug 404 errors
    requested_path = request.path
    print(f"🔍 404 ERROR: Requested path '{requested_path}' not found among defined routes.")
    
    # Check if it's an API route
    if requested_path.startswith('/api/'):
        return jsonify({
            'error': 'API route not found', 
            'path': requested_path,
            'suggestion': f'Try /api/questions/{requested_path.split("/")[-1]} for bank or /api/ai/{requested_path.split("/")[-1]} for AI generation'
        }), 404
        
    return send_from_directory(app.static_folder, 'index.html'), 404

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 ICSE Grade 10 MCQ Test Application")
    print("="*70)
    print("📚 Question Bank: CSV (2000+ questions)")
    print("🤖 AI Generation: Gemini API → Pending Review → Approved → CSV")
    print("🔧 Admin Panel: /admin.html")
    print("👥 Student Portal: /")
    print("="*70 + "\n")
    
    # Use 0.0.0.0 to allow external access
    app.run(host='0.0.0.0', port=PORT, debug=False)