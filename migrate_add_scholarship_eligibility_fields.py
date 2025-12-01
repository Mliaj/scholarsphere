#!/usr/bin/env python3
"""
Migration to add program_course and additional_criteria columns to scholarships table.
Minimum GPA will be stored in the eligibility column as specified.
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
                AND TABLE_NAME = 'scholarships'
            """))
            columns = [row[0] for row in result.fetchall()]
            
            # Add program_course column
            if 'program_course' not in columns:
                db.session.execute(text("""
                    ALTER TABLE scholarships 
                    ADD COLUMN program_course VARCHAR(255) NULL
                """))
                print("OK: Added program_course column")
            else:
                print("INFO: program_course column already exists")
            
            # Add additional_criteria column
            if 'additional_criteria' not in columns:
                db.session.execute(text("""
                    ALTER TABLE scholarships 
                    ADD COLUMN additional_criteria TEXT NULL
                """))
                print("OK: Added additional_criteria column")
            else:
                print("INFO: additional_criteria column already exists")
            
            db.session.commit()
            print("OK: Database migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Migration failed: {e}")

if __name__ == '__main__':
    migrate()

