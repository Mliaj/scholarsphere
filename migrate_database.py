#!/usr/bin/env python3
"""
Database migration script to add new fields to User model
"""

from app import app, db
from sqlalchemy import text

def migrate_database():
    """Add new columns to users table if they don't exist"""
    with app.app_context():
        try:
            # Get existing columns (MySQL)
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'users'
            """))
            columns = [row[0] for row in result.fetchall()]
            
            # Check if profile_picture column exists
            if 'profile_picture' not in columns:
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN profile_picture VARCHAR(255) NULL
                """))
                print("OK: Added profile_picture column")
            else:
                print("INFO: profile_picture column already exists")
            
            # Check if year_level column exists
            if 'year_level' not in columns:
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN year_level VARCHAR(20) NULL
                """))
                print("OK: Added year_level column")
            else:
                print("INFO: year_level column already exists")
            
            # Check if course column exists
            if 'course' not in columns:
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN course VARCHAR(50) NULL
                """))
                print("OK: Added course column")
            else:
                print("INFO: course column already exists")

            # Check if is_active column exists
            if 'is_active' not in columns:
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1
                """))
                print("OK: Added is_active column")
            else:
                print("INFO: is_active column already exists")
            
            db.session.commit()
            print("OK: Database migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Migration failed: {e}")

if __name__ == '__main__':
    migrate_database()
