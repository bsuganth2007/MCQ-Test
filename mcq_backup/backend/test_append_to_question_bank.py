from question_generator import QuestionGenerator

# Dummy AI output (list of 2 questions for test, can be expanded to 20)
dummy_questions = [
    {
        'Subject': 'Chemistry',
        'Question': 'Which functional group is present in ethanol?',
        'Option A': '-OH',
        'Option B': '-CHO',
        'Option C': '-COOH',
        'Option D': '-NH2',
        'Correct Option': 'A',
        'Difficulty': 'Easy'
    },
    {
        'Subject': 'Chemistry',
        'Question': 'Which group is characteristic of carboxylic acids?',
        'Option A': '-OH',
        'Option B': '-COOH',
        'Option C': '-CHO',
        'Option D': '-COO-',
        'Correct Option': 'B',
        'Difficulty': 'Medium'
    }
]

gen = QuestionGenerator()
result = gen.append_to_question_bank(dummy_questions)
print('Append result:', result)
