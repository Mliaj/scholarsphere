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
            # Check if awards table exists
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='awards'"))
            table_exists = result.fetchone() is not None
            
            if not table_exists:
                # Create awards table
                awards_table_sql = """
                CREATE TABLE awards (
                    id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    award_type VARCHAR(100) NOT NULL,
                    award_title VARCHAR(255) NOT NULL,
                    file_name VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    file_size INTEGER,
                    academic_year VARCHAR(20),
                    award_date DATE,
                    upload_date DATETIME NOT NULL,
                    is_active BOOLEAN,
                    PRIMARY KEY (id),
                    FOREIGN KEY(user_id) REFERENCES users (id)
                )
                """
                
                db.session.execute(text(awards_table_sql))
                db.session.commit()
                print("✅ Awards table created successfully!")
            else:
                print("ℹ️  Awards table already exists")
            
            print("🎉 Awards migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Awards migration failed: {e}")

if __name__ == '__main__':
    migrate_awards_table()
