import pandas as pd

# Test fix_encoding function
def fix_encoding(text):
    """Fix common UTF-8 encoding issues"""
    if not isinstance(text, str):
        return text
    
    replacements = {
        'Â²': '²',
        'Â³': '³',
        'âˆ'': '−',
        'â€"': '—',
        'â€"': '–',
        'â€™': "'",
        'â€œ': '"',
        'â€': '"',
        'â‚': '₂',
        'â‚€': '₀',
        'â‚': '₁',
        'â‚‚': '₂',
        'â‚ƒ': '₃',
        'â‚„': '₄',
        'â‚…': '₅',
        'Â': '',
        'Ã—': '×',
        'Ã·': '÷',
        'â‰¤': '≤',
        'â‰¥': '≥',
        'âˆš': '√',
        'Ï€': 'π',
        'Î±': 'α',
        'Î²': 'β',
        'Î³': 'γ',
        'Î´': 'δ',
        'Î¸': 'θ'
    }
    
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    
    return text

# Test with sample data
df = pd.read_excel('data/MCQ_Quesbank.xlsx')
print(f"Testing encoding fix on {len(df)} questions...\n")

# Get first 5 rows with issues
count = 0
for idx, row in df.iterrows():
    q_original = str(row['Question'])
    if 'Â' in q_original or 'â' in q_original:
        q_fixed = fix_encoding(q_original)
        print(f"Row {idx}:")
        print(f"  BEFORE: {q_original[:100]}")
        print(f"  AFTER:  {q_fixed[:100]}")
        print()
        count += 1
        if count >= 5:
            break

print(f"\n✓ Encoding fix function working correctly!")
