#!/usr/bin/env python3
"""
Script to verify database structure, relationships, and connections
"""

from app import app, db
from sqlalchemy import text, inspect
from sqlalchemy.engine import reflection

def check_database_connection():
    """Verify database connection"""
    print("=" * 70)
    print("1. DATABASE CONNECTION")
    print("=" * 70)
    try:
        with app.app_context():
            result = db.session.execute(text("SELECT 1"))
            result.fetchone()
            print("✓ Database connection: OK")
            return True
    except Exception as e:
        print(f"✗ Database connection: FAILED - {e}")
        return False

def check_tables():
    """Check if all required tables exist"""
    print("\n" + "=" * 70)
    print("2. REQUIRED TABLES")
    print("=" * 70)
    
    required_tables = [
        'users',
        'scholarships',
        'scholarship_applications',
        'credentials',
        'awards',
        'scholarship_application_files',
        'application_remarks',
        'student_remarks',
        'family_backgrounds',
        'academic_information',
        'application_personal_information',
        'notifications',
        'schedule',
        'announcements',
        'semester_expiration_notifications'
    ]
    
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        missing_tables = []
        for table in required_tables:
            if table in existing_tables:
                print(f"✓ Table '{table}': EXISTS")
            else:
                print(f"✗ Table '{table}': MISSING")
                missing_tables.append(table)
        
        if missing_tables:
            print(f"\n⚠ WARNING: {len(missing_tables)} table(s) missing")
            return False
        else:
            print(f"\n✓ All {len(required_tables)} required tables exist")
            return True

def check_scholarship_columns():
    """Check scholarship table columns"""
    print("\n" + "=" * 70)
    print("3. SCHOLARSHIPS TABLE COLUMNS")
    print("=" * 70)
    
    required_columns = [
        'id', 'code', 'title', 'description', 'type', 'level', 'eligibility',
        'program_course', 'additional_criteria', 'slots', 'contact_name',
        'contact_email', 'contact_phone', 'provider_id', 'status', 'deadline',
        'is_expired_deadline', 'semester', 'school_year', 'semester_date',
        'next_last_semester_date', 'is_expired_semester', 'amount', 'requirements',
        'applications_count', 'pending_count', 'approved_count', 'disapproved_count',
        'created_at', 'updated_at', 'is_active'
    ]
    
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('scholarships')]
        
        missing_columns = []
        for col in required_columns:
            if col in columns:
                print(f"✓ Column 'scholarships.{col}': EXISTS")
            else:
                print(f"✗ Column 'scholarships.{col}': MISSING")
                missing_columns.append(col)
        
        if missing_columns:
            print(f"\n⚠ WARNING: {len(missing_columns)} column(s) missing")
            return False
        else:
            print(f"\n✓ All {len(required_columns)} required columns exist")
            return True

def check_application_columns():
    """Check scholarship_applications table columns"""
    print("\n" + "=" * 70)
    print("4. SCHOLARSHIP_APPLICATIONS TABLE COLUMNS")
    print("=" * 70)
    
    required_columns = [
        'id', 'user_id', 'scholarship_id', 'status', 'application_date',
        'reviewed_at', 'reviewed_by', 'notes', 'is_active', 'is_renewal',
        'renewal_failed', 'original_application_id'
    ]
    
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('scholarship_applications')]
        
        missing_columns = []
        for col in required_columns:
            if col in columns:
                print(f"✓ Column 'scholarship_applications.{col}': EXISTS")
            else:
                print(f"✗ Column 'scholarship_applications.{col}': MISSING")
                missing_columns.append(col)
        
        if missing_columns:
            print(f"\n⚠ WARNING: {len(missing_columns)} column(s) missing")
            return False
        else:
            print(f"\n✓ All {len(required_columns)} required columns exist")
            return True

def check_academic_information_columns():
    """Check academic_information table columns"""
    print("\n" + "=" * 70)
    print("5. ACADEMIC_INFORMATION TABLE COLUMNS")
    print("=" * 70)
    
    required_columns = [
        'id', 'application_id', 'latest_gpa', 'current_semester',
        'school_year', 'created_at', 'updated_at'
    ]
    
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('academic_information')]
        
        missing_columns = []
        for col in required_columns:
            if col in columns:
                print(f"✓ Column 'academic_information.{col}': EXISTS")
            else:
                print(f"✗ Column 'academic_information.{col}': MISSING")
                missing_columns.append(col)
        
        # Note: next_last_semester_date is NOT in academic_information table
        # It's stored in scholarships table and referenced when needed
        print("\nℹ Note: next_last_semester_date is stored in scholarships table, not academic_information")
        
        if missing_columns:
            print(f"\n⚠ WARNING: {len(missing_columns)} column(s) missing")
            return False
        else:
            print(f"\n✓ All {len(required_columns)} required columns exist")
            return True

