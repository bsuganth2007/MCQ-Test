import sys
import os
sys.path.append('D:/Suganthi/Projects/MCQ-Test-App/backend')
os.chdir('D:/Suganthi/Projects/MCQ-Test-App/backend')

from question_generator import QuestionGenerator

print("Testing GenAI question generation...")
print("=" * 60)

try:
    generator = QuestionGenerator()
    print("✓ QuestionGenerator initialized")
    
    print("\nGenerating Physics questions...")
    questions = generator.generate_questions('Physics')
    
    if questions:
        print(f"✓ Generated {len(questions)} questions")
        print("\nFirst question:")
        print(f"  Subject: {questions[0]['Subject']}")
        print(f"  Question: {questions[0]['Question'][:100]}...")
        print(f"  Options: A, B, C, D")
        print(f"  Correct: {questions[0]['Correct Option']}")
    else:
        print("✗ No questions generated")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
