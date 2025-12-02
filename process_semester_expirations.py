#!/usr/bin/env python3
"""
Process Semester Expirations
Checks for scholarships with expiring semesters and sends notifications to approved students.
Runs advance notifications (1 month, 2 weeks, 1 week, 3 days before) and removes students when semester expires.
"""

from app import app, db, User, Scholarship, ScholarshipApplication, Notification
from sqlalchemy import text
from datetime import datetime, timedelta, date
from email_utils import send_email
import sys

def create_notification(user_id, notification_type, title, message):
    """Create an in-app notification for a user"""
    try:
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            created_at=datetime.utcnow(),
            is_active=True
        )
        db.session.add(notification)
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error creating notification for user {user_id}: {e}")
        db.session.rollback()
        return False

def has_notification_been_sent(scholarship_id, user_id, notification_type, notification_date):
    """Check if a notification has already been sent"""
    result = db.session.execute(
        text("""
            SELECT COUNT(*) 
            FROM semester_expiration_notifications
            WHERE scholarship_id = :scholarship_id
            AND user_id = :user_id
            AND notification_type = :notification_type
            AND notification_date = :notification_date
        """),
        {
            "scholarship_id": scholarship_id,
            "user_id": user_id,
            "notification_type": notification_type,
            "notification_date": notification_date
        }
    ).fetchone()
    return result[0] > 0 if result else False

def record_notification_sent(scholarship_id, user_id, notification_type, notification_date):
    """Record that a notification has been sent"""
    try:
        db.session.execute(
            text("""
                INSERT INTO semester_expiration_notifications 
                (scholarship_id, user_id, notification_type, notification_date, sent_at)
                VALUES (:scholarship_id, :user_id, :notification_type, :notification_date, :sent_at)
            """),
            {
                "scholarship_id": scholarship_id,
                "user_id": user_id,
                "notification_type": notification_type,
                "notification_date": notification_date,
                "sent_at": datetime.utcnow()
            }
        )
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error recording notification: {e}")
        db.session.rollback()
        return False

def send_advance_notification(scholarship, student, days_before, semester_date):
    """Send advance notification to student"""
    notification_type = f"semester_expiring_{days_before}days"
    
    # Check if already sent
    if has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
        return False
    
    # Format the date
    formatted_date = semester_date.strftime("%B %d, %Y")
    
    # Create title and message
    if days_before == 30:
        title = f"Scholarship Semester Expiring in 1 Month: {scholarship.title}"
        message = f"The semester for your approved scholarship '{scholarship.title}' will expire on {formatted_date} (1 month from now). Please prepare accordingly."
    elif days_before == 14:
        title = f"Scholarship Semester Expiring in 2 Weeks: {scholarship.title}"
        message = f"The semester for your approved scholarship '{scholarship.title}' will expire on {formatted_date} (2 weeks from now). Please prepare accordingly."
    elif days_before == 7:
        title = f"Scholarship Semester Expiring in 1 Week: {scholarship.title}"
        message = f"The semester for your approved scholarship '{scholarship.title}' will expire on {formatted_date} (1 week from now). Please prepare accordingly."
    elif days_before == 3:
        title = f"Scholarship Semester Expiring in 3 Days: {scholarship.title}"
        message = f"The semester for your approved scholarship '{scholarship.title}' will expire on {formatted_date} (3 days from now). Please prepare accordingly."
    else:
        return False
    
    # Create in-app notification
    if create_notification(student.id, 'deadline', title, message):
        # Send email
        try:
            from flask import url_for
            dashboard_url = url_for('students.dashboard', _external=True)
            scholarships_url = url_for('students.scholarships', _external=True)
            send_email(
                to=student.email,
                subject=title,
                template='email/semester_expiring_advance.html',
                student_name=student.get_full_name(),
                scholarship_name=scholarship.title,
                scholarship_code=scholarship.code,
                days_before=days_before,
                expiration_date=formatted_date,
                dashboard_url=dashboard_url,
                scholarships_url=scholarships_url
            )
        except Exception as e:
            print(f"Error sending email to {student.email}: {e}")
        
        # Record that notification was sent
        record_notification_sent(scholarship.id, student.id, notification_type, semester_date)
        return True
    
    return False

