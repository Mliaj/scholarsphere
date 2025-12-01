#!/usr/bin/env python3
"""
Migration: Add student_remarks table
This table stores provider remarks for students (one-to-many: multiple remarks per student)
"""

from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            # Check if table exists (MySQL)
            result = db.session.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'student_remarks'
            """))
            table_exists = result.fetchone() is not None
            
            if not table_exists:
                # Create student_remarks table (MySQL syntax)
                db.session.execute(text("""
                    CREATE TABLE student_remarks (
                        id INT AUTO_INCREMENT NOT NULL,
                        student_id INT NOT NULL,
                        provider_id INT NOT NULL,
                        remark_text TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NULL,
                        PRIMARY KEY (id),
                        FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE CASCADE,
                        FOREIGN KEY (provider_id) REFERENCES users (id) ON DELETE CASCADE,
                        INDEX idx_remarks_student_id (student_id),
                        INDEX idx_remarks_provider_id (provider_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                
                db.session.commit()
                print("OK: Successfully created student_remarks table")
                
                # Verify table creation
                verify_result = db.session.execute(text("""
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'student_remarks'
                """))
                if verify_result.fetchone():
                    print("OK: Table verification successful")
                else:
                    print("ERROR: Table verification failed")
                    return False
            else:
                print("INFO: student_remarks table already exists")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Migration failed: {str(e)}")
            return False

if __name__ == "__main__":
    print("Starting migration: Add student_remarks table")
    print("=" * 60)
    
    success = migrate()
    
    if success:
        print("=" * 60)
        print("Migration completed successfully!")
    else:
        print("=" * 60)
        print("Migration failed!")

