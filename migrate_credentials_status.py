#!/usr/bin/env python3
"""
Migration script to add status column to credentials table
"""

from app import app, db
from sqlalchemy import text

def migrate_credentials_status():
    """Add status column to credentials table if it doesn't exist"""
    with app.app_context():
        try:
            # For SQLite, we'll use PRAGMA table_info to check columns
            result = db.session.execute(text("PRAGMA table_info(credentials)"))
            columns = [row[1] for row in result.fetchall()]
            
            # Check if status column exists
            if 'status' not in columns:
                db.session.execute(text("ALTER TABLE credentials ADD COLUMN status VARCHAR(20) DEFAULT 'uploaded'"))
                print("✅ Added status column to credentials table")
                
                # Update existing records to have 'uploaded' status
                db.session.execute(text("UPDATE credentials SET status = 'uploaded' WHERE status IS NULL"))
                print("✅ Updated existing credentials to 'uploaded' status")
            else:
                print("ℹ️  status column already exists")
            
            db.session.commit()
            print("🎉 Credentials status migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {e}")

if __name__ == '__main__':
    migrate_credentials_status()
