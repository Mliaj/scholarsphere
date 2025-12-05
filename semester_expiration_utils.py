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
        # Send email
        email_sent = False
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
            email_sent = True
        except Exception:
            pass  # Email failure shouldn't stop the process, but don't mark as sent
        
        # Only record that notification was sent if email succeeded
        # This allows retry if email fails while keeping the in-app notification
        if email_sent:
            record_notification_sent(scholarship.id, student.id, notification_type, semester_date)
            return True
        else:
            # In-app notification was created but email failed - return False to allow retry
            return False
    
    return False

def process_expired_semester(scholarship, student):
    """Process expired semester - remove student and notify"""
    notification_type = "semester_expired"
    semester_date = scholarship.semester_date
    
    # CRITICAL: Only process expiration if the semester_date has actually expired
    # Don't process if semester_date is in the future
    today = date.today()
    if semester_date and semester_date > today:
        # Semester hasn't expired yet - don't process
        return False
    
    # IMPORTANT: Update semester date FIRST (before notification check)
    # This is a scholarship-level update that should happen regardless of notifications
    # Store the old semester_date before updating (for notes/transitions)
    old_semester_date = semester_date
    # Refresh scholarship to get latest state (in case another student already updated it)
    db.session.refresh(scholarship)
    if scholarship.next_last_semester_date:
        # Update the scholarship's semester_date to next_last_semester_date
        scholarship.semester_date = scholarship.next_last_semester_date
        # Clear next_last_semester_date as it's now the current semester_date
        # Provider can set a new next_last_semester_date for the next renewal cycle
        scholarship.next_last_semester_date = None
        db.session.commit()
        # Refresh again to get the updated semester_date for notification check
        db.session.refresh(scholarship)
        semester_date = scholarship.semester_date
    
    # Now check if notification was already sent (using potentially updated semester_date)
    if has_notification_been_sent(scholarship.id, student.id, notification_type, semester_date):
        return False
    
    # Get all approved renewals (including inactive ones waiting to become active)
    # When a renewal is approved, it's set to is_active=False until the semester expires
    all_approved_renewals = ScholarshipApplication.query.filter_by(
        user_id=student.id,
        scholarship_id=scholarship.id,
        status='approved',
        is_renewal=True
    ).order_by(ScholarshipApplication.application_date.asc()).all()
    
    # Also check for pending renewal (for backward compatibility with old data)
    pending_renewal = ScholarshipApplication.query.filter_by(
        user_id=student.id,
        scholarship_id=scholarship.id,
        status='pending',
        is_renewal=True
    ).filter(ScholarshipApplication.reviewed_at.isnot(None)).first()
    
    # Determine which renewal is waiting (inactive) vs current active (active)
    # Approved renewals with is_active=False are waiting to become active
    # Approved renewals with is_active=True are currently active
    approved_renewal = None  # The waiting renewal (inactive, newest)
    current_active_renewal = None  # The current active renewal (active, oldest)
    
    # Separate renewals by active status
    active_renewals = [r for r in all_approved_renewals if r.is_active]
    inactive_renewals = [r for r in all_approved_renewals if not r.is_active]
    
    if active_renewals:
        # There's at least one active renewal - the oldest active is current
        current_active_renewal = min(active_renewals, key=lambda r: r.application_date)
    
    if inactive_renewals:
        # There's at least one inactive renewal - the newest inactive is waiting
        approved_renewal = max(inactive_renewals, key=lambda r: r.application_date)
    
    # If no inactive renewal found but there's a pending renewal, use that
    if not approved_renewal and pending_renewal:
        approved_renewal = pending_renewal
    
    # Find the old approved application (could be non-renewal OR renewal)
    # Renewal system works the same for both regular and renewed applications
    # Find the oldest approved active application (regardless of whether it's a renewal or not)
    # This ensures renewed applications can be renewed again
    application = ScholarshipApplication.query.filter_by(
        user_id=student.id,
        scholarship_id=scholarship.id,
        status='approved',
        is_active=True
    ).order_by(ScholarshipApplication.application_date.asc()).first()  # Oldest first
    
    # If no application found but there's a current active renewal, use that
    if not application and current_active_renewal:
        application = current_active_renewal
    
    # Track if semester date was updated (to avoid duplicate updates when multiple students have applications)
    # Note: Semester date is already updated at the beginning of the function, so set to True
    semester_date_updated = True
    
    if application:
        # If there's an approved renewal or pending renewal, complete the old one and activate the renewal
        renewal = approved_renewal or pending_renewal
        if renewal:
            # Make sure renewal is different from the application being completed
            if renewal.id == application.id:
                # This shouldn't happen, but if it does, skip to avoid completing the renewal itself
                renewal = None
            
        if renewal and renewal.id != application.id:
            # CRITICAL: Only complete old application and activate renewal if semester has actually expired
            # Check the OLD semester_date (before update) to ensure it has expired
            # old_semester_date was captured at the beginning before any updates
            today = date.today()
            
            # Only proceed if the old semester_date has actually expired (is today or in the past)
            if old_semester_date and old_semester_date > today:
                # Semester hasn't expired yet - don't complete old application or activate renewal
                # The renewal will remain approved but inactive until the semester expires
                return False
            
            # Mark old approved application as completed
            application.status = 'completed'
            application.is_active = False  # Mark as inactive since semester has expired
            application.reviewed_at = datetime.utcnow()
            
            # If renewal was pending, approve it now
            if renewal.status == 'pending':
                renewal.status = 'approved'
                renewal.reviewed_at = datetime.utcnow()
                # Update scholarship counts (renewal becomes approved)
                if scholarship.pending_count and scholarship.pending_count > 0:
                    scholarship.pending_count = max(0, scholarship.pending_count - 1)
                scholarship.approved_count = (scholarship.approved_count or 0) + 1
            
            # Activate the renewal (set is_active = True)
            # This ensures only one application is active per scholarship per student
            renewal.is_active = True
            
            # Note: Semester date update is already handled at the beginning of the function
            # old_semester_date was captured before the update at function start
            
            # Tag renewal with "renewed" in notes and record semester transition
            renewal_note = '[RENEWED] This application became active when the previous semester ended.'
            semester_note = f'\n[Semester Transition] Previous semester ended: {old_semester_date.strftime("%B %d, %Y") if old_semester_date else "N/A"}. New semester date: {scholarship.semester_date.strftime("%B %d, %Y") if scholarship.semester_date else "N/A"}.'
            
            if renewal.notes:
                renewal.notes = renewal.notes + '\n' + renewal_note + semester_note
            else:
                renewal.notes = renewal_note + semester_note
            
            # IMPORTANT: Keep is_renewal=True for record keeping purposes (providers need to see this)
            # The renewal eligibility check in students/routes.py will exclude active renewals
            # (those that are approved, active, and is_renewal=True) from blocking future renewals
            # This allows the renewal to be renewed again when the semester expires
            
            db.session.commit()
            
            # Send notification about renewal activation
            title = f"Renewal Activated: {scholarship.title}"
            message = f"Your renewal for '{scholarship.title}' is now active. Your scholarship continues for the next semester."
            
            if create_notification(student.id, 'application', title, message):
                try:
                    formatted_date = scholarship.semester_date.strftime("%B %d, %Y") if scholarship.semester_date else "N/A"
                    scholarships_url = url_for('students.scholarships', _external=True)
                    send_email(
                        to=student.email,
                        subject=title,
                        template='email/application_status.html',
                        student_name=student.get_full_name(),
                        scholarship_name=scholarship.title,
                        new_status='approved'
                    )
                except Exception:
                    pass
            
            # Don't send expiration notification since renewal was activated
            return True
        else:
            # No renewal attempt - mark as completed and notify
            application.status = 'completed'
            application.is_active = False  # Mark as inactive since semester has expired
            application.reviewed_at = datetime.utcnow()
            db.session.commit()
    
    # Semester date update is now handled at the beginning of the function
    # This ensures it happens regardless of notification status or application state
    
    title = f"Scholarship Semester Completed: {scholarship.title}"
    message = f"The semester for your approved scholarship '{scholarship.title}' has been completed. Your application status has been updated."
    
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
            # Process expiration - this will handle pending renewals appropriately
            if days_until_expiration <= 0:
                # Process expiration - this will approve pending renewals if they've been reviewed
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