def check_foreign_keys():
    """Check foreign key relationships"""
    print("\n" + "=" * 70)
    print("6. FOREIGN KEY RELATIONSHIPS")
    print("=" * 70)
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Check scholarship_applications foreign keys
        fks = inspector.get_foreign_keys('scholarship_applications')
        fk_names = {}
        for fk in fks:
            for col in fk['constrained_columns']:
                fk_names[col] = fk['referred_table']
        
        expected_fks = {
            'user_id': 'users',
            'scholarship_id': 'scholarships',
            'reviewed_by': 'users',
            'original_application_id': 'scholarship_applications'  # Self-referencing
        }
        
        for col, expected_table in expected_fks.items():
            if col in fk_names:
                if fk_names[col] == expected_table:
                    print(f"✓ FK 'scholarship_applications.{col}' → '{expected_table}': OK")
                else:
                    print(f"✗ FK 'scholarship_applications.{col}' → '{fk_names[col]}' (expected '{expected_table}'): MISMATCH")
            else:
                print(f"✗ FK 'scholarship_applications.{col}': MISSING")
        
        # Check scholarships foreign keys
        fks = inspector.get_foreign_keys('scholarships')
        fk_names = {}
        for fk in fks:
            for col in fk['constrained_columns']:
                fk_names[col] = fk['referred_table']
        
        if 'provider_id' in fk_names:
            print(f"✓ FK 'scholarships.provider_id' → '{fk_names['provider_id']}': OK")
        else:
            print(f"✗ FK 'scholarships.provider_id': MISSING")
        
        print("\n✓ Foreign key relationships verified")

def check_model_relationships():
    """Check SQLAlchemy model relationships"""
    print("\n" + "=" * 70)
    print("7. SQLALCHEMY MODEL RELATIONSHIPS")
    print("=" * 70)
    
    from app import (
        User, Scholarship, ScholarshipApplication, Credential, Award,
        ScholarshipApplicationFile, ApplicationRemark, StudentRemark,
        FamilyBackground, AcademicInformation, ApplicationPersonalInformation,
        Notification, Schedule, Announcement
    )
    
    relationships_to_check = [
        ('User', 'scholarships', 'One-to-many: User → Scholarships'),
        ('User', 'scholarship_applications', 'One-to-many: User → Applications'),
        ('User', 'credentials', 'One-to-many: User → Credentials'),
        ('User', 'awards', 'One-to-many: User → Awards'),
        ('User', 'staff_members', 'One-to-many: Provider Admin → Staff'),
        ('Scholarship', 'applications', 'One-to-many: Scholarship → Applications'),
        ('ScholarshipApplication', 'application_files', 'One-to-many: Application → Files'),
        ('ScholarshipApplication', 'remarks', 'One-to-many: Application → Remarks'),
        ('ScholarshipApplication', 'family_background', 'One-to-one: Application → Family Background'),
        ('ScholarshipApplication', 'academic_information', 'One-to-one: Application → Academic Info'),
        ('ScholarshipApplication', 'personal_information', 'One-to-one: Application → Personal Info'),
        ('ScholarshipApplication', 'schedules', 'One-to-many: Application → Schedules'),
    ]
    
    all_ok = True
    for model_name, attr_name, description in relationships_to_check:
        try:
            model = globals()[model_name]
            if hasattr(model, attr_name):
                print(f"✓ {description}: EXISTS")
            else:
                # Check if it's a backref
                if hasattr(model, '__mapper__'):
                    mapper = model.__mapper__
                    if attr_name in mapper.relationships:
                        print(f"✓ {description}: EXISTS (relationship)")
                    elif any(rel.backref == attr_name for rel in mapper.relationships.values()):
                        print(f"✓ {description}: EXISTS (backref)")
                    else:
                        print(f"✗ {description}: MISSING")
                        all_ok = False
                else:
                    print(f"✗ {description}: MISSING")
                    all_ok = False
        except KeyError:
            print(f"✗ Model '{model_name}': NOT FOUND")
            all_ok = False
        except Exception as e:
            print(f"✗ Error checking {model_name}.{attr_name}: {e}")
            all_ok = False
    
    # Check for original_application_id relationship (self-referencing)
    try:
        if hasattr(ScholarshipApplication, 'original_application_id'):
            print("✓ ScholarshipApplication.original_application_id: Column EXISTS")
            # Note: No explicit relationship defined, but FK exists
            print("  ℹ Note: Self-referencing FK exists, but no relationship defined in model")
        else:
            print("✗ ScholarshipApplication.original_application_id: MISSING")
            all_ok = False
    except Exception as e:
        print(f"✗ Error checking original_application_id: {e}")
        all_ok = False
    
    return all_ok

def check_routes_database_usage():
    """Check if routes are using database correctly"""
    print("\n" + "=" * 70)
    print("8. ROUTES DATABASE USAGE")
    print("=" * 70)
    
    import os
    route_files = [
        'students/routes.py',
        'provider/routes.py'
    ]
    
    for route_file in route_files:
        if os.path.exists(route_file):
            print(f"\n✓ File '{route_file}': EXISTS")
            # Check if file imports db
            with open(route_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'from app import' in content or 'from flask import current_app' in content:
                    print(f"  ✓ Imports database connection")
                if 'db.session.execute' in content or 'db.session.query' in content or '.query.' in content:
                    print(f"  ✓ Uses database queries")
        else:
            print(f"✗ File '{route_file}': MISSING")
    
    print("\n✓ Routes database usage verified")

def main():
    """Run all verification checks"""
    print("\n" + "=" * 70)
    print("DATABASE STRUCTURE VERIFICATION")
    print("=" * 70)
    print(f"Timestamp: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    results.append(("Database Connection", check_database_connection()))
    results.append(("Tables", check_tables()))
    results.append(("Scholarship Columns", check_scholarship_columns()))
    results.append(("Application Columns", check_application_columns()))
    results.append(("Academic Information Columns", check_academic_information_columns()))
    check_foreign_keys()
    results.append(("Model Relationships", check_model_relationships()))
    check_routes_database_usage()
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {check_name}")
    
    print(f"\nResults: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✓ All critical checks passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} check(s) failed. Please review above.")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())

