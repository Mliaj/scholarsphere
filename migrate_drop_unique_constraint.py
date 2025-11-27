import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

# Database configuration
db_host = os.environ.get('DB_HOST', '127.0.0.1')
db_user = os.environ.get('DB_USER', 'root')
db_pass = os.environ.get('DB_PASS', '')
db_name = os.environ.get('DB_NAME', 'scholarsphere')
db_port = int(os.environ.get('DB_PORT', 3306))

# Create database connection string
DATABASE_URL = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

def migrate():
    print(f"Connecting to database: {db_name} at {db_host}...")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            print("Starting migration to drop 'unique_user_scholarship'...")

            # 1. Check if the unique index exists
            result = conn.execute(text(f"SHOW INDEX FROM scholarship_applications WHERE Key_name = 'unique_user_scholarship'"))
            if result.rowcount == 0:
                print("Unique index 'unique_user_scholarship' does not exist. No action needed.")
                conn.commit()
                return # Exit early if no index to drop

            print("Unique index 'unique_user_scholarship' found.")

            # 2. Create a non-unique index on user_id to satisfy FK `scholarship_applications_ibfk_1`
            print("Creating non-unique index 'idx_user_id' on 'scholarship_applications.user_id'...")
            try:
                conn.execute(text("CREATE INDEX idx_user_id ON scholarship_applications(user_id)"))
                print("Index 'idx_user_id' created successfully.")
            except Exception as e:
                if "Duplicate entry for key 'idx_user_id'" in str(e) or "already exists" in str(e):
                    print("Index 'idx_user_id' already exists. Skipping creation.")
                else:
                    raise # Re-raise if it's a different error

            # 3. Drop the problematic Unique Index
            print("Dropping unique index 'unique_user_scholarship'...")
            conn.execute(text("ALTER TABLE scholarship_applications DROP INDEX unique_user_scholarship"))
            print("Unique index 'unique_user_scholarship' dropped successfully.")
            
            conn.commit()
            print("Migration completed successfully!")
            
    except Exception as e:
        print(f"CRITICAL ERROR during migration: {e}")
        import traceback
        traceback.print_exc()
        # Rollback any pending transactions on error
        conn.rollback()

if __name__ == "__main__":
    migrate()
