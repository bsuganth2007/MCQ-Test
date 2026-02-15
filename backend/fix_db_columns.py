
import sqlite3
import os

db_path = 'data/history.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if column exists
    cursor.execute("PRAGMA table_info(ai_generated_questions)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'chapter_name' not in columns:
        print("Adding chapter_name column...")
        cursor.execute("ALTER TABLE ai_generated_questions ADD COLUMN chapter_name TEXT DEFAULT 'General'")
        conn.commit()
    
    if 'explanation' not in columns:
        print("Adding explanation column...")
        cursor.execute("ALTER TABLE ai_generated_questions ADD COLUMN explanation TEXT")
        conn.commit()
        print("Column 'explanation' added successfully.")
    else:
        print("Column 'explanation' already exists.")
        
    if 'difficulty' in columns:
        print("You may want to keep 'difficulty' or drop it later. For now, we will leave it.")

except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
