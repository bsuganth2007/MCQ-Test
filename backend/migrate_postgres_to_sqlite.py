import os
import sqlite3
import psycopg2

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SQLITE_DB = os.path.join(BASE_DIR, 'data', 'history.db')
POSTGRES_URL = os.environ.get('DATABASE_URL', 'postgresql://bsuganth:eC1JaDwHkhys4My9TxpnGBaMuHdCIu0P@dpg-d69boq49c44c7387enc0-a.oregon-postgres.render.com/mcq_hlvx')

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

RESET_LOCAL = True


def get_sqlite_columns(conn, table):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def get_postgres_columns(conn, table):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,)
    )
    return {row[0] for row in cursor.fetchall()}


def fetch_postgres_rows(conn, table, columns):
    cursor = conn.cursor()
    cols_sql = ', '.join(columns)
    cursor.execute(f"SELECT {cols_sql} FROM {table}")
    return cursor.fetchall()


def insert_sqlite_rows(conn, table, columns, rows):
    if not rows:
        return 0
    cols_sql = ', '.join(columns)
    placeholders = ', '.join(['?'] * len(columns))
    sql = f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders})"
    cursor = conn.cursor()
    cursor.executemany(sql, rows)
    conn.commit()
    return len(rows)


def clear_sqlite_table(conn, table):
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table}")
    conn.commit()


def main():
    if not os.path.exists(SQLITE_DB):
        raise SystemExit(f"SQLite DB not found at {SQLITE_DB}")

    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.execute('PRAGMA foreign_keys = OFF')
    pg_conn = psycopg2.connect(POSTGRES_URL)

    try:
        if RESET_LOCAL:
            for table in reversed(TABLES):
                clear_sqlite_table(sqlite_conn, table)

        for table in TABLES:
            sqlite_cols = get_sqlite_columns(sqlite_conn, table)
            pg_cols = get_postgres_columns(pg_conn, table)
            common_cols = [col for col in sqlite_cols if col in pg_cols]

            if not common_cols:
                print(f"Skipping {table}: no shared columns")
                continue

            rows = fetch_postgres_rows(pg_conn, table, common_cols)
            inserted = insert_sqlite_rows(sqlite_conn, table, common_cols, rows)
            print(f"{table}: copied {inserted} rows")

        print("Sync complete.")
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == '__main__':
    main()
