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
        
        # Try to load from .env if not in environment
        if not api_key:
            env_paths = [
                '.env',
                'backend/.env',
                '../.env',
                os.path.join(os.path.dirname(__file__), '.env')
            ]
            for path in env_paths:
                if os.path.exists(path):
                    with open(path) as f:
                        for line in f:
                            if line.strip().startswith('GEMINI_API_KEY='):
                                api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                                os.environ['GEMINI_API_KEY'] = api_key
                                break
                if api_key: break

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
        # Using Gemini 3 Flash Preview (Active in Feb 2026)
        self.model = genai.GenerativeModel(
            'gemini-3-flash-preview',
            generation_config={"response_mime_type": "application/json"}
        )

    def _strip_code_fences(self, text):
        if not text:
            return text
        if "```" not in text:
            return text
        # Extract the first fenced block if present
        parts = text.split("```")
        if len(parts) >= 3:
            return parts[1].lstrip("json\n").lstrip("JSON\n").strip()
        return text

    def _clean_json_text(self, text):
        if not text:
            return text
        # Remove trailing commas that break JSON parsing
        import re
        return re.sub(r",\s*([}\]])", r"\1", text)

    def _extract_json_candidate(self, text):
        if not text:
            return None
        text = text.strip()
        text = self._strip_code_fences(text)
        if text.startswith('[') and text.endswith(']'):
            return text
        if text.startswith('{') and 'questions' in text:
            return text
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end > start:
            return text[start:end]
        return text

    def generate_questions(self, subject, count=20):
        """Generate MCQ questions for a given subject using Gemini AI with specific conditions"""
        prompt = f"""
        System Role: You are an expert ICSE (Indian Certificate of Secondary Education) Board Examiner for Grade 10.
        
        Task: Generate {count} high-quality Multiple Choice Questions (MCQs) for the subject: {subject}.
        
        Reference Material & Context:
        - Curriculum: Latest ICSE Grade 10 Syllabus.
        - Academic Level: High School (Grade 10).
        - Question Quality: Follow the standards of ICSE Board Examination papers.
        
        Specific Conditions & Constraints:
        1. Numerical Distribution: 
           - If Subject is 'Physics', ensure EXACTLY 30% of questions are numerical problems.
           - If Subject is 'Mathematics' or 'Maths', ensure 100% of questions are numerical/mathematical problems.
           - Otherwise, include 20-30% numerical/logical problems where relevant.
        2. Difficulty Distribution: 
           - 30% Easy (Direct recall / Simple calculation).
           - 50% Medium (Application-based / Multi-step calculation).
           - 20% Hard (Complex synthesis / Analytical problems).
        3. Options Quality:
           - Each question must have EXACTLY 4 options (A, B, C, D).
           - Distractors (incorrect options) must be plausible and based on common student misconceptions.
        4. Symbol Formatting: 
           - Use LaTeX for ALL mathematical symbols, chemical equations, and formulas. 
           - CRITICAL: In the JSON output, you MUST escape every backslash with another backslash for JSON compatibility.
           - Example: Use "$\\frac{1}{2}$" (not "$\frac{1}{2}$") and "$H_{2}SO_{4}$".
           - Always use double backslashes for LaTeX commands: \\sum, \\alpha, \\beta, \\rightarrow, etc.
        5. Clarity: No ambiguous questions. Ensure there is only ONE unequivocally correct answer.
        6. Style: Match the exact tone and terminology used in ICSE Board Grade 10 examination papers.
        
        Output Format: Respond ONLY with a valid JSON array of objects.
        Each JSON object must have these EXACT keys:
        - "Question": The question text.
        - "Option A": Text for option A.
        - "Option B": Text for option B.
        - "Option C": Text for option C.
        - "Option D": Text for option D.
        - "Correct Option": Only the letter (A, B, C, or D).
        - "Explanation": A clear 1-2 sentence explanation of the solution or reason.
        - "Type": Either "Standard", "Reasoning", or "Assertion".
        - "Chapter Name": The name of the specific chapter this question belongs to.
        - "Subject": "{subject}"
        
        Return ONLY the JSON array starting with [ and ending with ].
        """
        
        try:
            print(f"🤖 AI generating {count} questions for {subject}...")
            response = self.model.generate_content(prompt)
            
            # Extract JSON from the response text
            text = getattr(response, 'text', None) or ''
            candidate = self._extract_json_candidate(text)
            candidate = self._clean_json_text(candidate or '')

            questions = None
            parse_errors = []
            for raw in [candidate, text]:
                if not raw:
                    continue
                raw = self._clean_json_text(self._strip_code_fences(raw.strip()))
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict) and 'questions' in parsed:
                        questions = parsed.get('questions')
                    else:
                        questions = parsed
                    break
                except Exception as parse_err:
                    parse_errors.append(str(parse_err))

            if questions is None:
                # If there's "Extra data" or truncated JSON, try to fix it
                bracket_count = 0
                first_array_end = -1
                start_idx = text.find('[')
                if start_idx != -1:
                    for i, char in enumerate(text[start_idx:], start_idx):
                        if char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                            if bracket_count == 0:
                                first_array_end = i + 1
                                break

                if first_array_end != -1:
                    questions_json = self._clean_json_text(text[start_idx:first_array_end])
                    try:
                        questions = json.loads(questions_json)
                    except Exception as parse_err:
                        parse_errors.append(str(parse_err))
                else:
                    print(f"❌ Failed to parse JSON. Errors: {parse_errors}")
                    print(f"DEBUG - Full response text from AI:\n{text}\n--- END DEBUG ---")
                    return []
            
            if not isinstance(questions, list):
                print("❌ Response is not a list of questions")
                return []
                
            print(f"✅ Successfully generated {len(questions)} questions")
            return questions
            
        except Exception as e:
            error_str = str(e)
            print(f"❌ Error during generation: {error_str}")
            if "429" in error_str or "quota" in error_str.lower():
                raise Exception("AI API Quota Exceeded. Please try again later or wait 1-2 minutes.")
            return []
    
    def append_to_question_bank(self, questions):
        """Append questions to the CSV question bank"""
        # Your implementation
        pass
    
    def verify_answer(self, question, options, suggested_answer):
        """Verify the correct answer for a given question using Gemini"""
        if not options:
            return None
            
        prompt = f"""
        Review the following Multiple Choice Question (MCQ) and determine the correct answer.
        
        Question: {question}
        Options:
        A: {options.get('A', '')}
        B: {options.get('B', '')}
        C: {options.get('C', '')}
        D: {options.get('D', '')}
        
        The user suggests the correct answer is option: {suggested_answer}
        
        Please respond strictly in JSON format with the following keys:
        1. "is_correct": boolean (true if the suggested answer is actually correct)
        2. "correct_option": string (The correct letter A, B, C, or D)
        3. "explanation": string (Short explanation of why this is the correct answer)
        
        Return ONLY valid JSON.
        """
        
        try:
            print(f"🤖 AI Verifying answer for: {question[:50]}...")
            response = self.model.generate_content(prompt)
            # Find JSON in response
            text = response.text
            
            # Use robust JSON extraction
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    # Try finding balanced braces if extra text exists
                    start = text.find('{')
                    bracket_count = 0
                    for i in range(start, len(text)):
                        if text[i] == '{': bracket_count += 1
                        elif text[i] == '}': 
                            bracket_count -= 1
                            if bracket_count == 0:
                                return json.loads(text[start:i+1])
            
            print(f"❌ Failed to extract JSON from AI verification response: {text}")
            return None
        except Exception as e:
            print(f"❌ Error verifying answer with Gemini: {e}")
            return None

    def save_questions_to_db(self, questions, status='pending_review'):
        """Save generated questions to the ai_generated_questions table"""
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, 'data', 'history.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        try:
            # Store individual questions
            for q in questions:
                try:
                    # Map keys robustly (handle variations in AI output keys)
                    subject = q.get('Subject', q.get('subject', 'Unknown'))
                    question_text = q.get('Question', q.get('question', ''))
                    opt_a = q.get('Option A', q.get('option_a', ''))
                    opt_b = q.get('Option B', q.get('option_b', ''))
                    opt_c = q.get('Option C', q.get('option_c', ''))
                    opt_d = q.get('Option D', q.get('option_d', ''))
                    correct = q.get('Correct Option', q.get('correct_option', q.get('Correct Answer', 'A')))
                    q_type = q.get('Type', q.get('question_type', 'Standard'))
                    chapter = q.get('Chapter Name', q.get('chapter_name', 'General'))
                    expl = q.get('Explanation', q.get('explanation', ''))

                    if not question_text:
                        continue

                    cursor.execute('''
                        INSERT INTO ai_generated_questions 
                        (subject, question, option_a, option_b, option_c, option_d, 
                         correct_option, question_type, chapter_name, explanation, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        subject, question_text, opt_a, opt_b, opt_c, opt_d, 
                        correct, q_type, chapter, expl, status
                    ))
                    saved_count += 1
                except Exception as item_err:
                    print(f"⚠️ Error saving single question to DB: {item_err}")
                    continue
            
            conn.commit()
            print(f"✅ Automatically backed up {saved_count}/{len(questions)} AI questions to DB with status '{status}'")
            return True
            
        except Exception as e:
            if conn: conn.rollback()
            print(f"❌ Critical error in save_questions_to_db: {e}")
            return False
        finally:
            if conn:
                conn.close()