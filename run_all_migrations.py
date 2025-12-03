#!/usr/bin/env python3
"""
Master migration script to run all database migrations in the correct order.
This script will execute all migration files sequentially.
"""

import sys
from datetime import datetime

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_section(text):
    """Print a formatted section"""
    print(f"\n{'-' * 70}")
    print(f"  {text}")
    print(f"{'-' * 70}")

def main():
    """Run all migrations in the correct order"""
    print_header("SCHOLARSPHERE DATABASE MIGRATION SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # List of migrations in execution order
    migrations = [
        {
            'name': 'Database - User Fields',
            'module': 'migrate_database',
            'function': 'migrate_database',
            'description': 'Add profile_picture, year_level, course, is_active to users'
        },
        {
            'name': 'Users - is_active Column',
            'module': 'migrate_add_is_active',
            'function': 'main',
            'description': 'Ensure is_active column exists in users table'
        },
        {
            'name': 'Scholarships - Deadline Column',
            'module': 'migrate_add_deadline_to_scholarships',
            'function': 'main',
            'description': 'Add deadline column to scholarships table'
        },
        {
            'name': 'Scholarships - Status Counts',
            'module': 'migrate_update_scholarships_counts',
            'function': 'main',
            'description': 'Add pending_count, approved_count, disapproved_count columns'
        },
        {
            'name': 'Scholarships - Extended Fields',
            'module': 'migrate_extend_scholarships_fields',
            'function': 'migrate',
            'description': 'Add description, type, level, eligibility, slots, contact fields'
        },
        {
            'name': 'Awards Table',
            'module': 'migrate_awards_table',
            'function': 'migrate_awards_table',
            'description': 'Create awards table for student achievements'
        },
        {
            'name': 'Credentials - Status Column',
            'module': 'migrate_credentials_status',
            'function': 'migrate_credentials_status',
            'description': 'Add status column to credentials table'
        },
        {
            'name': 'Credentials - Verified Column',
            'module': 'migrate_add_is_verified',
            'function': 'migrate',
            'description': 'Add is_verified column to credentials table'
        },
        {
            'name': 'Scholarship Application Files',
            'module': 'migrate_add_scholarship_application_files',
            'function': 'migrate',
            'description': 'Create scholarship_application_files table'
        },
        {
            'name': 'Application Remarks',
            'module': 'migrate_add_remarks_table',
            'function': 'migrate',
            'description': 'Create application_remarks table for provider reviews'
        },
        {
            'name': 'Student Remarks',
            'module': 'migrate_add_student_remarks_table',
            'function': 'migrate',
            'description': 'Create student_remarks table for provider remarks on students (one-to-many)'
        },
        {
            'name': 'Announcements Table',
            'module': 'migrate_add_announcements_table',
            'function': 'migrate',
            'description': 'Create announcements table for provider sent messages'
        },
        {
            'name': 'Scholarships Table',
            'module': 'create_scholarships_table',
            'function': 'main',
            'description': 'Ensure scholarships table exists with basic structure'
        },
        {
            'name': 'Schedule Migration',
            'module': 'migrate_schedule',
            'function': 'backfill_from_legacy',
            'description': 'Migrate legacy schedule data to new schedule table (optional)',
            'optional': True
        },
        {
            'name': 'Ensure Missing Tables',
            'module': 'migrate_ensure_missing_tables',
            'function': 'migrate',
            'description': 'Final check to ensure scholarship_application_files, application_remarks, and student_remarks exist'
        },
        {
            'name': 'Drop Unique Constraint',
            'module': 'migrate_drop_unique_constraint',
            'function': 'migrate',
            'description': 'Drop restrictive unique_user_scholarship index to allow re-application'
        },
        {
            'name': 'Password Reset Tokens',
            'module': 'migrate_add_password_reset',
            'function': 'migrate',
            'description': 'Add reset_token and reset_token_expires columns to users table'
        },
        {
            'name': 'Scholarship Eligibility Fields',
            'module': 'migrate_add_scholarship_eligibility_fields',
            'function': 'migrate',
            'description': 'Add program_course and additional_criteria columns to scholarships table'
        },
        {
            'name': 'Family Background Table',
            'module': 'migrate_add_family_background_table',
            'function': 'migrate',
            'description': 'Create family_backgrounds table for scholarship application family information'
        },
        {
            'name': 'Academic Information Table',
            'module': 'migrate_add_academic_information_table',
            'function': 'migrate',
            'description': 'Create academic_information table for scholarship application academic details'
        },
        {
            'name': 'Application Personal Information Table',
            'module': 'migrate_add_personal_information_table',
            'function': 'migrate',
            'description': 'Create application_personal_information table for department, school, address, contact'
        },
        {
            'name': 'Scholarships - Semester and Expiration Fields',
            'module': 'migrate_add_scholarship_semester_fields',
            'function': 'migrate',
            'description': 'Add is_expired_deadline, semester, school_year, semester_date, is_expired_semester columns to scholarships table'
        },
        {
            'name': 'Provider Roles and Staff Relationship',
            'module': 'migrate_provider_roles_and_staff',
            'function': 'migrate',
            'description': 'Update provider roles to provider_admin and provider_staff, add managed_by field for staff relationship'
        },
        {
            'name': 'Semester Expiration Notifications Table',
            'module': 'migrate_add_semester_expiration_notifications_table',
            'function': 'migrate',
            'description': 'Create semester_expiration_notifications table to track sent notifications'
        },
        {
            'name': 'Renewal Tracking Fields',
            'module': 'migrate_add_renewal_tracking',
            'function': 'migrate',
            'description': 'Add is_renewal, renewal_failed, and original_application_id columns to scholarship_applications table'
        },
        {
            'name': 'Scholarships - Next Last Semester Date',
            'module': 'migrate_add_next_last_semester_date',
            'function': 'main',
            'description': 'Add next_last_semester_date column to scholarships table for renewal tracking'
        },
        {
            'name': 'Users - Staff Scholarship Type',
            'module': 'migrate_add_staff_scholarship_type',
            'function': 'migrate',
            'description': 'Add scholarship_type column to users table for provider_staff assignment'
        }
    ]
    
    successful = []
    failed = []
    skipped = []
    
    # Run each migration
    for i, migration in enumerate(migrations, 1):
        print_section(f"[{i}/{len(migrations)}] {migration['name']}")
        print(f"Description: {migration['description']}")
        print(f"Module: {migration['module']}.{migration['function']}")
        
        try:
            # Dynamically import and run the migration
            module = __import__(migration['module'])
            func = getattr(module, migration['function'])
            
            # Execute the migration function
            # For optional migrations like schedule, we need to handle them differently
            if migration.get('optional') and migration['module'] == 'migrate_schedule':
                # Schedule migration needs app context
                from app import app
                with app.app_context():
                    result = func(drop_legacy=False)
            else:
                result = func()
            
            # Some migrations return True/False, others return None
            if result is False:
                failed.append(migration['name'])
                print(f"X FAILED: {migration['name']}")
            elif result is None:
                # Assume success if no return value
                successful.append(migration['name'])
                print(f"OK: SUCCESS: {migration['name']}")
            else:
                successful.append(migration['name'])
                print(f"OK: SUCCESS: {migration['name']}")
                
        except ImportError as e:
            failed.append(migration['name'])
            print(f"X IMPORT ERROR: {migration['name']}")
            print(f"   Error: {e}")
        except Exception as e:
            failed.append(migration['name'])
            print(f"X ERROR: {migration['name']}")
            print(f"   Error: {e}")
    
    # Print summary
    print_header("MIGRATION SUMMARY")
    print(f"\nTotal migrations: {len(migrations)}")
    print(f"OK: Successful: {len(successful)}")
    print(f"X Failed: {len(failed)}")
    print(f"> Skipped: {len(skipped)}")
    
    if successful:
        print("\nOK: Successful migrations:")
        for name in successful:
            print(f"   - {name}")
    
    if failed:
        print("\nX Failed migrations:")
        for name in failed:
            print(f"   - {name}")
        print("\nWARNING: Please review the errors above and fix any issues.")
        sys.exit(1)
    
    if skipped:
        print("\n> Skipped migrations:")
        for name in skipped:
            print(f"   - {name}")
    
    print(f"\n{'=' * 70}")
    print("SUCCESS: All migrations completed successfully!")
    print(f"{'=' * 70}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run verification
    print_section("Running Database Verification")
    try:
        from verify_migrations import verify_migrations
        verify_migrations()
    except ImportError:
        print("INFO: Verification script not found, skipping verification")
    except Exception as e:
        print(f"WARNING: Verification failed: {e}")
    
    print("\n" + "=" * 70)
    print("Migration process complete!")
    print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nWARNING: Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

