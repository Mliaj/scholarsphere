#!/usr/bin/env python3
"""
Migration to add per-status application counts to scholarships table.
Adds columns: pending_count, approved_count, disapproved_count if missing.
"""
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
    changed = False
    if 'pending_count' not in cols:
        cur.execute("ALTER TABLE scholarships ADD COLUMN pending_count INTEGER DEFAULT 0 NOT NULL")
        changed = True
    if 'approved_count' not in cols:
        cur.execute("ALTER TABLE scholarships ADD COLUMN approved_count INTEGER DEFAULT 0 NOT NULL")
        changed = True
    if 'disapproved_count' not in cols:
        cur.execute("ALTER TABLE scholarships ADD COLUMN disapproved_count INTEGER DEFAULT 0 NOT NULL")
        changed = True
    if changed:
        conn.commit()
        print('Added status count columns to scholarships')
    else:
        print('Status count columns already present')
    conn.close()

if __name__ == '__main__':
    main()





