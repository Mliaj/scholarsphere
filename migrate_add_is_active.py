#!/usr/bin/env python3
"""
Migration to add users.is_active column to MySQL database.
"""
from app import app, db
from sqlalchemy import text

def main():
    with app.app_context():
        try:
            # Check if column exists (MySQL)
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'users' 
                AND COLUMN_NAME = 'is_active'
            """))
            column_exists = result.fetchone() is not None
            
            if column_exists:
                print("INFO: users.is_active already exists")
                return
            
            # Add column (MySQL syntax)
            db.session.execute(text("""
                ALTER TABLE users 
                ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1
            """))
            db.session.commit()
            print("OK: Added users.is_active column")
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Migration failed: {e}")

if __name__ == '__main__':
    main()


