#!/usr/bin/env python3
"""
Migration to add deadline column to scholarships table
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
                AND TABLE_NAME = 'scholarships' 
                AND COLUMN_NAME = 'deadline'
            """))
            column_exists = result.fetchone() is not None
            
            if column_exists:
                print('INFO: deadline already exists')
                return
            
            # Add column (MySQL syntax)
            db.session.execute(text("""
                ALTER TABLE scholarships 
                ADD COLUMN deadline DATE NULL
            """))
            db.session.commit()
            print('OK: Added scholarships.deadline')
            
        except Exception as e:
            db.session.rollback()
            print(f'ERROR: Migration failed: {e}')

if __name__ == '__main__':
    main()





