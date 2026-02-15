import pandas as pd
import sys

df = pd.read_excel('data/MCQ_Quesbank.xlsx')
print(f"Total questions: {len(df)}")
print(f"Columns: {df.columns.tolist()}")

# Find chemistry questions with special characters
chem = df[df['Subject'].str.contains('Chem', case=False, na=False)]
print(f"\nChemistry questions found: {len(chem)}")

if len(chem) > 0:
    for idx, row in chem.head(3).iterrows():
        q = row['Question']
        print(f"\n--- Question {idx} ---")
        print(f"Text: {q[:200]}")
        print(f"Repr: {repr(q[:200])}")
        
        # Check for problematic characters
        if 'â€"' in q or 'â‚' in q:
            print("⚠️ ENCODING ISSUE DETECTED!")
            print(f"Raw bytes: {q.encode('utf-8', errors='replace')[:100]}")
