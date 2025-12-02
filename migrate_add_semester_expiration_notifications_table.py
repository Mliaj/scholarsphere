#!/usr/bin/env python3
"""
Migration: Add semester_expiration_notifications table
Tracks which semester expiration notifications have been sent to avoid duplicates
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
                AND TABLE_NAME = 'semester_expiration_notifications'
            """))
            table_exists = result.fetchone() is not None

            if not table_exists:
                # Create semester_expiration_notifications table
                db.session.execute(text("""
                    CREATE TABLE semester_expiration_notifications (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        scholarship_id INT NOT NULL,
                        user_id INT NOT NULL,
                        notification_type VARCHAR(50) NOT NULL,
                        notification_date DATE NOT NULL,
                        sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (scholarship_id) REFERENCES scholarships(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        UNIQUE KEY unique_notification (scholarship_id, user_id, notification_type, notification_date),
                        INDEX idx_scholarship_id (scholarship_id),
                        INDEX idx_user_id (user_id),
                        INDEX idx_notification_type (notification_type),
                        INDEX idx_notification_date (notification_date)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
                print("OK: Created semester_expiration_notifications table")
            else:
                print("INFO: semester_expiration_notifications table already exists")

            db.session.commit()
            print("OK: Semester expiration notifications table migration completed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Semester expiration notifications table migration failed: {e}")

if __name__ == '__main__':
    migrate()

