from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pandas as pd
import random
import sqlite3
from datetime import datetime
import os
from question_generator import QuestionGenerator

# Get the port from environment (Replit uses dynamic ports)
PORT = int(os.environ.get('PORT', 5001))

# Update CORS to allow Replit domain
app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuration
DATA_FILE = 'data/MCQ_Quesbank.csv'
DB_FILE = 'data/history.db'

# Initialize database
def init_db():
    if not os.path.exists('data'):
        os.makedirs('data')
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Existing test history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            total_questions INTEGER NOT NULL,
            correct_answers INTEGER NOT NULL,
            score REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Existing question history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS question_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            user_answer TEXT,
            correct_answer TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL,
            FOREIGN KEY (test_id) REFERENCES test_history(id)
        )
    ''')
    
    # NEW: AI-generated questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_generated_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL,
            question_type TEXT DEFAULT 'Standard',
            status TEXT DEFAULT 'pending_review',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            reviewed_at DATETIME DEFAULT NULL,
            reviewed_by TEXT DEFAULT NULL,
            is_active BOOLEAN DEFAULT 1,
            review_notes TEXT DEFAULT NULL
        )
    ''')
    
    # NEW: Admin actions log
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
    
    conn.commit()
    conn.close()

init_db()

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
def load_questions(subject=None):
    try:
        df = pd.read_csv(DATA_FILE, encoding='utf-8')
        # Fix typo in Physics
        df['Subject'] = df['Subject'].str.replace('Physcis', 'Physics', case=False)
        # Fix encoding issues in all text columns
        text_columns = ['Question', 'Option A', 'Option B', 'Option C', 'Option D', 'Subject']
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: fix_encoding(str(x)) if pd.notna(x) else x)
        if subject:
            df = df[df['Subject'].str.lower() == subject.lower()]
        return df.to_dict('records')
    except FileNotFoundError:
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
        df = pd.read_csv(DATA_FILE, encoding='utf-8')
        # Fix typo in Physics
        df['Subject'] = df['Subject'].str.replace('Physcis', 'Physics', case=False)
        # Fix encoding in subject names
        df['Subject'] = df['Subject'].apply(lambda x: fix_encoding(str(x)) if pd.notna(x) else x)
        subjects = sorted(df['Subject'].unique().tolist())
        return jsonify({'subjects': subjects})
    except Exception as e:
        return jsonify({'subjects': []})

@app.route('/api/questions/<subject>', methods=['GET'])
def get_questions(subject):
    """Get 20 random questions for a subject from CSV Question Bank"""
    questions = load_questions(subject)
    
    if not questions:
        return jsonify({'error': 'No questions found for this subject'}), 404
    
    # Randomly select 20 questions
    selected_questions = random.sample(questions, min(20, len(questions)))
    
    # Format questions (remove correct answer from response)
    formatted_questions = []
    for i, q in enumerate(selected_questions):
        # Map correct option letter to actual option text
        option_map = {
            'A': q['Option A'],
            'B': q['Option B'],
            'C': q['Option C'],
            'D': q['Option D']
        }
        correct_option_letter = q['Correct Option'].strip().upper()
        correct_answer_text = option_map.get(correct_option_letter, q['Option A'])
        
        formatted_questions.append({
            'id': i,
            'question': q['Question'],
            'options': [
                q['Option A'],
                q['Option B'],
                q['Option C'],
                q['Option D']
            ],
            'correct_answer': correct_answer_text
        })
    
    return jsonify({
        'questions': formatted_questions,
        'source': 'csv_question_bank'
    })

