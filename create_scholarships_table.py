#!/usr/bin/env python3
"""
Create a minimal scholarships table if it doesn't exist.
"""
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'scholarsphere.db')

def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"Database not found at {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Create table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scholarships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            title TEXT NOT NULL,
            provider_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'approved',
            applications_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(provider_id) REFERENCES users(id)
        )
        """
    )

    # Seed one example if table empty
    cur.execute("SELECT COUNT(*) FROM scholarships")
    if cur.fetchone()[0] == 0:
        # Try to find a provider user
        cur.execute("SELECT id, organization FROM users WHERE role='provider' ORDER BY id ASC LIMIT 1")
        row = cur.fetchone()
        provider_id = row[0] if row else 1
        cur.execute(
            "INSERT OR IGNORE INTO scholarships (code, title, provider_id, status, applications_count, created_at) VALUES (?,?,?,?,?,?)",
            (
                'SCH-001',
                'Academic Excellence Scholarship',
                provider_id,
                'approved',
                45,
                datetime.utcnow().isoformat(),
            ),
        )
    conn.commit()
    conn.close()
    print('Scholarships table ensured')

if __name__ == '__main__':
    main()





