import pandas as pd

df = pd.read_excel('data/MCQ_Quesbank.xlsx')
print(f'Total questions: {len(df)}')
print(f'Columns: {list(df.columns)}')
print(f'\nSubjects and counts:')
print(df['Subject'].value_counts())
print(f'\nFirst question:')
print(df.head(1).to_string())
