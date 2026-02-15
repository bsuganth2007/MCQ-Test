import pandas as pd

df = pd.read_excel('data/MCQ_Quesbank.xlsx')

# Search for problematic characters
problematic_chars = ['â€"', 'â‚', 'â€™', 'Â']
found_issues = []

for idx, row in df.iterrows():
    q = str(row['Question'])
    for opt in ['Option A', 'Option B', 'Option C', 'Option D']:
        q += ' ' + str(row[opt])
    
    for char in problematic_chars:
        if char in q:
            found_issues.append({
                'index': idx,
                'subject': row['Subject'],
                'question': row['Question'][:150],
                'problematic_text': q[:200]
            })
            break

print(f"Found {len(found_issues)} questions with encoding issues\n")

for issue in found_issues[:5]:
    print(f"Row {issue['index']} - {issue['subject']}")
    print(f"Text: {issue['problematic_text']}")
    print(f"Repr: {repr(issue['problematic_text'][:100])}")
    print("-" * 80)