def check_all_students_semester_expirations():
    """
    Check and process semester expirations for all students
    Called when provider visits pages to ensure renewals are processed
    
    This function:
    - Gets all students with approved applications
    - Checks semester expirations for each student
    - Processes expired semesters and sends notifications
    """
    try:
        from app import User
        students = User.query.filter_by(role='student').all()
        for student in students:
            try:
                check_student_semester_expirations(student.id)
            except Exception:
                # Continue with next student if one fails
                pass
    except Exception:
        # Silently fail - don't break page load if check fails
        pass

def process_expired_semesters_for_all_scholarships():
    """
    Process expired semesters for ALL scholarships, regardless of student applications
    This ensures semester dates are updated even if no students have applications
    Called when provider accesses pages to ensure semester dates are always up to date
    
    This function:
    - Gets all scholarships with expired semesters that have next_last_semester_date set
    - Updates semester_date to next_last_semester_date
    - Clears next_last_semester_date
    """
    try:
        today = date.today()
        
        # Get all scholarships with expired semesters that have next_last_semester_date set
        expired_scholarships = Scholarship.query.filter(
            Scholarship.semester_date <= today,
            Scholarship.next_last_semester_date.isnot(None)
        ).all()
        
        for scholarship in expired_scholarships:
            try:
                # Refresh to get latest state (in case another process already updated it)
                db.session.refresh(scholarship)
                
                # Double-check that next_last_semester_date still exists (might have been updated)
                if scholarship.next_last_semester_date:
                    # Update the scholarship's semester_date to next_last_semester_date
                    scholarship.semester_date = scholarship.next_last_semester_date
                    # Clear next_last_semester_date as it's now the current semester_date
                    # Provider can set a new next_last_semester_date for the next renewal cycle
                    scholarship.next_last_semester_date = None
                    db.session.commit()
            except Exception:
                # Continue with next scholarship if one fails
                db.session.rollback()
                continue
    except Exception:
        # Silently fail - don't break page load if check fails
        pass

