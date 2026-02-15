
import sys
import os

# Add the current directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from question_generator import QuestionGenerator

def push_manual():
    print("🚀 Starting one-time push for Biology and Physics...")
    generator = QuestionGenerator()
    
    subjects = ['Biology', 'Physics']
    
    for subject in subjects:
        print(f"\n--- Generating for {subject} ---")
        try:
            # Generate 10 questions (standard batch size)
            questions = generator.generate_questions(subject, count=10)
            
            if questions:
                # Use the robust save method we just improved
                success = generator.save_questions_to_db(questions, status='pending_review')
                if success:
                    print(f"✅ Successfully pushed {len(questions)} questions for {subject}")
                else:
                    print(f"❌ Failed to save questions for {subject}")
            else:
                print(f"❌ No questions were generated for {subject}")
        except Exception as e:
            print(f"❌ Error during manual push for {subject}: {e}")

if __name__ == "__main__":
    push_manual()
