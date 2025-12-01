import sys
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

# Initialize Flask app
app = Flask(__name__)

# Database Configuration
database_url = os.environ.get('DATABASE_URL')

# Fix for Render's Postgres URL (if applicable)
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

if not database_url or database_url.startswith('sqlite'):
    # Build MySQL connection string from individual environment variables
    db_host = os.environ.get('DB_HOST', '127.0.0.1')
    db_user = os.environ.get('DB_USER', 'root')
    db_pass = os.environ.get('DB_PASS', '')
    db_name = os.environ.get('DB_NAME', 'scholarsphere')
    db_port = int(os.environ.get('DB_PORT', 3306))
    database_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define tables to truncate in order (Child tables first to avoid FK constraint errors)
TABLES = [
    'announcements',
    'notifications',
    'schedule',
    'student_remarks',
    'application_remarks',
    'family_backgrounds',
    'academic_information',
    'application_personal_information',
    'scholarship_application_files',
    'scholarship_applications',
    'credentials',
    'awards',
    'scholarships',
    'users'
]

def truncate_tables():
    print("⚠️  WARNING: This will DELETE ALL DATA from your database tables!")
    confirm = input("Type 'yes' to confirm and proceed: ")
    
    if confirm.lower() != 'yes':
        print("Operation cancelled.")
        return

    with app.app_context():
        try:
            # Disable foreign key checks to allow truncation in any order (MySQL specific)
            # For PostgreSQL/SQLite, this might need different handling or careful ordering
            is_mysql = 'mysql' in database_url
            is_sqlite = 'sqlite' in database_url
            
            if is_mysql:
                db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            for table in TABLES:
                print(f"Truncating table: {table}...")
                try:
                    # Use DELETE FROM for better compatibility across DBs instead of TRUNCATE
                    db.session.execute(text(f"DELETE FROM {table}"))
                    
                    # Reset Auto Increment (MySQL) / Sequence (Postgres)
                    if is_mysql:
                        db.session.execute(text(f"ALTER TABLE {table} AUTO_INCREMENT = 1"))
                    elif is_sqlite:
                        db.session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
                        
                except Exception as e:
                    print(f"Error truncating {table} (might not exist): {e}")

            if is_mysql:
                db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                
            db.session.commit()
            print("\n✅ All tables truncated successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ An error occurred: {e}")

if __name__ == '__main__':
    truncate_tables()