@app.route('/api/questions/genai/<subject>', methods=['GET'])
def get_genai_questions(subject):
    """Generate 20 questions using GenAI and save for admin review"""
    try:
        generator = QuestionGenerator()
        questions = generator.generate_questions(subject)
        
        if not questions:
            return jsonify({'error': 'Failed to generate questions'}), 500
        
        # Save to database with PENDING status
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        saved_count = 0
        for q in questions:
            try:
                cursor.execute('''
                    INSERT INTO ai_generated_questions 
                    (subject, question, option_a, option_b, option_c, option_d, 
                     correct_option, question_type, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    subject,
                    q['Question'],
                    q['Option A'],
                    q['Option B'],
                    q['Option C'],
                    q['Option D'],
                    q['Correct Option'],
                    q.get('Type', 'Standard'),
                    'pending_review'
                ))
                saved_count += 1
            except Exception as e:
                print(f"Error saving question: {e}")
        
        conn.commit()
        conn.close()
        
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
    data = request.json
    subject = data.get('subject')
    answers = data.get('answers')
    
    if not subject or not answers:
        return jsonify({'error': 'Invalid request'}), 400
    
    # Calculate score
    total_questions = len(answers)
    correct_count = 0
    results = []
    
    for answer in answers:
        is_correct = answer['user_answer'] == answer['correct_answer']
        if is_correct:
            correct_count += 1
        
        results.append({
            'question': answer['question'],
            'user_answer': answer['user_answer'],
            'correct_answer': answer['correct_answer'],
            'is_correct': is_correct
        })
    
    score = (correct_count / total_questions) * 100
    
    # Save to database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO test_history (subject, total_questions, correct_answers, score)
        VALUES (?, ?, ?, ?)
    ''', (subject, total_questions, correct_count, score))
    
    test_id = cursor.lastrowid
    
    # Save individual question results
    for result in results:
        cursor.execute('''
            INSERT INTO question_history (test_id, question, user_answer, correct_answer, is_correct)
            VALUES (?, ?, ?, ?, ?)
        ''', (test_id, result['question'], result['user_answer'], result['correct_answer'], result['is_correct']))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'test_id': test_id,
        'total_questions': total_questions,
        'correct_answers': correct_count,
        'score': score,
        'results': results
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get test history"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, subject, total_questions, correct_answers, score, timestamp
        FROM test_history
        ORDER BY timestamp DESC
    ''')
    
    history = []
    for idx, row in enumerate(cursor.fetchall(), 1):
        timestamp = datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S')
        history.append({
            'test_no': idx,
            'date': timestamp.strftime('%d-%m-%Y'),
            'time': timestamp.strftime('%I:%M %p'),
            'subject': row[1],
            'score': f"{row[4]:.1f}%",
            'id': row[0],
            'total_questions': row[2],
            'correct_answers': row[3]
        })
    
    conn.close()
    return jsonify({'history': history})

@app.route('/api/history/<int:test_id>', methods=['GET'])
def get_test_details(test_id):
    """Get detailed results for a specific test"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get test info
    cursor.execute('''
        SELECT subject, total_questions, correct_answers, score, timestamp
        FROM test_history
        WHERE id = ?
    ''', (test_id,))
    
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
        
        # Save to database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        saved_count = 0
        for q in questions:
            try:
                cursor.execute('''
                    INSERT INTO ai_generated_questions 
                    (subject, question, option_a, option_b, option_c, option_d, 
                     correct_option, question_type, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    subject,
                    q['Question'],
                    q['Option A'],
                    q['Option B'],
                    q['Option C'],
                    q['Option D'],
                    q['Correct Option'],
                    q.get('Type', 'Standard'),
                    'pending_review'
                ))
                saved_count += 1
            except Exception as e:
                print(f"Error saving question: {e}")
        
        conn.commit()
        conn.close()
        
        log_admin_action('admin_generation', None, 
                        f'Admin generated {saved_count} questions for {subject}')
        
        return jsonify({
            'message': f'Generated {saved_count} questions for review',
            'question_count': saved_count,
            'status': 'pending_review'
        })
        
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
                   correct_option, question_type, created_at, status
            FROM ai_generated_questions
            WHERE status = 'pending_review' AND subject = ? AND is_active = 1
            ORDER BY created_at DESC
        ''', (subject,))
    else:
        cursor.execute('''
            SELECT id, subject, question, option_a, option_b, option_c, option_d, 
                   correct_option, question_type, created_at, status
            FROM ai_generated_questions
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
            'status': row[10]
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
        FROM ai_generated_questions
        WHERE id = ? AND status = 'pending_review'
    ''', (question_id,))
    
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return jsonify({'error': 'Question not found or already processed'}), 404
    
    # Update status in database
    cursor.execute('''
        UPDATE ai_generated_questions
        SET status = 'approved',
            reviewed_at = CURRENT_TIMESTAMP,
            reviewed_by = ?
        WHERE id = ?
    ''', (admin_user, question_id))
    
    conn.commit()
    conn.close()
    
    # Add to main CSV file
    try:
        df = pd.read_csv(DATA_FILE, encoding='utf-8')
        
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
            FROM ai_generated_questions
            WHERE id = ? AND status = 'pending_review'
        ''', (qid,))
        
        row = cursor.fetchone()
        
        if row:
            # Update status
            cursor.execute('''
                UPDATE ai_generated_questions
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
            df = pd.read_csv(DATA_FILE, encoding='utf-8')
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

@app.route('/api/admin/reject-question/<int:question_id>', methods=['POST'])
def reject_question(question_id):
    """Reject a question (soft delete)"""
    data = request.json
    admin_user = data.get('admin_user', 'admin')
    reason = data.get('reason', 'No reason provided')
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE ai_generated_questions
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
        UPDATE ai_generated_questions
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
            FROM ai_generated_questions
            WHERE status = 'approved' AND subject = ? AND is_active = 1
            ORDER BY reviewed_at DESC
        ''', (subject,))
    else:
        cursor.execute('''
            SELECT id, subject, question, option_a, option_b, option_c, option_d,
                   correct_option, question_type, reviewed_at, reviewed_by
            FROM ai_generated_questions
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
    try:
        df = pd.read_csv(DATA_FILE, encoding='utf-8')
        df['Subject'] = df['Subject'].str.replace('Physcis', 'Physics', case=False)
        subjects = sorted(df['Subject'].unique().tolist())
    except:
        subjects = ['Physics', 'Chemistry', 'Maths', 'Biology']
    
    stats = {}
    
    for subject in subjects:
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN status = 'pending_review' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved,
                COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected
            FROM ai_generated_questions
            WHERE subject = ? AND is_active = 1
        ''', (subject,))
        
        row = cursor.fetchone()
        stats[subject] = {
            'pending': row[0],
            'approved': row[1],
            'rejected': row[2],
            'total': row[0] + row[1]
        }
    
    conn.close()
    return jsonify({'stats': stats})

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

# ============================================================================
# FRONTEND ROUTES
# ============================================================================

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

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