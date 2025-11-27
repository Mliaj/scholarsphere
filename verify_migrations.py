#!/usr/bin/env python3
"""
Verify all migrations have been applied successfully
"""

from app import app, db
from sqlalchemy import text

def verify_migrations():
    """Check that all expected tables exist"""
    with app.app_context():
        try:
            # Get all tables in the database
            result = db.session.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE()
                ORDER BY TABLE_NAME
            """))
            tables = [row[0] for row in result.fetchall()]
            
            print("=" * 60)
            print("Database Migration Verification")
            print("=" * 60)
            print(f"\nFound {len(tables)} tables in database:")
            for table in tables:
                print(f"  - {table}")
            
            # Expected tables
            expected_tables = [
                'users',
                'awards',
                'credentials',
                'scholarships',
                'scholarship_applications',
                'scholarship_application_files',
                'application_remarks',
                'notifications',
                'schedule'
            ]
            
            print("\n" + "=" * 60)
            print("Verification Results:")
            print("=" * 60)
            
            all_present = True
            for table in expected_tables:
                if table in tables:
                    print(f"OK: {table} table exists")
                else:
                    print(f"WARNING: {table} table missing")
                    all_present = False
            
            if all_present:
                print("\n" + "=" * 60)
                print("SUCCESS: All expected tables are present!")
                print("=" * 60)
            else:
                print("\n" + "=" * 60)
                print("WARNING: Some tables are missing")
                print("=" * 60)
            
            # Check some key columns
            print("\n" + "=" * 60)
            print("Checking Key Columns:")
            print("=" * 60)
            
            # Check users table columns
            user_cols = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'users'
            """)).fetchall()
            user_column_names = [row[0] for row in user_cols]
            
            key_user_cols = ['is_active', 'profile_picture', 'year_level', 'course']
            for col in key_user_cols:
                if col in user_column_names:
                    print(f"OK: users.{col} exists")
                else:
                    print(f"WARNING: users.{col} missing")
            
            # Check scholarships table columns
            scholarship_cols = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'scholarships'
            """)).fetchall()
            scholarship_column_names = [row[0] for row in scholarship_cols]
            
            key_scholarship_cols = ['deadline', 'pending_count', 'approved_count', 'disapproved_count', 'is_active']
            for col in key_scholarship_cols:
                if col in scholarship_column_names:
                    print(f"OK: scholarships.{col} exists")
                else:
                    print(f"WARNING: scholarships.{col} missing")
            
            # Check credentials table columns
            credential_cols = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'credentials'
            """)).fetchall()
            credential_column_names = [row[0] for row in credential_cols]
            
            if 'status' in credential_column_names:
                print(f"OK: credentials.status exists")
            else:
                print(f"WARNING: credentials.status missing")
            
            print("\n" + "=" * 60)
            print("Verification Complete!")
            print("=" * 60)
            
        except Exception as e:
            print(f"ERROR: Verification failed: {e}")

if __name__ == '__main__':
    verify_migrations()

