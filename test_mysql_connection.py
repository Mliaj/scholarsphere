#!/usr/bin/env python3
"""
Test MySQL database connection for Scholarsphere
"""

import os
import sys
from dotenv import load_dotenv
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Load environment variables
load_dotenv('config.env')

def test_connection():
    """Test MySQL database connection"""
    print("Testing MySQL Database Connection...")
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
    print("=" * 50)
    
    # Test 1: Basic PyMySQL connection (without database)
    print("\n1. Testing basic MySQL server connection...")
    try:
        conn = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            charset='utf8mb4'
        )
        print("OK: Successfully connected to MySQL server")
        conn.close()
    except Exception as e:
        print(f"X Failed to connect to MySQL server: {e}")
        print("\nPlease ensure:")
        print("  - MySQL server is running")
        print("  - Host, port, user, and password are correct")
        return False
    
    # Test 2: Check if database exists
    print("\n2. Checking if database exists...")
    try:
        conn = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES LIKE %s", (db_name,))
        result = cursor.fetchone()
        if result:
            print(f"OK: Database '{db_name}' exists")
        else:
            print(f"X Database '{db_name}' does not exist")
            print(f"  Run 'python create_mysql_database.py' to create it")
            conn.close()
            return False
        conn.close()
    except Exception as e:
        print(f"X Error checking database: {e}")
        return False
    
    # Test 3: SQLAlchemy connection
    print("\n3. Testing SQLAlchemy connection...")
    try:
        database_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={'charset': 'utf8mb4'}
        )
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            result.fetchone()
        print("OK: SQLAlchemy connection successful")
    except Exception as e:
        print(f"X SQLAlchemy connection failed: {e}")
        return False
    
    # Test 4: Flask-SQLAlchemy connection
    print("\n4. Testing Flask-SQLAlchemy connection...")
    try:
        from app import app, db
        with app.app_context():
            # Try to execute a simple query
            result = db.session.execute(text("SELECT 1 as test"))
            result.fetchone()
        print("OK: Flask-SQLAlchemy connection successful")
    except Exception as e:
        print(f"X Flask-SQLAlchemy connection failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("OK: All connection tests passed!")
    print("=" * 50)
    return True

if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)

