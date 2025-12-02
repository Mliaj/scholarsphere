#!/usr/bin/env python3
"""
Test script to verify semester expiration processing setup
Run this before setting up the scheduled task to ensure everything works
"""

from app import app, db, Scholarship, ScholarshipApplication, User
from sqlalchemy import text
from datetime import date

def test_setup():
    """Test that the environment is set up correctly"""
    print("Testing Semester Expiration Processing Setup")
    print("=" * 70)
    
    with app.app_context():
        # Test 1: Database connection
        print("\n1. Testing database connection...")
        try:
            result = db.session.execute(text("SELECT 1")).fetchone()
            if result:
                print("   ✓ Database connection successful")
            else:
                print("   ✗ Database connection failed")
                return False
        except Exception as e:
            print(f"   ✗ Database connection error: {e}")
            return False
        
        # Test 2: Check if required tables exist
        print("\n2. Checking required tables...")
        required_tables = [
            'scholarships',
            'scholarship_applications',
            'users',
            'notifications',
            'semester_expiration_notifications'
        ]
        
        for table in required_tables:
            try:
                result = db.session.execute(
                    text(f"SHOW TABLES LIKE '{table}'")
                ).fetchone()
                if result:
                    print(f"   ✓ Table '{table}' exists")
                else:
                    print(f"   ✗ Table '{table}' is missing")
                    return False
            except Exception as e:
                print(f"   ✗ Error checking table '{table}': {e}")
                return False
        
        # Test 3: Check for scholarships with semester dates
        print("\n3. Checking scholarships with semester dates...")
        try:
            scholarships = Scholarship.query.filter(
                Scholarship.semester_date.isnot(None),
                Scholarship.is_active == True
            ).count()
            print(f"   ✓ Found {scholarships} active scholarship(s) with semester dates")
        except Exception as e:
            print(f"   ✗ Error querying scholarships: {e}")
            return False
        
        # Test 4: Check for approved applications
        print("\n4. Checking approved applications...")
        try:
            approved_count = ScholarshipApplication.query.filter_by(
                status='approved',
                is_active=True
            ).count()
            print(f"   ✓ Found {approved_count} approved application(s)")
        except Exception as e:
            print(f"   ✗ Error querying applications: {e}")
            return False
        
        # Test 5: Test email configuration (if available)
        print("\n5. Testing email configuration...")
        try:
            from flask import current_app
            mail_config = current_app.config.get('MAIL_SERVER')
            if mail_config:
                print(f"   ✓ Mail server configured: {mail_config}")
            else:
                print("   ⚠ Mail server not configured (emails may not send)")
        except Exception as e:
            print(f"   ⚠ Could not check email configuration: {e}")
        
        # Test 6: Check if we can import the processing script
        print("\n6. Testing script imports...")
        try:
            from process_semester_expirations import (
                create_notification,
                has_notification_been_sent,
                record_notification_sent
            )
            print("   ✓ All required functions can be imported")
        except Exception as e:
            print(f"   ✗ Import error: {e}")
            return False
        
        print("\n" + "=" * 70)
        print("✓ All tests passed! The environment is ready for scheduled tasks.")
        print("=" * 70)
        return True

if __name__ == '__main__':
    try:
        success = test_setup()
        if not success:
            print("\n✗ Some tests failed. Please fix the issues before setting up the scheduled task.")
            exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error during testing: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

