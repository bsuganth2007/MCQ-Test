import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
import google.generativeai as genai

class QuestionGenerator:
    def __init__(self):
        """Initialize the question generator with Gemini API"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key or api_key == 'YOUR_GEMINI_API_KEY_HERE':
            error_msg = """
            ❌ Gemini API Key Not Configured
            
            The GEMINI_API_KEY is not set or is using the default placeholder.
            
            To configure your API key:
            1. Get your API key from: https://aistudio.google.com/app/apikey
            2. Copy backend/.env.example to backend/.env
            3. Replace YOUR_GEMINI_API_KEY_HERE with your actual API key
            4. Restart the application
            
            For detailed instructions, see SECURITY_SETUP.md
            """
            raise ValueError(error_msg.strip())
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_questions(self, subject, count=20):
        """Generate MCQ questions for a given subject"""
        # Implementation for generating questions via Gemini API
        pass
    
    def append_to_question_bank(self, questions):
        """Append questions to the CSV question bank"""
        # Your implementation
        pass
    
    def save_questions_to_db(self, questions, status='pending_review'):
        """Save generated questions with pending review status"""
        conn = sqlite3.connect('data/history.db')
        cursor = conn.cursor()
        
        try:
            # Get subject from first question
            subject = questions[0].get('Subject', 'Unknown')
            
            # Create a question set
            cursor.execute('''
                INSERT INTO question_sets (subject, status, question_count)
                VALUES (?, ?, ?)
            ''', (subject, status, len(questions)))
            
            set_id = cursor.lastrowid
            
            # Store individual questions
            for q in questions:
                cursor.execute('''
                    INSERT INTO generated_questions 
                    (subject, question, option_a, option_b, option_c, option_d, 
                     correct_option, question_type, status, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    q.get('Subject', subject),
                    q['Question'],
                    q['Option A'],
                    q['Option B'],
                    q['Option C'],
                    q['Option D'],
                    q['Correct Option'],
                    q.get('Type', 'Standard'),
                    status,
                    'ai_generated'
                ))
            
            conn.commit()
            print(f"✅ Saved {len(questions)} questions with status '{status}'")
            return set_id
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error saving questions: {e}")
            return None
        finally:
            conn.close()