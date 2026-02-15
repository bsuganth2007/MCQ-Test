import pandas as pd

df = pd.read_csv('data/MCQ_Quesbank.csv', encoding='utf-8')

print(f"Total questions in CSV: {len(df)}")
print(f"\nQuestions by subject:")
print(df['Subject'].value_counts())

print(f"\nSample Physics question:")
physics = df[df['Subject'].str.lower() == 'physics'].iloc[0]
print(f"Question: {physics['Question'][:50]}...")
print(f"Option A: {physics['Option A']}")
print(f"Option B: {physics['Option B']}")
print(f"Option C: {physics['Option C']}")
print(f"Option D: {physics['Option D']}")
print(f"Correct Answer: {physics['Correct Answer']}")

print(f"\nChecking for issues:")
print(f"Empty questions: {df['Question'].isna().sum()}")
print(f"Empty correct answers: {df['Correct Answer'].isna().sum()}")
print(f"Empty Option A: {df['Option A'].isna().sum()}")
print(f"Empty Option B: {df['Option B'].isna().sum()}")

EOF