
import os
from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        print("Migrating: Creating announcements table...")
        
        try:
            # Create announcements table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS announcements (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    provider_id INT NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    recipient_filter VARCHAR(255),
                    recipient_count INT DEFAULT 0,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (provider_id) REFERENCES users(id)
                )
            """))
            print("Success: 'announcements' table created.")
            
            # Verify
            result = db.session.execute(text("SHOW TABLES LIKE 'announcements'"))
            if result.fetchone():
                print("Verification: Table exists.")
            else:
                print("Verification Failed!")
                
        except Exception as e:
            print(f"Error: {e}")
            db.session.rollback()

if __name__ == '__main__':
    migrate()
