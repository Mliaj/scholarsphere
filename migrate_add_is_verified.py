from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        try:
            # Check if column exists
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'credentials' 
                AND COLUMN_NAME = 'is_verified'
            """))
            if result.fetchone():
                print("Column 'is_verified' already exists in 'credentials' table.")
                return

            # Add column
            db.session.execute(text("ALTER TABLE credentials ADD COLUMN is_verified TINYINT(1) DEFAULT 0"))
            db.session.commit()
            print("Successfully added 'is_verified' column to 'credentials' table.")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error migrating database: {e}")

if __name__ == '__main__':
    migrate()
