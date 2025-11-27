#!/usr/bin/env python3
"""
Create a minimal scholarships table if it doesn't exist (MySQL).
"""
from app import app, db
from sqlalchemy import text

def main():
    with app.app_context():
        try:
            # Check if table exists (MySQL)
            result = db.session.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'scholarships'
            """))
            table_exists = result.fetchone() is not None

            if not table_exists:
                # Create table (MySQL syntax)
                db.session.execute(text("""
                    CREATE TABLE scholarships (
                        id INT AUTO_INCREMENT NOT NULL,
                        code VARCHAR(50) UNIQUE,
                        title VARCHAR(255) NOT NULL,
                        provider_id INT NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'approved',
                        applications_count INT NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL,
                        PRIMARY KEY (id),
                        FOREIGN KEY(provider_id) REFERENCES users(id) ON DELETE CASCADE,
                        INDEX idx_scholarships_provider_id (provider_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                db.session.commit()
                print('OK: Scholarships table created')
            else:
                print('INFO: Scholarships table already exists')

        except Exception as e:
            db.session.rollback()
            print(f'ERROR: Failed to ensure scholarships table: {e}')

if __name__ == '__main__':
    main()





