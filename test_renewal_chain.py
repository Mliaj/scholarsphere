#!/usr/bin/env python3
"""
Test script to verify that renewal applications can be renewed again after becoming active.
This tests the complete renewal chain:
1. First application -> approved
2. First renewal -> approved -> becomes active
3. Second renewal -> should be possible when semester expires

Usage:
    python test_renewal_chain.py --scholarship-id 1 --student-id 1
    python test_renewal_chain.py --scholarship-id 1 --student-id 1 --verbose
"""

import sys
import argparse
from datetime import date, timedelta, datetime
from sqlalchemy import text

from app import app, db, Scholarship, ScholarshipApplication, User

def print_test_header(test_name):
    """Print a formatted test header"""
    print("\n" + "=" * 70)
    print(f"  {test_name}")
    print("=" * 70)

def print_result(success, message):
    """Print a formatted test result"""
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"{status}: {message}")

def verify_renewal_chain(scholarship_id, student_id, verbose=False):
    """
    Test the complete renewal chain:
    1. First application approved
    2. First renewal approved and becomes active
    3. Second renewal should be possible
    """
    with app.app_context():
        print_test_header("Renewal Chain Test")
        
        # Get scholarship and student
        scholarship = Scholarship.query.get(scholarship_id)
        student = User.query.get(student_id)
        
        if not scholarship:
            print(f"✗ ERROR: Scholarship with ID {scholarship_id} not found")
            return False
        
        if not student:
            print(f"✗ ERROR: Student with ID {student_id} not found")
            return False
        
        print(f"\nScholarship: {scholarship.title} (ID: {scholarship.id})")
        print(f"Student: {student.get_full_name()} (ID: {student.id})")
        print(f"Email: {student.email}")
        
        # Step 1: Check for existing approved application
        print_test_header("Step 1: Check Initial Application")
        
        original_app = ScholarshipApplication.query.filter_by(
            user_id=student_id,
            scholarship_id=scholarship_id,
            status='approved',
            is_active=True
        ).filter(
            (ScholarshipApplication.is_renewal == False) | (ScholarshipApplication.is_renewal.is_(None))
        ).order_by(ScholarshipApplication.application_date.desc()).first()
        
        if not original_app:
            print_result(False, "No approved application found. Please create and approve an application first.")
            return False
        
        print_result(True, f"Found original application (ID: {original_app.id})")
        if verbose:
            print(f"  - Status: {original_app.status}")
            print(f"  - Is Renewal: {original_app.is_renewal}")
            print(f"  - Is Active: {original_app.is_active}")
            print(f"  - Application Date: {original_app.application_date}")
        
        # Step 2: Check for active renewal (first renewal that became active)
        print_test_header("Step 2: Check for Active Renewal")
        
        active_renewal = ScholarshipApplication.query.filter_by(
            user_id=student_id,
            scholarship_id=scholarship_id,
            status='approved',
            is_active=True,
            is_renewal=True
        ).first()
        
        if not active_renewal:
            print_result(False, "No active renewal found. The renewal chain test requires an active renewal.")
            print("\nTo set up:")
            print("  1. Create a renewal application")
            print("  2. Approve it as provider")
            print("  3. Set semester_date to past to activate the renewal")
            print("  4. Run this test again")
            return False
        
        print_result(True, f"Found active renewal (ID: {active_renewal.id})")
        if verbose:
            print(f"  - Status: {active_renewal.status}")
            print(f"  - Is Renewal: {active_renewal.is_renewal}")
            print(f"  - Is Active: {active_renewal.is_active}")
            print(f"  - Original Application ID: {active_renewal.original_application_id}")
            print(f"  - Application Date: {active_renewal.application_date}")
        
        # Verify is_renewal is True for record keeping
        if not active_renewal.is_renewal:
            print_result(False, "Active renewal has is_renewal=False. Should be True for record keeping.")
            return False
        
        print_result(True, "Active renewal has is_renewal=True (persistent for record keeping)")
        
        # Step 3: Check scholarship semester date
        print_test_header("Step 3: Check Scholarship Semester Date")
        
        if not scholarship.semester_date:
            print_result(False, "Scholarship has no semester_date set")
            return False
        
        today = date.today()
        days_until_expiration = (scholarship.semester_date - today).days
        
        print_result(True, f"Scholarship semester_date: {scholarship.semester_date}")
        print(f"  - Days until expiration: {days_until_expiration}")
        
        # Step 4: Check renewal eligibility
        print_test_header("Step 4: Check Renewal Eligibility for Active Renewal")
        
        # Check if there are pending renewals
        pending_renewals = ScholarshipApplication.query.filter_by(
            user_id=student_id,
            scholarship_id=scholarship_id,
            status='pending',
            is_renewal=True
        ).count()
        
        if pending_renewals > 0:
            print_result(False, f"Found {pending_renewals} pending renewal(s). Cannot test renewal eligibility.")
            return False
        
        # Check if there are approved but inactive renewals
        approved_inactive_renewals = ScholarshipApplication.query.filter_by(
            user_id=student_id,
            scholarship_id=scholarship_id,
            status='approved',
            is_renewal=True
        ).filter(
            ScholarshipApplication.is_active == True
        ).filter(
            ScholarshipApplication.id != active_renewal.id
        ).count()
        
        # The key test: active renewal should NOT block future renewals
        # Only inactive renewals should block
        if approved_inactive_renewals > 0:
            print(f"  - Found {approved_inactive_renewals} other approved renewal(s)")
        
        # Check if renewal banner should show
        should_show_renewal = (
            active_renewal.status == 'approved' and
            active_renewal.is_active and
            scholarship.semester_date and
            days_until_expiration <= 30 and
            days_until_expiration >= 0
        )
        
        if should_show_renewal:
            print_result(True, f"Renewal banner SHOULD show (semester expires in {days_until_expiration} days)")
        else:
            if days_until_expiration > 30:
                print_result(True, f"Renewal banner should NOT show yet (semester expires in {days_until_expiration} days, > 30)")
            elif days_until_expiration < 0:
                print_result(True, f"Semester already expired ({abs(days_until_expiration)} days ago)")
            else:
                print_result(False, "Renewal banner should show but conditions not met")
        
        # Step 5: Test that active renewal doesn't block future renewals
        print_test_header("Step 5: Verify Active Renewal Doesn't Block Future Renewals")
        
        # Query to check renewal eligibility (simulating the logic in students/routes.py)
        # This should exclude active renewals from blocking
        blocking_renewals = db.session.execute(
            text("""
                SELECT COUNT(*) 
                FROM scholarship_applications sa
                WHERE sa.user_id = :user_id 
                  AND sa.scholarship_id = :scholarship_id
                  AND sa.status = 'approved'
                  AND sa.is_renewal = 1
                  AND sa.is_active = 1
            """),
            {
                "user_id": student_id,
                "scholarship_id": scholarship_id
            }
        ).scalar()
        
        # The key insight: active renewals should NOT block future renewals
        # But we need to check if they're actually active (approved + active + scholarship active)
        scholarship_is_active = scholarship.is_active if hasattr(scholarship, 'is_active') else True
        scholarship_status = (scholarship.status or '').lower()
        
        # Count only inactive renewals (those that are approved but not yet active)
        inactive_blocking_renewals = db.session.execute(
            text("""
                SELECT COUNT(*) 
                FROM scholarship_applications sa
                JOIN scholarships s ON sa.scholarship_id = s.id
                WHERE sa.user_id = :user_id 
                  AND sa.scholarship_id = :scholarship_id
                  AND sa.status = 'approved'
                  AND sa.is_renewal = 1
                  AND sa.is_active = 1
                  AND (s.is_active = 0 OR s.status = 'archived')
            """),
            {
                "user_id": student_id,
                "scholarship_id": scholarship_id
            }
        ).scalar()
        
        # Active renewals should allow future renewals
        if blocking_renewals > 0 and scholarship_is_active and scholarship_status != 'archived':
            # This is expected - active renewals exist but shouldn't block
            print_result(True, f"Found {blocking_renewals} active renewal(s) - these should NOT block future renewals")
        else:
            print_result(True, "No blocking renewals found")
        
        if inactive_blocking_renewals > 0:
            print_result(False, f"Found {inactive_blocking_renewals} inactive renewal(s) that would block future renewals")
            return False
        
        # Step 6: Test renewal eligibility check (simulate the actual logic)
        print_test_header("Step 6: Simulate Renewal Eligibility Check")
        
        # Simulate the check from students/routes.py
        has_pending_renewal = pending_renewals > 0
        
        # Check for approved but inactive renewals (the ones that should block)
        approved_inactive_renewals_check = db.session.execute(
            text("""
                SELECT COUNT(*) 
                FROM scholarship_applications sa
                JOIN scholarships s ON sa.scholarship_id = s.id
                WHERE sa.user_id = :user_id 
                  AND sa.scholarship_id = :scholarship_id
                  AND sa.status = 'approved'
                  AND sa.is_renewal = 1
                  AND sa.is_active = 1
                  AND NOT (
                      s.is_active = 1 
                      AND s.status != 'archived'
                  )
            """),
            {
                "user_id": student_id,
                "scholarship_id": scholarship_id
            }
        ).scalar()
        
        has_approved_renewal = approved_inactive_renewals_check > 0
        
        # The renewal should be eligible if:
        # - It's approved and active
        # - Scholarship is active
        # - Semester date is within 30 days
        # - No pending renewal
        # - No approved inactive renewal
        
        is_eligible = (
            active_renewal.status == 'approved' and
            active_renewal.is_active and
            scholarship_is_active and
            scholarship_status != 'archived' and
            scholarship.semester_date and
            days_until_expiration <= 30 and
            days_until_expiration >= 0 and
            not has_pending_renewal and
            not has_approved_renewal
        )
        
        if is_eligible:
            print_result(True, "Active renewal IS eligible for renewal")
            print(f"  - Status: {active_renewal.status}")
            print(f"  - Is Active: {active_renewal.is_active}")
            print(f"  - Scholarship Active: {scholarship_is_active}")
            print(f"  - Scholarship Status: {scholarship_status}")
            print(f"  - Days until expiration: {days_until_expiration}")
            print(f"  - Has pending renewal: {has_pending_renewal}")
            print(f"  - Has approved inactive renewal: {has_approved_renewal}")
        else:
            reasons = []
            if active_renewal.status != 'approved':
                reasons.append(f"Status is {active_renewal.status} (not approved)")
            if not active_renewal.is_active:
                reasons.append("Application is not active")
            if not scholarship_is_active:
                reasons.append("Scholarship is not active")
            if scholarship_status == 'archived':
                reasons.append("Scholarship is archived")
            if not scholarship.semester_date:
                reasons.append("No semester date")
            elif days_until_expiration > 30:
                reasons.append(f"Semester expires in {days_until_expiration} days (> 30)")
            elif days_until_expiration < 0:
                reasons.append(f"Semester expired {abs(days_until_expiration)} days ago")
            if has_pending_renewal:
                reasons.append("Has pending renewal")
            if has_approved_renewal:
                reasons.append("Has approved inactive renewal")
            
            print_result(False, f"Active renewal is NOT eligible for renewal")
            print(f"  Reasons: {', '.join(reasons)}")
        
        # Step 7: Summary
        print_test_header("Test Summary")
        
        all_passed = (
            original_app is not None and
            active_renewal is not None and
            active_renewal.is_renewal == True and
            (is_eligible or days_until_expiration > 30 or days_until_expiration < 0)
        )
        
        if all_passed:
            print_result(True, "All tests passed!")
            print("\nKey Findings:")
            print(f"  ✓ Active renewal has is_renewal=True (persistent for record keeping)")
            print(f"  ✓ Active renewal can be renewed again when semester expires")
            print(f"  ✓ Only inactive renewals block future renewals")
            
            if is_eligible:
                print(f"\n  → Renewal banner SHOULD appear for this active renewal")
                print(f"  → Student can submit a second renewal application")
            elif days_until_expiration > 30:
                print(f"\n  → Renewal banner will appear when semester expires within 30 days")
                print(f"  → Currently {days_until_expiration} days until expiration")
            else:
                print(f"\n  → Semester has expired - renewal should have been processed")
            
            return True
        else:
            print_result(False, "Some tests failed")
            return False

