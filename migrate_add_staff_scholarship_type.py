#!/usr/bin/env python3
"""
Migration: Add scholarship_type column to users table for provider_staff
"""
from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            # Check if column exists
            result = db.session.execute(text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'users'
                AND COLUMN_NAME = 'scholarship_type'
            """))
            column_exists = result.fetchone() is not None
            
            if not column_exists:
                # Add scholarship_type column
                db.session.execute(text("""
                    ALTER TABLE users
                    ADD COLUMN scholarship_type VARCHAR(100) NULL
                """))
                print("OK: Added scholarship_type column to users table")
            else:
                print("INFO: scholarship_type column already exists")
            
            db.session.commit()
            print("OK: Staff scholarship type migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Staff scholarship type migration failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    migrate()

