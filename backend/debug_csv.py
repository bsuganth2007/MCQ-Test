import pandas as pd
import os

csv_file = 'data/MCQ_Quesbank.csv'

print("="*60)
print("CSV DIAGNOSTIC REPORT")
print("="*60)

# Check file exists
print(f"\n1. FILE CHECK:")
print(f"   File path: {csv_file}")
print(f"   Exists: {os.path.exists(csv_file)}")
if os.path.exists(csv_file):
    print(f"   Size: {os.path.getsize(csv_file)} bytes")

# Count raw lines
print(f"\n2. RAW FILE CONTENT:")
try:
    with open(csv_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"   Total lines: {len(lines)}")
        print(f"   Header: {lines[0].strip()}")
        print(f"   Columns in header: {len(lines[0].split(','))}")
        
        if len(lines) > 1:
            print(f"\n   First data row:")
            print(f"   {lines[1][:200]}")
        
        if len(lines) > 2:
            print(f"\n   Second data row:")
            print(f"   {lines[2][:200]}")
except Exception as e:
    print(f"   Error reading file: {e}")

# Try pandas read
print(f"\n3. PANDAS READ ATTEMPTS:")

# Attempt 1: Default
try:
    df = pd.read_csv(csv_file, encoding='utf-8')
    print(f"   ✅ Default read: SUCCESS - {len(df)} rows")
    
    print(f"\n4. DATA STRUCTURE:")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Column count: {len(df.columns)}")
    
    if 'Subject' in df.columns:
        print(f"\n5. SUBJECT BREAKDOWN:")
        for subject, count in df['Subject'].value_counts().items():
            print(f"   {subject}: {count} questions")
    
    print(f"\n6. SAMPLE DATA (First row):")
    if len(df) > 0:
        first_row = df.iloc[0]
        for col in df.columns:
            print(f"   {col}: {first_row[col]}")
    
    print(f"\n7. DATA QUALITY CHECK:")
    print(f"   Rows with missing 'Question': {df['Question'].isna().sum()}")
    print(f"   Rows with missing 'Correct Answer': {df['Correct Answer'].isna().sum()}")
    print(f"   Rows with missing 'Subject': {df['Subject'].isna().sum()}")
    
except Exception as e:
    print(f"   ❌ Default read: FAILED - {e}")
    
    # Attempt 2: With error handling
    try:
        df = pd.read_csv(csv_file, encoding='utf-8', on_bad_lines='skip')
        print(f"   ✅ Skip bad lines: SUCCESS - {len(df)} rows")
    except Exception as e2:
        print(f"   ❌ Skip bad lines: FAILED - {e2}")
        
        # Attempt 3: Different encoding
        try:
            df = pd.read_csv(csv_file, encoding='latin-1')
            print(f"   ✅ Latin-1 encoding: SUCCESS - {len(df)} rows")
        except Exception as e3:
            print(f"   ❌ Latin-1 encoding: FAILED - {e3}")

print("\n" + "="*60)
print("END OF DIAGNOSTIC")
print("="*60)


