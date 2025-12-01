#!/usr/bin/env python3
"""
Migration: Add family_backgrounds table
Stores family background information for each scholarship application
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
                AND TABLE_NAME = 'family_backgrounds'
            """))
            table_exists = result.fetchone() is not None

            if not table_exists:
                # Create family_backgrounds table
                db.session.execute(text("""
                    CREATE TABLE family_backgrounds (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        application_id INT NOT NULL,
                        parent_guardian_name VARCHAR(255) NOT NULL,
                        occupation VARCHAR(255) NULL,
                        household_income VARCHAR(100) NULL,
                        dependents INT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (application_id) REFERENCES scholarship_applications(id) ON DELETE CASCADE,
                        INDEX idx_application_id (application_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                print("OK: Created family_backgrounds table")
            else:
                print("INFO: family_backgrounds table already exists")

            db.session.commit()
            print("OK: Family background table migration completed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Family background table migration failed: {e}")

if __name__ == '__main__':
    migrate()