def process_expired_semester(scholarship, student):
    """Process expired semester - remove student and notify"""
    notification_type = "semester_expired"
    semester_date = scholarship.semester_date
    
    # Check if already processed
    if has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
        return False
    
    # Update application status to archived
    application = ScholarshipApplication.query.filter_by(
        user_id=student.id,
        scholarship_id=scholarship.id,
        status='approved',
        is_active=True
    ).first()
    
    if application:
        application.status = 'archived'
        application.is_active = False
        application.reviewed_at = datetime.utcnow()
        db.session.commit()
    
    # Create notification
    title = f"Scholarship Semester Expired: {scholarship.title}"
    message = f"The semester for your approved scholarship '{scholarship.title}' has expired. Your application has been removed from this scholarship."
    
    if create_notification(student.id, 'deadline', title, message):
        # Send email
        try:
            from flask import url_for
            formatted_date = semester_date.strftime("%B %d, %Y") if semester_date else "N/A"
            scholarships_url = url_for('students.scholarships', _external=True)
            send_email(
                to=student.email,
                subject=title,
                template='email/semester_expired.html',
                student_name=student.get_full_name(),
                scholarship_name=scholarship.title,
                scholarship_code=scholarship.code,
                expiration_date=formatted_date,
                scholarships_url=scholarships_url
            )
        except Exception as e:
            print(f"Error sending email to {student.email}: {e}")
        
        # Record that notification was sent
        record_notification_sent(scholarship.id, student.id, notification_type, semester_date)
        return True
    
    return False

def process_semester_expirations():
    """Main function to process semester expirations"""
    today = date.today()
    
    print(f"Processing semester expirations for {today}")
    print("=" * 70)
    
    # Get all active scholarships with semester_date
    scholarships = Scholarship.query.filter(
        Scholarship.semester_date.isnot(None),
        Scholarship.is_active == True,
        Scholarship.status.in_(['active', 'approved'])
    ).all()
    
    if not scholarships:
        print("No scholarships with semester dates found.")
        return
    
    print(f"Found {len(scholarships)} scholarships with semester dates")
    
    total_notifications = 0
    total_expired = 0
    
    for scholarship in scholarships:
        if not scholarship.semester_date:
            continue
        
        semester_date = scholarship.semester_date
        days_until_expiration = (semester_date - today).days
        
        # Get all approved applications for this scholarship
        approved_applications = ScholarshipApplication.query.filter_by(
            scholarship_id=scholarship.id,
            status='approved',
            is_active=True
        ).all()
        
        if not approved_applications:
            continue
        
        print(f"\nProcessing scholarship: {scholarship.title} (ID: {scholarship.id})")
        print(f"  Semester date: {semester_date}")
        print(f"  Days until expiration: {days_until_expiration}")
        print(f"  Approved applications: {len(approved_applications)}")
        
        for application in approved_applications:
            student = User.query.get(application.user_id)
            if not student or student.role != 'student':
                continue
            
            # Check if semester has expired
            if days_until_expiration < 0:
                # Semester has expired - remove student and notify
                print(f"    Processing expired semester for student: {student.get_full_name()} ({student.email})")
                if process_expired_semester(scholarship, student):
                    total_expired += 1
                    print(f"      ✓ Removed and notified student")
            else:
                # Check for advance notifications
                # We check if we're at or past the target date but haven't sent it yet
                # This allows catching up if the script wasn't run on the exact day
                notification_sent = False
                
                # 1 month (30 days) before - send if we're at or past 30 days but haven't sent
                if days_until_expiration <= 30 and days_until_expiration > 14:
                    notification_type = f"semester_expiring_30days"
                    if not has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
                        print(f"    Sending 1 month advance notification to: {student.get_full_name()}")
                        if send_advance_notification(scholarship, student, 30, semester_date):
                            total_notifications += 1
                            print(f"      ✓ Notification sent")
                            notification_sent = True
                
                # 2 weeks (14 days) before - send if we're at or past 14 days but haven't sent
                if not notification_sent and days_until_expiration <= 14 and days_until_expiration > 7:
                    notification_type = f"semester_expiring_14days"
                    if not has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
                        print(f"    Sending 2 weeks advance notification to: {student.get_full_name()}")
                        if send_advance_notification(scholarship, student, 14, semester_date):
                            total_notifications += 1
                            print(f"      ✓ Notification sent")
                            notification_sent = True
                
                # 1 week (7 days) before - send if we're at or past 7 days but haven't sent
                if not notification_sent and days_until_expiration <= 7 and days_until_expiration > 3:
                    notification_type = f"semester_expiring_7days"
                    if not has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
                        print(f"    Sending 1 week advance notification to: {student.get_full_name()}")
                        if send_advance_notification(scholarship, student, 7, semester_date):
                            total_notifications += 1
                            print(f"      ✓ Notification sent")
                            notification_sent = True
                
                # 3 days before - send if we're at or past 3 days but haven't sent
                if not notification_sent and days_until_expiration <= 3 and days_until_expiration > 0:
                    notification_type = f"semester_expiring_3days"
                    if not has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
                        print(f"    Sending 3 days advance notification to: {student.get_full_name()}")
                        if send_advance_notification(scholarship, student, 3, semester_date):
                            total_notifications += 1
                            print(f"      ✓ Notification sent")
    
    print("\n" + "=" * 70)
    print(f"Processing complete!")
    print(f"  Advance notifications sent: {total_notifications}")
    print(f"  Expired semesters processed: {total_expired}")
    print("=" * 70)

def main():
    """Main entry point"""
    with app.app_context():
        try:
            process_semester_expirations()
        except Exception as e:
            print(f"ERROR: Failed to process semester expirations: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    main()

