#!/usr/bin/env python3
"""
Create MySQL database for Scholarsphere if it doesn't exist
"""

import os
import sys
from dotenv import load_dotenv
import pymysql
from pymysql.err import OperationalError

# Load environment variables
load_dotenv('config.env')

def create_database():
    """Create MySQL database if it doesn't exist"""
    print("Creating MySQL Database...")
    print("=" * 50)
    
    # Get database configuration
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_user = os.getenv('DB_USER', 'root')
    db_pass = os.getenv('DB_PASS', '')
    db_name = os.getenv('DB_NAME', 'scholarsphere')
    db_port = int(os.getenv('DB_PORT', 3306))
    
    print(f"Host: {db_host}")
    print(f"Port: {db_port}")
    print(f"User: {db_user}")
    print(f"Database: {db_name}")
    print(f"Password: {'*' * len(db_pass) if db_pass else '(empty)'}")
    print("=" * 50)
    
    try:
        # Connect to MySQL server (without specifying database)
        print("\nConnecting to MySQL server...")
        conn = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            charset='utf8mb4'
        )
        print("OK: Connected to MySQL server")
        
        # Check if database exists
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES LIKE %s", (db_name,))
        result = cursor.fetchone()
        
        if result:
            print(f"\nOK: Database '{db_name}' already exists")
            conn.close()
            return True
        
        # Create database
        print(f"\nCreating database '{db_name}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        print(f"OK: Database '{db_name}' created successfully")
        
        # Verify creation
        cursor.execute("SHOW DATABASES LIKE %s", (db_name,))
        result = cursor.fetchone()
        if result:
            print(f"OK: Database '{db_name}' verified")
        else:
            print(f"X Failed to verify database creation")
            conn.close()
            return False
        
        conn.close()
        
        print("\n" + "=" * 50)
        print("OK: Database setup complete!")
        print("=" * 50)
        print("\nNext steps:")
        print("  1. Run 'python test_mysql_connection.py' to verify connection")
        print("  2. Run 'python run.py' to start the application and create tables")
        print("=" * 50)
        
        return True
        
    except OperationalError as e:
        print(f"\nX MySQL connection error: {e}")
        print("\nPlease ensure:")
        print("  - MySQL server is running")
        print("  - Host, port, user, and password are correct in config.env")
        return False
    except Exception as e:
        print(f"\nX Error creating database: {e}")
        return False

if __name__ == '__main__':
    success = create_database()
    sys.exit(0 if success else 1)

