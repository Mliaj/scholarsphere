#!/usr/bin/env python3
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'scholarsphere.db')

def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(scholarships)")
    cols = [r[1] for r in cur.fetchall()]
    if 'deadline' not in cols:
        cur.execute("ALTER TABLE scholarships ADD COLUMN deadline TEXT")
        conn.commit()
        print('Added scholarships.deadline')
    else:
        print('deadline already exists')
    conn.close()

if __name__ == '__main__':
    main()





