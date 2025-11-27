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
            # Check if column exists (MySQL)
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'credentials' 
                AND COLUMN_NAME = 'status'
            """))
            column_exists = result.fetchone() is not None
            
            # Check if status column exists
            if not column_exists:
                db.session.execute(text("""
                    ALTER TABLE credentials 
                    ADD COLUMN status VARCHAR(20) DEFAULT 'uploaded'
                """))
                print("OK: Added status column to credentials table")
                
                # Update existing records to have 'uploaded' status
                db.session.execute(text("""
                    UPDATE credentials 
                    SET status = 'uploaded' 
                    WHERE status IS NULL
                """))
                print("OK: Updated existing credentials to 'uploaded' status")
            else:
                print("INFO: status column already exists")
            
            db.session.commit()
            print("OK: Credentials status migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Migration failed: {e}")

if __name__ == '__main__':
    migrate_credentials_status()
