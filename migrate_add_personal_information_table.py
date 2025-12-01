#!/usr/bin/env python3
"""
Migration: Add application_personal_information table
Stores personal information for each scholarship application (department, school, address, contact)
"""
from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            # Check if table exists
            result = db.session.execute(text("""
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'application_personal_information'
            """))
            table_exists = result.fetchone() is not None

            if not table_exists:
                # Create application_personal_information table
                db.session.execute(text("""
                    CREATE TABLE application_personal_information (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        application_id INT NOT NULL,
                        department VARCHAR(255) NULL,
                        school_university VARCHAR(255) NULL,
                        address TEXT NULL,
                        contact_number VARCHAR(50) NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (application_id) REFERENCES scholarship_applications(id) ON DELETE CASCADE,
                        UNIQUE KEY unique_application (application_id),
                        INDEX idx_application_id (application_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                print("OK: Created application_personal_information table")
            else:
                print("INFO: application_personal_information table already exists")

            db.session.commit()
            print("OK: Application personal information table migration completed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Application personal information table migration failed: {e}")

if __name__ == '__main__':
    migrate()

