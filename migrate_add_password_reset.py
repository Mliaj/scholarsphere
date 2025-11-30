#!/usr/bin/env python3
"""
Migration to add password reset token columns to users table.
"""
from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            # Check if columns exist (MySQL)
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'users'
            """))
            columns = [row[0] for row in result.fetchall()]
            
            # Check if reset_token column exists
            if 'reset_token' not in columns:
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN reset_token VARCHAR(100) NULL
                """))
                print("OK: Added reset_token column")
            else:
                print("INFO: reset_token column already exists")
            
            # Check if reset_token_expires column exists
            if 'reset_token_expires' not in columns:
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN reset_token_expires DATETIME NULL
                """))
                print("OK: Added reset_token_expires column")
            else:
                print("INFO: reset_token_expires column already exists")
            
            db.session.commit()
            print("OK: Database migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Migration failed: {e}")

if __name__ == '__main__':
    migrate()

