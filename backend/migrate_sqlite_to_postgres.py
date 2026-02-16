import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_batch

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLITE_DB = os.path.join(BASE_DIR, 'data', 'history.db')
POSTGRES_URL = os.environ.get('DATABASE_URL')

if not POSTGRES_URL:
    raise SystemExit('DATABASE_URL is not set')

TABLES = [
    'test_history',
    'question_history',
    'user_sessions',
    'visitor_logs',
    'test_attempts',
    'ai_generated_questions',
    'admin_actions',
]

SEQUENCES = {
    'test_history': 'test_history_id_seq',
    'question_history': 'question_history_id_seq',
    'user_sessions': 'user_sessions_id_seq',
    'visitor_logs': 'visitor_logs_id_seq',
    'test_attempts': 'test_attempts_id_seq',
    'ai_generated_questions': 'ai_generated_questions_id_seq',
    'admin_actions': 'admin_actions_id_seq',
}


def get_sqlite_columns(conn, table):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def fetch_sqlite_rows(conn, table, columns):
    cursor = conn.cursor()
    cols_sql = ', '.join(columns)
    cursor.execute(f"SELECT {cols_sql} FROM {table}")
    return cursor.fetchall()


def insert_postgres_rows(conn, table, columns, rows):
    if not rows:
        return 0
    cols_sql = ', '.join(columns)
    placeholders = ', '.join(['%s'] * len(columns))
    sql = (
        f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders}) "
        f"ON CONFLICT (id) DO NOTHING"
    )
    with conn.cursor() as cursor:
        execute_batch(cursor, sql, rows, page_size=500)
    conn.commit()
    return len(rows)


def reset_sequence(conn, table, sequence):
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT COALESCE(MAX(id), 1) FROM {table}")
        max_id = cursor.fetchone()[0]
        cursor.execute("SELECT setval(%s, %s)", (sequence, max_id))
    conn.commit()


def main():
    if not os.path.exists(SQLITE_DB):
        raise SystemExit(f"SQLite DB not found at {SQLITE_DB}")

    sqlite_conn = sqlite3.connect(SQLITE_DB)
    pg_conn = psycopg2.connect(POSTGRES_URL)

    try:
        for table in TABLES:
            columns = get_sqlite_columns(sqlite_conn, table)
            if 'id' not in columns:
                print(f"Skipping {table}: no id column")
                continue

            rows = fetch_sqlite_rows(sqlite_conn, table, columns)
            inserted = insert_postgres_rows(pg_conn, table, columns, rows)
            print(f"{table}: migrated {inserted} rows")

            sequence = SEQUENCES.get(table)
            if sequence:
                reset_sequence(pg_conn, table, sequence)

        print("Migration complete.")
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == '__main__':
    main()
