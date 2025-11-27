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
from app import app, db
from sqlalchemy import text


def column_exists(table: str, column: str) -> bool:
    """Check if a column exists in a table (MySQL)"""
    result = db.session.execute(text("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = :table 
        AND COLUMN_NAME = :column
    """), {"table": table, "column": column})
    return result.fetchone() is not None


def add_column_if_missing(table: str, column: str, ddl: str) -> None:
    """Add a column if it doesn't exist (MySQL)"""
    if not column_exists(table, column):
        db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def migrate():
    with app.app_context():
        try:
            # Check if scholarships table exists
            result = db.session.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'scholarships'
            """))
            table_exists = result.fetchone() is not None

            if not table_exists:
                # Create scholarships table if it doesn't exist (MySQL syntax)
                db.session.execute(text("""
                    CREATE TABLE scholarships (
                        id INT AUTO_INCREMENT NOT NULL,
                        code VARCHAR(50) UNIQUE,
                        PRIMARY KEY (id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))

            # Add new columns if missing
            add_column_if_missing('scholarships', 'description', 'TEXT')
            add_column_if_missing('scholarships', 'type', 'VARCHAR(100)')
            add_column_if_missing('scholarships', 'level', 'VARCHAR(100)')
            add_column_if_missing('scholarships', 'eligibility', 'TEXT')
            add_column_if_missing('scholarships', 'slots', 'INT')
            add_column_if_missing('scholarships', 'contact_name', 'VARCHAR(255)')
            add_column_if_missing('scholarships', 'contact_email', 'VARCHAR(255)')
            add_column_if_missing('scholarships', 'contact_phone', 'VARCHAR(50)')

            # Keep existing columns commonly used by the app (no-op if present)
            add_column_if_missing('scholarships', 'title', 'VARCHAR(255)')
            add_column_if_missing('scholarships', 'deadline', 'DATE')
            add_column_if_missing('scholarships', 'requirements', 'TEXT')
            add_column_if_missing('scholarships', 'provider_id', 'INT')
            add_column_if_missing('scholarships', 'status', "VARCHAR(20) DEFAULT 'draft'")
            add_column_if_missing('scholarships', 'applications_count', 'INT DEFAULT 0')
            add_column_if_missing('scholarships', 'pending_count', 'INT DEFAULT 0')
            add_column_if_missing('scholarships', 'approved_count', 'INT DEFAULT 0')
            add_column_if_missing('scholarships', 'disapproved_count', 'INT DEFAULT 0')
            add_column_if_missing('scholarships', 'created_at', 'DATETIME')
            add_column_if_missing('scholarships', 'updated_at', 'DATETIME')
            add_column_if_missing('scholarships', 'is_active', 'TINYINT(1) DEFAULT 1')

            db.session.commit()
            print('OK: Migration completed: scholarships table extended')
            
        except Exception as e:
            db.session.rollback()
            print(f'ERROR: Migration failed: {e}')


if __name__ == '__main__':
    migrate()



