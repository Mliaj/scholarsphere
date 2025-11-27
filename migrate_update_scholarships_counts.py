#!/usr/bin/env python3
"""
Migration to add per-status application counts to scholarships table.
Adds columns: pending_count, approved_count, disapproved_count if missing.
"""
from app import app, db
from sqlalchemy import text

def main():
    with app.app_context():
        try:
            # Get existing columns (MySQL)
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'scholarships'
            """))
            cols = [r[0] for r in result.fetchall()]
            
            changed = False
            if 'pending_count' not in cols:
                db.session.execute(text("""
                    ALTER TABLE scholarships 
                    ADD COLUMN pending_count INT NOT NULL DEFAULT 0
                """))
                changed = True
            if 'approved_count' not in cols:
                db.session.execute(text("""
                    ALTER TABLE scholarships 
                    ADD COLUMN approved_count INT NOT NULL DEFAULT 0
                """))
                changed = True
            if 'disapproved_count' not in cols:
                db.session.execute(text("""
                    ALTER TABLE scholarships 
                    ADD COLUMN disapproved_count INT NOT NULL DEFAULT 0
                """))
                changed = True
            
            if changed:
                db.session.commit()
                print('OK: Added status count columns to scholarships')
            else:
                print('INFO: Status count columns already present')
                
        except Exception as e:
            db.session.rollback()
            print(f'ERROR: Migration failed: {e}')

if __name__ == '__main__':
    main()





