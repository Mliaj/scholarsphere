#!/usr/bin/env python3
"""
Migration: Add scholarship_application_files table
This table will link scholarship applications with credential files
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
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'scholarship_application_files'
            """))
            table_exists = result.fetchone() is not None
            
            if not table_exists:
                # Create scholarship_application_files table (MySQL syntax)
                db.session.execute(text("""
                    CREATE TABLE scholarship_application_files (
                        id INT AUTO_INCREMENT NOT NULL,
                        application_id INT NOT NULL,
                        credential_id INT NOT NULL,
                        requirement_type VARCHAR(100) NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (id),
                        FOREIGN KEY (application_id) REFERENCES scholarship_applications (id) ON DELETE CASCADE,
                        FOREIGN KEY (credential_id) REFERENCES credentials (id) ON DELETE CASCADE,
                        UNIQUE KEY unique_app_cred_req (application_id, credential_id, requirement_type),
                        INDEX idx_application_files_app_id (application_id),
                        INDEX idx_application_files_cred_id (credential_id),
                        INDEX idx_application_files_req_type (requirement_type)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                
                db.session.commit()
                print("OK: Successfully created scholarship_application_files table")
                
                # Verify table creation
                verify_result = db.session.execute(text("""
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'scholarship_application_files'
                """))
                if verify_result.fetchone():
                    print("OK: Table verification successful")
                else:
                    print("ERROR: Table verification failed")
                    return False
            else:
                print("INFO: scholarship_application_files table already exists")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Migration failed: {str(e)}")
            return False

if __name__ == "__main__":
    print("Starting migration: Add scholarship_application_files table")
    print("=" * 60)
    
    success = migrate()
    
    if success:
        print("=" * 60)
        print("OK: Migration completed successfully!")
    else:
        print("=" * 60)
        print("ERROR: Migration failed!")
