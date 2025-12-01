import os
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Load environment variables
load_dotenv('config.env')

# Database configuration
db_host = os.environ.get('DB_HOST', '127.0.0.1')
db_user = os.environ.get('DB_USER', 'root')
db_pass = os.environ.get('DB_PASS', '')
db_name = os.environ.get('DB_NAME', 'scholarsphere')
db_port = int(os.environ.get('DB_PORT', 3306))

DATABASE_URL = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

def migrate():
    print(f"Connecting to database: {db_name} at {db_host}...")
    engine = create_engine(DATABASE_URL)
    
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        with engine.connect() as conn:
            # 1. Create scholarship_application_files
            if 'scholarship_application_files' not in existing_tables:
                print("Creating table 'scholarship_application_files'...")
                conn.execute(text("""
                    CREATE TABLE scholarship_application_files (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        application_id INT NOT NULL,
                        credential_id INT NOT NULL,
                        requirement_type VARCHAR(100) NOT NULL,
                        FOREIGN KEY (application_id) REFERENCES scholarship_applications(id),
                        FOREIGN KEY (credential_id) REFERENCES credentials(id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """))
                print("Table 'scholarship_application_files' created.")
            else:
                print("Table 'scholarship_application_files' already exists.")

            # 2. Create application_remarks
            if 'application_remarks' not in existing_tables:
                print("Creating table 'application_remarks'...")
                conn.execute(text("""
                    CREATE TABLE application_remarks (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        application_id INT NOT NULL,
                        provider_id INT NOT NULL,
                        remark_text TEXT NOT NULL,
                        status VARCHAR(50),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (application_id) REFERENCES scholarship_applications(id),
                        FOREIGN KEY (provider_id) REFERENCES users(id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """))
                print("Table 'application_remarks' created.")
            else:
                print("Table 'application_remarks' already exists.")

            # 3. Create student_remarks
            if 'student_remarks' not in existing_tables:
                print("Creating table 'student_remarks'...")
                conn.execute(text("""
                    CREATE TABLE student_remarks (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        student_id INT NOT NULL,
                        provider_id INT NOT NULL,
                        remark_text TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NULL,
                        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (provider_id) REFERENCES users(id) ON DELETE CASCADE,
                        INDEX idx_remarks_student_id (student_id),
                        INDEX idx_remarks_provider_id (provider_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """))
                print("Table 'student_remarks' created.")
            else:
                print("Table 'student_remarks' already exists.")
                
            conn.commit()
            print("Migration completed successfully!")
            
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
