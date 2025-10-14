#!/usr/bin/env python3
"""
Extend scholarships table to match Create Scholarship UI fields.

Adds columns if missing (safe to run multiple times):
  - description TEXT
  - type TEXT
  - level TEXT
  - eligibility TEXT
  - slots INTEGER
  - contact_name TEXT
  - contact_email TEXT
  - contact_phone TEXT

Usage: python migrate_extend_scholarships_fields.py
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'scholarsphere.db')


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def add_column_if_missing(cursor: sqlite3.Cursor, table: str, column: str, ddl: str) -> None:
    if not column_exists(cursor, table, column):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def migrate():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"Database not found at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure scholarships table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scholarships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE
        )
    """)

    # Add new columns if missing
    add_column_if_missing(cur, 'scholarships', 'description', 'TEXT')
    add_column_if_missing(cur, 'scholarships', 'type', 'TEXT')
    add_column_if_missing(cur, 'scholarships', 'level', 'TEXT')
    add_column_if_missing(cur, 'scholarships', 'eligibility', 'TEXT')
    add_column_if_missing(cur, 'scholarships', 'slots', 'INTEGER')
    add_column_if_missing(cur, 'scholarships', 'contact_name', 'TEXT')
    add_column_if_missing(cur, 'scholarships', 'contact_email', 'TEXT')
    add_column_if_missing(cur, 'scholarships', 'contact_phone', 'TEXT')

    # Keep existing columns commonly used by the app (no-op if present)
    add_column_if_missing(cur, 'scholarships', 'title', 'TEXT')
    add_column_if_missing(cur, 'scholarships', 'deadline', 'TEXT')
    add_column_if_missing(cur, 'scholarships', 'requirements', 'TEXT')
    add_column_if_missing(cur, 'scholarships', 'provider_id', 'INTEGER')
    add_column_if_missing(cur, 'scholarships', 'status', "TEXT DEFAULT 'draft'")
    add_column_if_missing(cur, 'scholarships', 'applications_count', 'INTEGER DEFAULT 0')
    add_column_if_missing(cur, 'scholarships', 'pending_count', 'INTEGER DEFAULT 0')
    add_column_if_missing(cur, 'scholarships', 'approved_count', 'INTEGER DEFAULT 0')
    add_column_if_missing(cur, 'scholarships', 'disapproved_count', 'INTEGER DEFAULT 0')
    add_column_if_missing(cur, 'scholarships', 'created_at', 'TEXT')
    add_column_if_missing(cur, 'scholarships', 'updated_at', 'TEXT')
    add_column_if_missing(cur, 'scholarships', 'is_active', 'INTEGER DEFAULT 1')

    conn.commit()
    conn.close()
    print('Migration completed: scholarships table extended')


if __name__ == '__main__':
    migrate()



