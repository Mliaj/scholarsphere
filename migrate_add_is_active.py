#!/usr/bin/env python3
"""
Lightweight migration to add users.is_active to the SQLite DB without importing Flask app.
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'scholarsphere.db')

def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        if 'is_active' in columns:
            print("users.is_active already exists")
            return
        cur.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL")
        conn.commit()
        print("Added users.is_active column")
    finally:
        conn.close()

if __name__ == '__main__':
    main()


