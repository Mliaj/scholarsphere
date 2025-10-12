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
            # For SQLite, we'll use PRAGMA table_info to check columns
            result = db.session.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            
            # Check if profile_picture column exists
            if 'profile_picture' not in columns:
                db.session.execute(text("ALTER TABLE users ADD COLUMN profile_picture VARCHAR(255)"))
                print("✅ Added profile_picture column")
            else:
                print("ℹ️  profile_picture column already exists")
            
            # Check if year_level column exists
            if 'year_level' not in columns:
                db.session.execute(text("ALTER TABLE users ADD COLUMN year_level VARCHAR(20)"))
                print("✅ Added year_level column")
            else:
                print("ℹ️  year_level column already exists")
            
            # Check if course column exists
            if 'course' not in columns:
                db.session.execute(text("ALTER TABLE users ADD COLUMN course VARCHAR(50)"))
                print("✅ Added course column")
            else:
                print("ℹ️  course column already exists")

            # Check if is_active column exists
            if 'is_active' not in columns:
                db.session.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL"))
                print("✅ Added is_active column")
            else:
                print("ℹ️  is_active column already exists")
            
            db.session.commit()
            print("🎉 Database migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {e}")

if __name__ == '__main__':
    migrate_database()
