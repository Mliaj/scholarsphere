#!/usr/bin/env python3
"""
Migration script to create the awards table
"""

from app import app, db
from sqlalchemy import text

def migrate_awards_table():
    """Create awards table"""
    with app.app_context():
        try:
            # Check if awards table exists (MySQL)
            result = db.session.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'awards'
            """))
            table_exists = result.fetchone() is not None
            
            if not table_exists:
                # Create awards table (MySQL syntax)
                awards_table_sql = """
                CREATE TABLE awards (
                    id INT AUTO_INCREMENT NOT NULL,
                    user_id INT NOT NULL,
                    award_type VARCHAR(100) NOT NULL,
                    award_title VARCHAR(255) NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    file_size INT,
                    academic_year VARCHAR(20),
                    award_date DATE,
                    upload_date DATETIME NOT NULL,
                    is_active TINYINT(1) DEFAULT 1,
                    PRIMARY KEY (id),
                    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
                    INDEX idx_awards_user_id (user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
                
                db.session.execute(text(awards_table_sql))
                db.session.commit()
                print("OK: Awards table created successfully!")
            else:
                print("INFO: Awards table already exists")
            
            print("OK: Awards migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Awards migration failed: {e}")

if __name__ == '__main__':
    migrate_awards_table()
