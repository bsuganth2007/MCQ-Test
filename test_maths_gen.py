import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from question_generator import QuestionGenerator

def test_maths():
    gen = QuestionGenerator()
    subject = "Maths"
    print(f"Testing generation for {subject}...")
    questions = gen.generate_questions(subject, count=2)
    if questions:
        print(f"✅ Success! Generated {len(questions)} questions.")
        for i, q in enumerate(questions):
            print(f"Q{i+1}: {q.get('Question')[:50]}...")
    else:
        print("❌ Failed to generate questions.")

if __name__ == "__main__":
    test_maths()
