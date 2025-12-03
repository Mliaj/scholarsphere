#!/usr/bin/env python3
"""
Helper script to update scholarship dates for testing the renewal system.
This is safer than changing your system date.

Usage:
    python test_renewal_dates.py --scholarship-id 1 --set-semester-days 5
    python test_renewal_dates.py --scholarship-id 1 --set-semester-past
    python test_renewal_dates.py --scholarship-id 1 --set-next-semester-days 180
    python test_renewal_dates.py --scholarship-id 1 --show-dates
    python test_renewal_dates.py --scholarship-id 1 --reset-dates
"""

import sys
import argparse
from datetime import date, timedelta
from sqlalchemy import text

# Import app to get database connection
from app import app, db, Scholarship

def show_dates(scholarship_id):
    """Show current dates for a scholarship"""
    with app.app_context():
        scholarship = Scholarship.query.get(scholarship_id)
        if not scholarship:
            print(f"ERROR: Scholarship with ID {scholarship_id} not found")
            return
        
        today = date.today()
        days_until = None
        if scholarship.semester_date:
            days_until = (scholarship.semester_date - today).days
        
        print(f"\nScholarship: {scholarship.title} (ID: {scholarship.id})")
        print(f"Code: {scholarship.code}")
        print(f"\nCurrent Date: {today.strftime('%Y-%m-%d')}")
        print(f"Semester Date: {scholarship.semester_date.strftime('%Y-%m-%d') if scholarship.semester_date else 'Not set'}")
        if days_until is not None:
            if days_until < 0:
                print(f"  → Expired {abs(days_until)} days ago")
            elif days_until == 0:
                print(f"  → Expires TODAY")
            elif days_until <= 30:
                print(f"  → Expires in {days_until} days (Renewal banner should show)")
            else:
                print(f"  → Expires in {days_until} days")
        print(f"Next Last Semester Date: {scholarship.next_last_semester_date.strftime('%Y-%m-%d') if scholarship.next_last_semester_date else 'Not set'}")
        print()

def set_semester_days(scholarship_id, days):
    """Set semester_date to N days from today"""
    with app.app_context():
        scholarship = Scholarship.query.get(scholarship_id)
        if not scholarship:
            print(f"ERROR: Scholarship with ID {scholarship_id} not found")
            return
        
        new_date = date.today() + timedelta(days=days)
        scholarship.semester_date = new_date
        db.session.commit()
        
        print(f"✓ Updated semester_date to {new_date.strftime('%Y-%m-%d')} ({days} days from today)")
        if days <= 30:
            print("  → Renewal banner should appear for approved applications")
        show_dates(scholarship_id)

def set_semester_past(scholarship_id, days_ago=1):
    """Set semester_date to N days ago (to trigger expiration)"""
    with app.app_context():
        scholarship = Scholarship.query.get(scholarship_id)
        if not scholarship:
            print(f"ERROR: Scholarship with ID {scholarship_id} not found")
            return
        
        new_date = date.today() - timedelta(days=days_ago)
        scholarship.semester_date = new_date
        db.session.commit()
        
        print(f"✓ Updated semester_date to {new_date.strftime('%Y-%m-%d')} ({days_ago} day(s) ago)")
        print("  → Semester expiration should process on next page visit")
        show_dates(scholarship_id)

def set_next_semester_days(scholarship_id, days):
    """Set next_last_semester_date to N days from today"""
    with app.app_context():
        scholarship = Scholarship.query.get(scholarship_id)
        if not scholarship:
            print(f"ERROR: Scholarship with ID {scholarship_id} not found")
            return
        
        new_date = date.today() + timedelta(days=days)
        scholarship.next_last_semester_date = new_date
        db.session.commit()
        
        print(f"✓ Updated next_last_semester_date to {new_date.strftime('%Y-%m-%d')} ({days} days from today)")
        show_dates(scholarship_id)

def clear_next_semester(scholarship_id):
    """Clear next_last_semester_date"""
    with app.app_context():
        scholarship = Scholarship.query.get(scholarship_id)
        if not scholarship:
            print(f"ERROR: Scholarship with ID {scholarship_id} not found")
            return
        
        scholarship.next_last_semester_date = None
        db.session.commit()
        
        print(f"✓ Cleared next_last_semester_date")
        show_dates(scholarship_id)

def reset_dates(scholarship_id):
    """Reset dates to default (6 months from today)"""
    with app.app_context():
        scholarship = Scholarship.query.get(scholarship_id)
        if not scholarship:
            print(f"ERROR: Scholarship with ID {scholarship_id} not found")
            return
        
        default_date = date.today() + timedelta(days=180)
        scholarship.semester_date = default_date
        scholarship.next_last_semester_date = None
        db.session.commit()
        
        print(f"✓ Reset dates:")
        print(f"  → semester_date: {default_date.strftime('%Y-%m-%d')}")
        print(f"  → next_last_semester_date: Cleared")
        show_dates(scholarship_id)

def list_scholarships():
    """List all scholarships"""
    with app.app_context():
        scholarships = Scholarship.query.all()
        if not scholarships:
            print("No scholarships found")
            return
        
        print("\nAvailable Scholarships:")
        print("-" * 80)
        for s in scholarships:
            semester_str = s.semester_date.strftime('%Y-%m-%d') if s.semester_date else 'Not set'
            print(f"ID: {s.id:3d} | {s.title[:40]:40s} | Code: {s.code:10s} | Semester: {semester_str}")
        print("-" * 80)
        print()

def main():
    parser = argparse.ArgumentParser(description='Update scholarship dates for testing renewal system')
    parser.add_argument('--scholarship-id', type=int, help='Scholarship ID to update')
    parser.add_argument('--list', action='store_true', help='List all scholarships')
    parser.add_argument('--set-semester-days', type=int, help='Set semester_date to N days from today')
    parser.add_argument('--set-semester-past', type=int, nargs='?', const=1, help='Set semester_date to N days ago (default: 1)')
    parser.add_argument('--set-next-semester-days', type=int, help='Set next_last_semester_date to N days from today')
    parser.add_argument('--clear-next-semester', action='store_true', help='Clear next_last_semester_date')
    parser.add_argument('--show-dates', action='store_true', help='Show current dates')
    parser.add_argument('--reset-dates', action='store_true', help='Reset dates to default')
    
    args = parser.parse_args()
    
    if args.list:
        list_scholarships()
        return
    
    if not args.scholarship_id:
        print("ERROR: --scholarship-id is required (use --list to see available scholarships)")
        parser.print_help()
        return
    
    if args.show_dates:
        show_dates(args.scholarship_id)
    elif args.set_semester_days is not None:
        set_semester_days(args.scholarship_id, args.set_semester_days)
    elif args.set_semester_past is not None:
        set_semester_past(args.scholarship_id, args.set_semester_past)
    elif args.set_next_semester_days is not None:
        set_next_semester_days(args.scholarship_id, args.set_next_semester_days)
    elif args.clear_next_semester:
        clear_next_semester(args.scholarship_id)
    elif args.reset_dates:
        reset_dates(args.scholarship_id)
    else:
        print("ERROR: No action specified")
        parser.print_help()

if __name__ == '__main__':
    main()

