#!/usr/bin/env python3
"""
Migration: Add semester, school_year, deadline expiration, and semester expiration fields to scholarships table

Adds columns if missing (safe to run multiple times):
  - is_expired_deadline TINYINT(1) DEFAULT 0
  - semester VARCHAR(50) NULL (e.g., "1st", "2nd")
  - school_year VARCHAR(50) NULL (e.g., "2025 - 2026")
  - semester_date DATE NULL
  - is_expired_semester TINYINT(1) DEFAULT 0

Usage: python migrate_add_scholarship_semester_fields.py
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
        print(f"OK: Added column {table}.{column}")
    else:
        print(f"INFO: Column {table}.{column} already exists")


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
                print("ERROR: scholarships table does not exist. Please run base migrations first.")
                return

            # Add new columns if missing
            add_column_if_missing('scholarships', 'is_expired_deadline', 'TINYINT(1) DEFAULT 0')
            add_column_if_missing('scholarships', 'semester', 'VARCHAR(50) NULL')
            add_column_if_missing('scholarships', 'school_year', 'VARCHAR(50) NULL')
            add_column_if_missing('scholarships', 'semester_date', 'DATE NULL')
            add_column_if_missing('scholarships', 'is_expired_semester', 'TINYINT(1) DEFAULT 0')

            db.session.commit()
            print("OK: Scholarship semester fields migration completed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Migration failed: {e}")

if __name__ == '__main__':
    migrate()