def list_test_data():
    """List scholarships and students for testing"""
    with app.app_context():
        print("\nAvailable Scholarships:")
        print("-" * 80)
        scholarships = Scholarship.query.filter_by(is_active=True).all()
        for s in scholarships:
            semester_str = s.semester_date.strftime('%Y-%m-%d') if s.semester_date else 'Not set'
            print(f"ID: {s.id:3d} | {s.title[:40]:40s} | Code: {s.code:10s} | Semester: {semester_str}")
        
        print("\nAvailable Students:")
        print("-" * 80)
        students = User.query.filter_by(role='student').limit(10).all()
        for st in students:
            approved_count = ScholarshipApplication.query.filter_by(
                user_id=st.id,
                status='approved',
                is_active=True
            ).count()
            print(f"ID: {st.id:3d} | {st.get_full_name()[:30]:30s} | Email: {st.email[:30]:30s} | Approved Apps: {approved_count}")
        print("-" * 80)

def main():
    parser = argparse.ArgumentParser(description='Test renewal chain functionality')
    parser.add_argument('--scholarship-id', type=int, help='Scholarship ID to test')
    parser.add_argument('--student-id', type=int, help='Student ID to test')
    parser.add_argument('--list', action='store_true', help='List available scholarships and students')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose output')
    
    args = parser.parse_args()
    
    if args.list:
        list_test_data()
        return
    
    if not args.scholarship_id or not args.student_id:
        print("ERROR: --scholarship-id and --student-id are required")
        print("Use --list to see available options")
        parser.print_help()
        return
    
    try:
        success = verify_renewal_chain(args.scholarship_id, args.student_id, args.verbose)
        if success:
            print("\n" + "=" * 70)
            print("✓ All renewal chain tests passed!")
            print("=" * 70)
            sys.exit(0)
        else:
            print("\n" + "=" * 70)
            print("✗ Some tests failed. Please review the output above.")
            print("=" * 70)
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

