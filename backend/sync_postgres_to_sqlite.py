import os
import sqlite3

DATABASE_URL = os.environ.get('DATABASE_URL')
SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'history.db')

TABLES = [
    'test_history',
    'question_history',
    'visitor_logs',
    'user_sessions',
    'test_attempts',
    'ai_generated_questions',
    'admin_actions'
]


def fetch_table(cursor, table):
    cursor.execute(f'SELECT * FROM {table}')
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    return columns, rows


def clear_table(cursor, table):
    cursor.execute(f'DELETE FROM {table}')


def insert_rows(cursor, table, columns, rows):
    if not rows:
        return
    placeholders = ','.join(['?'] * len(columns))
    col_sql = ','.join(columns)
    cursor.executemany(
        f'INSERT INTO {table} ({col_sql}) VALUES ({placeholders})',
        rows
    )


def main():
    if not DATABASE_URL:
        print('DATABASE_URL not set. Aborting.')
        return

    try:
        import psycopg2
    except Exception as exc:
        print(f'psycopg2 not available: {exc}')
        return

    pg_conn = psycopg2.connect(DATABASE_URL)
    pg_cursor = pg_conn.cursor()

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cursor = sqlite_conn.cursor()

    for table in TABLES:
        try:
            columns, rows = fetch_table(pg_cursor, table)
        except Exception as exc:
            print(f'Skipping {table}: {exc}')
            continue

        clear_table(sqlite_cursor, table)
        insert_rows(sqlite_cursor, table, columns, rows)
        print(f'Synced {table}: {len(rows)} rows')

    sqlite_conn.commit()
    sqlite_conn.close()
    pg_conn.close()


if __name__ == '__main__':
    main()
