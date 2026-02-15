import sqlite3
import os

db_path = 'backend/data/history-backup1.db'
print(f"Checking DB at {os.path.abspath(db_path)}")
print(f"File size: {os.path.getsize(db_path)} bytes")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(ai_generated_questions)")
columns = cursor.fetchall()
for col in columns:
    print(f"Column: {col[1]}")
conn.close()
