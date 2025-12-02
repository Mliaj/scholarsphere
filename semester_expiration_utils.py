"""
Utility functions for checking semester expirations
Can be called from routes without needing a cron job
"""
from app import db, User, Scholarship, ScholarshipApplication, Notification
from sqlalchemy import text
from datetime import datetime, date
from email_utils import send_email
from flask import url_for

def has_notification_been_sent(scholarship_id, user_id, notification_type, notification_date):
    """Check if a notification has already been sent"""
    try:
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
    except Exception:
        return False

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
    except Exception:
        db.session.rollback()
        return False

def create_notification(user_id, notification_type, title, message):
    """Create an in-app notification"""
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
    except Exception:
        db.session.rollback()
        return False

def send_advance_notification(scholarship, student, days_before, semester_date):
    """Send advance notification to student"""
    notification_type = f"semester_expiring_{days_before}days"
    
    if has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
        return False
    
    formatted_date = semester_date.strftime("%B %d, %Y")
    
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
    
    if create_notification(student.id, 'deadline', title, message):
        try:
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
        except Exception:
            pass  # Email failure shouldn't stop the process
        
        record_notification_sent(scholarship.id, student.id, notification_type, semester_date)
        return True
    
    return False

def process_expired_semester(scholarship, student):
    """Process expired semester - remove student and notify"""
    notification_type = "semester_expired"
    semester_date = scholarship.semester_date
    
    if has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
        return False
    
    # Check if there's a pending renewal application
    pending_renewal = ScholarshipApplication.query.filter_by(
        user_id=student.id,
        scholarship_id=scholarship.id,
        status='pending',
        is_active=True,
        is_renewal=True
    ).first()
    
    # Update application status
    application = ScholarshipApplication.query.filter_by(
        user_id=student.id,
        scholarship_id=scholarship.id,
        status='approved',
        is_active=True
    ).first()
    
    if application:
        # If there's a pending renewal, check if provider approved it
        if pending_renewal:
            # Provider failed to renew - remove both applications
            application.status = 'archived'
            application.is_active = False
            application.reviewed_at = datetime.utcnow()
            # Also archive the renewal application
            pending_renewal.status = 'archived'
            pending_renewal.is_active = False
            db.session.commit()
        else:
            # No renewal attempt - just archive the original
            application.status = 'archived'
            application.is_active = False
            application.reviewed_at = datetime.utcnow()
            db.session.commit()
    
    title = f"Scholarship Semester Expired: {scholarship.title}"
    message = f"The semester for your approved scholarship '{scholarship.title}' has expired. Your application has been removed from this scholarship."
    
    if create_notification(student.id, 'deadline', title, message):
        try:
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
        except Exception:
            pass
        
        record_notification_sent(scholarship.id, student.id, notification_type, semester_date)
        return True
    
    return False

def check_student_semester_expirations(student_id):
    """
    Check and process semester expirations for a specific student
    Called when student logs in or views dashboard/applications
    
    This function:
    - Checks all approved applications for the student
    - Sends advance notifications (1 month, 2 weeks, 1 week, 3 days before)
    - Processes expired semesters (removes student and notifies)
    - Prevents duplicate notifications using the tracking table
    """
    try:
        today = date.today()
        
        # Get all approved applications for this student
        approved_applications = ScholarshipApplication.query.filter_by(
            user_id=student_id,
            status='approved',
            is_active=True
        ).all()
        
        if not approved_applications:
            return
        
        student = User.query.get(student_id)
        if not student or student.role != 'student':
            return
        
        for application in approved_applications:
            scholarship = Scholarship.query.get(application.scholarship_id)
            if not scholarship or not scholarship.semester_date:
                continue
            
            semester_date = scholarship.semester_date
            days_until_expiration = (semester_date - today).days
            
            # Check if expired
            if days_until_expiration < 0:
                process_expired_semester(scholarship, student)
            else:
                # Send only the nearest/closest notification to avoid duplicates
                # Check from closest to farthest and send only the first applicable one
                notification_sent = False
                
                # 3 days notification - highest priority (closest to expiration)
                if days_until_expiration <= 3 and days_until_expiration > 0:
                    notification_type = "semester_expiring_3days"
                    if not has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
                        send_advance_notification(scholarship, student, 3, semester_date)
                        notification_sent = True
                
                # 1 week (7 days) notification
                if not notification_sent and days_until_expiration <= 7 and days_until_expiration > 3:
                    notification_type = "semester_expiring_7days"
                    if not has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
                        send_advance_notification(scholarship, student, 7, semester_date)
                        notification_sent = True
                
                # 2 weeks (14 days) notification
                if not notification_sent and days_until_expiration <= 14 and days_until_expiration > 7:
                    notification_type = "semester_expiring_14days"
                    if not has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
                        send_advance_notification(scholarship, student, 14, semester_date)
                        notification_sent = True
                
                # 1 month (30 days) notification - lowest priority (farthest from expiration)
                if not notification_sent and days_until_expiration <= 30 and days_until_expiration > 14:
                    notification_type = "semester_expiring_30days"
                    if not has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
                        send_advance_notification(scholarship, student, 30, semester_date)
    except Exception:
        # Silently fail - don't break login/dashboard if check fails
        # In production, you might want to log this
        pass

