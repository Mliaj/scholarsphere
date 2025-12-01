#!/usr/bin/env python3
"""
Migration: Add academic_information table
Stores academic information for each scholarship application
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
                AND TABLE_NAME = 'academic_information'
            """))
            table_exists = result.fetchone() is not None

            if not table_exists:
                # Create academic_information table
                db.session.execute(text("""
                    CREATE TABLE academic_information (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        application_id INT NOT NULL,
                        latest_gpa VARCHAR(50) NULL,
                        current_semester VARCHAR(100) NULL,
                        school_year VARCHAR(50) NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (application_id) REFERENCES scholarship_applications(id) ON DELETE CASCADE,
                        INDEX idx_application_id (application_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                print("OK: Created academic_information table")
            else:
                print("INFO: academic_information table already exists")

            db.session.commit()
            print("OK: Academic information table migration completed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Academic information table migration failed: {e}")

if __name__ == '__main__':
    migrate()

