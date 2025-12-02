#!/usr/bin/env python3
"""
Migration: Add renewal tracking fields to scholarship_applications table
Tracks renewal applications and renewal failure status
"""
from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            # Check if columns exist
            result = db.session.execute(text("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'scholarship_applications'
                AND COLUMN_NAME IN ('is_renewal', 'renewal_failed', 'original_application_id')
            """))
            existing_columns = [row[0] for row in result.fetchall()]
            
            # Add is_renewal column
            if 'is_renewal' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE scholarship_applications
                    ADD COLUMN is_renewal BOOLEAN NOT NULL DEFAULT FALSE
                """))
                print("OK: Added is_renewal column")
            else:
                print("INFO: is_renewal column already exists")
            
            # Add renewal_failed column
            if 'renewal_failed' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE scholarship_applications
                    ADD COLUMN renewal_failed BOOLEAN NOT NULL DEFAULT FALSE
                """))
                print("OK: Added renewal_failed column")
            else:
                print("INFO: renewal_failed column already exists")
            
            # Add original_application_id column (for linking renewal to original application)
            if 'original_application_id' not in existing_columns:
                db.session.execute(text("""
                    ALTER TABLE scholarship_applications
                    ADD COLUMN original_application_id INT NULL,
                    ADD INDEX idx_original_app_id (original_application_id),
                    ADD FOREIGN KEY (original_application_id) REFERENCES scholarship_applications(id) ON DELETE SET NULL
                """))
                print("OK: Added original_application_id column")
            else:
                print("INFO: original_application_id column already exists")
            
            db.session.commit()
            print("OK: Renewal tracking migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Renewal tracking migration failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    migrate()

