"""
Student dashboard routes for Scholarsphere
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
import os
import uuid
from datetime import datetime, date
from sqlalchemy import text

students_bp = Blueprint('students', __name__)

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads/profile_pictures'
CREDENTIALS_FOLDER = 'static/uploads/credentials'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 'jfif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@students_bp.route('/dashboard')
@login_required
def dashboard():
    """Student dashboard"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
    # Check semester expirations (no cron job needed - checks on dashboard load)
    try:
        from semester_expiration_utils import check_student_semester_expirations
        check_student_semester_expirations(current_user.id)
    except Exception:
        # Don't fail dashboard load if check fails
        pass
    
    # Get real data from database using raw SQL to avoid circular imports
    from flask import current_app
    db = current_app.extensions['sqlalchemy']
    
    # Count actual credentials uploaded by the student
    total_credentials = db.session.execute(
        text("SELECT COUNT(*) FROM credentials WHERE user_id = :user_id AND is_active = 1"),
        {"user_id": current_user.id}
    ).scalar()
    
    # Count actual scholarship applications
    total_applications = db.session.execute(
        text("SELECT COUNT(*) FROM scholarship_applications WHERE user_id = :user_id AND is_active = 1"),
        {"user_id": current_user.id}
    ).scalar()
    
    # Count approved applications
    approved_applications = db.session.execute(
        text("SELECT COUNT(*) FROM scholarship_applications WHERE user_id = :user_id AND status = 'approved' AND is_active = 1"),
        {"user_id": current_user.id}
    ).scalar()
    
    # Count active applications (approved applications where scholarship is not archived)
    active_applications = db.session.execute(
        text("""
            SELECT COUNT(*) FROM scholarship_applications sa
            JOIN scholarships s ON sa.scholarship_id = s.id
            WHERE sa.user_id = :user_id 
              AND sa.status = 'approved' 
              AND sa.is_active = 1
              AND s.is_active = 1
              AND s.status != 'archived'
        """),
        {"user_id": current_user.id}
    ).scalar() or 0
    
    # Deadlines: count for this month and upcoming months (beyond current month)
    from datetime import date
    today = date.today()
    first_of_month = today.replace(day=1)
    if first_of_month.month == 12:
        first_next_month = first_of_month.replace(year=first_of_month.year + 1, month=1)
    else:
        first_next_month = first_of_month.replace(month=first_of_month.month + 1)

    # Count scholarships with deadlines this month
    this_month_deadlines = db.session.execute(
        text("""
            SELECT COUNT(*) FROM scholarships
            WHERE status IN ('active','approved') AND is_active = 1
              AND deadline IS NOT NULL
              AND DATE(deadline) >= :start AND DATE(deadline) < :end
        """),
        {"start": first_of_month.isoformat(), "end": first_next_month.isoformat()}
    ).scalar() or 0

    # Count scholarships with deadlines in upcoming months (beyond current month)
    upcoming_months_deadlines = db.session.execute(
        text("""
            SELECT COUNT(*) FROM scholarships
            WHERE status IN ('active','approved') AND is_active = 1
              AND deadline IS NOT NULL
              AND DATE(deadline) >= :start
        """),
        {"start": first_next_month.isoformat()}
    ).scalar() or 0

    dashboard_data = {
        'user': current_user,
        'credentials': {
            'total': total_credentials
        },
        'applications': {
            'total': total_applications,
            'approved': approved_applications,
            'active': active_applications
        },
        'deadlines': {
            'this_month': this_month_deadlines,
            'upcoming_months': upcoming_months_deadlines
        }
    }
    
    return render_template('students/dashboard.html', data=dashboard_data)

@students_bp.route('/profile')
@login_required
def profile():
    """Student profile page"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
    # Check semester expirations (no cron job needed - checks on page load)
    try:
        from semester_expiration_utils import check_student_semester_expirations
        check_student_semester_expirations(current_user.id)
    except Exception:
        # Don't fail page load if check fails
        pass
    
    return render_template('students/profile.html', user=current_user)

@students_bp.route('/credentials')
@login_required
def credentials():
    """Student credentials page"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
    # Check semester expirations (no cron job needed - checks on page load)
    try:
        from semester_expiration_utils import check_student_semester_expirations
        check_student_semester_expirations(current_user.id)
    except Exception:
        # Don't fail page load if check fails
        pass
    
    # Get actual credentials from database using raw SQL
    from flask import current_app
    db = current_app.extensions['sqlalchemy']
    
    user_credentials = db.session.execute(
        text("SELECT * FROM credentials WHERE user_id = :user_id AND is_active = 1 ORDER BY upload_date DESC"),
        {"user_id": current_user.id}
    ).fetchall()
    
    # Convert to list of dictionaries for template compatibility
    credentials_list = []
    for cred in user_credentials:
        # Ensure upload_date is a proper datetime object
        upload_date = cred[7]
        if upload_date is not None:
            if isinstance(upload_date, str):
                try:
                    # Try different datetime formats
                    if 'T' in upload_date:
                        upload_date = datetime.fromisoformat(upload_date.replace('Z', '+00:00'))
                    else:
                        # Try parsing as date string
                        upload_date = datetime.strptime(upload_date, '%Y-%m-%d %H:%M:%S')
                except:
                    try:
                        # Try parsing as timestamp string
                        upload_date = datetime.fromtimestamp(float(upload_date))
                    except:
                        upload_date = None
            elif isinstance(upload_date, int):
                # Convert timestamp to datetime
                try:
                    upload_date = datetime.fromtimestamp(upload_date)
                except:
                    upload_date = None
            elif not isinstance(upload_date, datetime):
                upload_date = None
        
        # Get scholarship title(s) for this credential
        scholarship_titles = db.session.execute(
            text("""
                SELECT DISTINCT s.title
                FROM scholarship_application_files saf
                JOIN scholarship_applications sa ON saf.application_id = sa.id
                JOIN scholarships s ON sa.scholarship_id = s.id
                WHERE saf.credential_id = :credential_id
                ORDER BY sa.application_date DESC
            """),
            {"credential_id": cred[0]}
        ).fetchall()
        
        # Get the most recent scholarship title (or first one if multiple)
        scholarship_title = scholarship_titles[0][0] if scholarship_titles else None
        
        credentials_list.append({
            'id': cred[0],
            'user_id': cred[1],
            'credential_type': cred[2],
            'file_name': cred[3],
            'file_path': cred[4],
            'file_size': cred[5],
            'status': cred[6],
            'upload_date': upload_date,
            'is_active': cred[8],
            'scholarship_title': scholarship_title
        })
    
    # Debug: Print credential data to identify the issue
    print("DEBUG: Credentials data:")
    for cred in credentials_list:
        print(f"  ID: {cred['id']}, Upload Date: {cred['upload_date']}, Type: {type(cred['upload_date'])}")
    
    # Get approved scholarship for the student (only if scholarship is not archived)
    approved_scholarship = db.session.execute(
        text("""
            SELECT s.title, s.code, s.is_active, s.status
            FROM scholarship_applications sa
            JOIN scholarships s ON sa.scholarship_id = s.id
            WHERE sa.user_id = :user_id 
              AND sa.status = 'approved' 
              AND sa.is_active = 1
              AND s.is_active = 1
              AND s.status != 'archived'
            ORDER BY sa.reviewed_at DESC
            LIMIT 1
        """),
        {"user_id": current_user.id}
    ).fetchone()
    
    scholarship_name = None
    if approved_scholarship:
        scholarship_name = approved_scholarship[0]  # title
    
    return render_template('students/credentials.html', credentials=credentials_list, user=current_user, scholarship_name=scholarship_name)

@students_bp.route('/applications')
@login_required
def applications():
    """Student applications page"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
    # Check semester expirations (no cron job needed - checks on applications page load)
    try:
        from semester_expiration_utils import check_student_semester_expirations
        check_student_semester_expirations(current_user.id)
    except Exception:
        # Don't fail page load if check fails
        pass
    
    # Get actual applications from database using raw SQL
    from flask import current_app
    from datetime import datetime
    db = current_app.extensions['sqlalchemy']
    
    user_applications = db.session.execute(
        text("""
            SELECT sa.id, sa.user_id, sa.scholarship_id, sa.status, sa.application_date, 
                   s.title, s.deadline, s.is_active as scholarship_is_active, s.status as scholarship_status,
                   s.semester_date, s.code, sa.is_renewal, sa.renewal_failed, sa.reviewed_at, sa.notes, sa.is_active as application_is_active,
                   sa.original_application_id
            FROM scholarship_applications sa
            JOIN scholarships s ON sa.scholarship_id = s.id
            WHERE sa.user_id = :user_id AND (sa.is_active = 1 OR (sa.is_renewal = 1 AND sa.status = 'approved') OR sa.status = 'completed' OR sa.status = 'archived')
            ORDER BY sa.application_date DESC
        """),
        {"user_id": current_user.id}
    ).fetchall()
    
    # Check for pending renewals per scholarship to disable renewal banner
    # Only count applications where is_renewal=True AND status is pending
    pending_renewals_map = {}
    # Track only INACTIVE approved renewals per scholarship (active renewals shouldn't block)
    # Active renewals allow students to renew again when their semester expires
    approved_renewals_map = {}
    for app in user_applications:
        scholarship_id = app[2]
        is_renewal = bool(app[11]) if len(app) > 11 else False
        status = app[3].lower() if app[3] else ''
        application_id = app[0]
        application_is_active = bool(app[15]) if len(app) > 15 else True
        scholarship_is_active = app[7] if len(app) > 7 else True
        scholarship_status = (app[8] or '').lower() if len(app) > 8 else ''
        
        if is_renewal and status == 'pending':
            pending_renewals_map[scholarship_id] = True
        elif is_renewal and status == 'approved':
            # Only track inactive approved renewals (those waiting to become active)
            # Active renewals (approved + active + scholarship active) should NOT block future renewals
            is_currently_active = (status == 'approved' and application_is_active and 
                                 scholarship_is_active and scholarship_status != 'archived')
            if not is_currently_active:
                # This is an inactive approved renewal (waiting for semester to end)
                # Only inactive renewals should block the renewal banner
                if scholarship_id not in approved_renewals_map:
                    approved_renewals_map[scholarship_id] = []
                approved_renewals_map[scholarship_id].append(application_id)
    
    from datetime import date
    today = date.today()
    
    applications_data = []
    for app in user_applications:
        # Parse dates robustly
        app_date = app[4]
        deadline_val = app[6]

        if isinstance(app_date, str):
            try:
                app_date = datetime.fromisoformat(app_date.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    app_date = datetime.strptime(app_date, '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    app_date = datetime.now() # Fallback
        elif not hasattr(app_date, 'strftime'):
            app_date = datetime.now()

        deadline = None
        if deadline_val:
            if isinstance(deadline_val, str):
                try:
                    deadline = datetime.fromisoformat(deadline_val.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    try:
                        deadline = datetime.strptime(deadline_val, '%Y-%m-%d')
                    except (ValueError, TypeError):
                        try:
                            deadline = datetime.strptime(deadline_val, '%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            deadline = None
            elif hasattr(deadline_val, 'strftime'):
                deadline = deadline_val
        
        # Determine if application is active
        # Active = approved AND scholarship is not archived
        scholarship_is_active = app[7] if len(app) > 7 else True
        scholarship_status = (app[8] or '').lower() if len(app) > 8 else ''
        app_status = app[3].lower()
        
        is_active = False
        if app_status == 'approved' and scholarship_is_active and scholarship_status != 'archived':
            is_active = True
        
        # Check semester expiration for renewal
        semester_date_val = app[9] if len(app) > 9 else None
        semester_date = None
        needs_renewal = False
        days_until_expiration = None
        
        # Check renewal eligibility: must be approved and active, and have a semester date
        # EXCEPTION: Don't show renewal banner if:
        # 1. There's already a pending renewal for this scholarship
        # 2. There's an inactive approved renewal waiting (active renewals don't block)
        scholarship_id = app[2]
        application_id = app[0]
        is_renewal_app = bool(app[11]) if len(app) > 11 else False
        has_pending_renewal = pending_renewals_map.get(scholarship_id, False)
        
        # Check if there's an inactive approved renewal for this scholarship
        # Active renewals should NOT block - students can renew active renewals when semester expires
        approved_renewals_list = approved_renewals_map.get(scholarship_id, [])
        has_inactive_approved_renewal = len(approved_renewals_list) > 0

        # Don't show renewal banner if:
        # - There's a pending renewal, OR
        # - There's an inactive approved renewal waiting (active renewals don't block)
        if app_status == 'approved' and is_active and semester_date_val and not has_pending_renewal and not has_inactive_approved_renewal:
            # Parse semester_date from various formats
            try:
                if isinstance(semester_date_val, str):
                    try:
                        semester_date = datetime.strptime(semester_date_val, '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        try:
                            semester_date = datetime.fromisoformat(semester_date_val.replace('Z', '+00:00')).date()
                        except (ValueError, TypeError):
                            semester_date = None
                elif isinstance(semester_date_val, date):
                    # Already a date object
                    semester_date = semester_date_val
                elif hasattr(semester_date_val, 'date'):
                    # datetime object - extract date
                    semester_date = semester_date_val.date()
                elif hasattr(semester_date_val, 'strftime'):
                    # Might be a date-like object
                    try:
                        semester_date = semester_date_val.date() if hasattr(semester_date_val, 'date') else date.fromisoformat(str(semester_date_val))
                    except:
                        semester_date = None
                
                if semester_date:
                    days_until_expiration = (semester_date - today).days
                    # Show renewal if semester expires within 30 days (including today and up to 30 days)
                    if 0 <= days_until_expiration <= 30:
                        needs_renewal = True
            except Exception as e:
                # Silently handle parsing errors - don't break the page
                print(f"Error parsing semester_date for application {app[0]}: {e}")
                semester_date = None
        
        scholarship_code = app[10] if len(app) > 10 else ''
        is_renewal_app = bool(app[11]) if len(app) > 11 else False
        renewal_failed = bool(app[12]) if len(app) > 12 else False
        reviewed_at = app[13] if len(app) > 13 else None
        notes = app[14] if len(app) > 14 else None
        application_is_active = bool(app[15]) if len(app) > 15 else True
        original_application_id = app[16] if len(app) > 16 else None
        
        # Check if this was originally a renewal (for display purposes)
        # This includes both current renewals (is_renewal=True) and applications that were originally renewals
        # (original_application_id is not null indicates it was originally a renewal)
        was_renewal = is_renewal_app or (original_application_id is not None)
        
        # Check if there's an inactive approved renewal for this specific scholarship
        # This is used for display purposes in the template
        # Only inactive renewals block the banner - active renewals don't block
        approved_renewals_list_for_this = approved_renewals_map.get(scholarship_id, [])
        has_approved_renewal_for_this = len(approved_renewals_list_for_this) > 0
        
        # For approved renewals: check if there's still an active non-renewal approved application
        # If so, the renewal should be inactive (but still displayed)
        is_renewal_inactive = False
        if is_renewal_app and app_status == 'approved':
            # Check if there's an active non-renewal approved application for this scholarship
            active_non_renewal = db.session.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM scholarship_applications sa
                    WHERE sa.user_id = :user_id 
                      AND sa.scholarship_id = :scholarship_id
                      AND sa.status = 'approved'
                      AND sa.is_active = 1
                      AND (sa.is_renewal = 0 OR sa.is_renewal IS NULL)
                      AND sa.id != :current_app_id
                """),
                {
                    "user_id": current_user.id,
                    "scholarship_id": scholarship_id,
                    "current_app_id": app[0]
                }
            ).scalar() or 0
            
            if active_non_renewal > 0:
                is_renewal_inactive = True
                # Override is_active to False for display purposes
                is_active = False
        
        applications_data.append({
            'id': f"APP-{app[0]:03d}",
            'scholarship': app[5],
            'status': app[3].title(),
            'date_applied': app_date.strftime('%B %d, %Y'),
            'deadline': deadline.strftime('%B %d, %Y') if deadline else 'No deadline',
            'scholarship_id': app[2],
            'application_id': app[0],
            'is_active': is_active,
            'needs_renewal': needs_renewal,
            'semester_date': semester_date.strftime('%B %d, %Y') if semester_date else None,
            'days_until_expiration': days_until_expiration if days_until_expiration is not None else None,
            'scholarship_code': scholarship_code,
            'is_renewal': is_renewal_app,
            'was_renewal': was_renewal,  # For display purposes - shows "Renewed" tag
            'renewal_failed': renewal_failed,
            'has_approved_renewal': has_approved_renewal_for_this,
            'reviewed_at': reviewed_at,
            'notes': notes,
            'is_renewal_inactive': is_renewal_inactive
        })
    
    return render_template('students/applications.html', applications=applications_data, user=current_user)

@students_bp.route('/scholarships')
@login_required
def scholarships():
    """Available scholarships page"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
    # Check semester expirations (no cron job needed - checks on page load)
    try:
        from semester_expiration_utils import check_student_semester_expirations
        check_student_semester_expirations(current_user.id)
    except Exception:
        # Don't fail page load if check fails
        pass
    
    # Check if this is a renewal redirect
    renewal_scholarship_id = request.args.get('renew', type=int)
    is_renewal = renewal_scholarship_id is not None
    
    # Get actual scholarships from database using raw SQL
    from flask import current_app
    from datetime import datetime
    db = current_app.extensions['sqlalchemy']

    today = datetime.utcnow().date()
    today_date = today.isoformat()
    
    # Update expired deadline status (but keep scholarship active)
    db.session.execute(
        text(
            """
            UPDATE scholarships
            SET is_expired_deadline = 1
            WHERE deadline IS NOT NULL AND deadline < :today AND is_expired_deadline = 0
            """
        ),
        {"today": today}
    )
    
    # Update expired semester status
    db.session.execute(
        text(
            """
            UPDATE scholarships
            SET is_expired_semester = 1
            WHERE semester_date IS NOT NULL AND semester_date < :today AND is_expired_semester = 0
            """
        ),
        {"today": today}
    )
    
    # Reset expiration status if deadline/semester_date is updated to future date
    db.session.execute(
        text(
            """
            UPDATE scholarships
            SET is_expired_deadline = 0
            WHERE deadline IS NOT NULL AND deadline >= :today AND is_expired_deadline = 1
            """
        ),
        {"today": today}
    )
    
    db.session.execute(
        text(
            """
            UPDATE scholarships
            SET is_expired_semester = 0
            WHERE semester_date IS NOT NULL AND semester_date >= :today AND is_expired_semester = 1
            """
        ),
        {"today": today}
    )
    
    db.session.commit()
    
    # Build query - filter by renewal scholarship if applicable
    if is_renewal and renewal_scholarship_id:
        available_scholarships = db.session.execute(
            text(
                """
                SELECT s.id, s.code, s.title, s.description, s.amount, s.deadline, s.requirements, u.organization,
                       s.type, s.level, s.eligibility, s.program_course, s.additional_criteria, s.slots, s.contact_name, s.contact_email, s.contact_phone,
                       s.is_expired_deadline, s.semester, s.school_year, s.semester_date, s.is_expired_semester, s.next_last_semester_date
                FROM scholarships s
                LEFT JOIN users u ON s.provider_id = u.id
                WHERE s.id = :scholarship_id AND s.status IN ('active','approved') AND s.is_active = 1
                ORDER BY s.deadline ASC
                """
            ),
            {"scholarship_id": renewal_scholarship_id}
        ).fetchall()
    else:
        available_scholarships = db.session.execute(
            text(
                """
                SELECT s.id, s.code, s.title, s.description, s.amount, s.deadline, s.requirements, u.organization,
                       s.type, s.level, s.eligibility, s.program_course, s.additional_criteria, s.slots, s.contact_name, s.contact_email, s.contact_phone,
                       s.is_expired_deadline, s.semester, s.school_year, s.semester_date, s.is_expired_semester, s.next_last_semester_date
                FROM scholarships s
                LEFT JOIN users u ON s.provider_id = u.id
                WHERE s.status IN ('active','approved') AND s.is_active = 1
                ORDER BY s.deadline ASC
                """
            )
        ).fetchall()

    # Fetch all applications for the current user in one query
    user_applications = db.session.execute(
        text(
            """
            SELECT scholarship_id, status FROM scholarship_applications 
            WHERE user_id = :user_id AND is_active = 1
            """
        ),
        {"user_id": current_user.id}
    ).fetchall()

    # Create a dictionary for quick lookups of application status
    application_statuses = {app.scholarship_id: app.status for app in user_applications}
    
    scholarships_data = []
    for scholarship in available_scholarships:
        scholarship_id = scholarship[0]
        existing_application_status = application_statuses.get(scholarship_id)
        
        # Parse deadline
        deadline_val = scholarship[5]
        deadline = None
        if deadline_val:
            if isinstance(deadline_val, str):
                try:
                    deadline = datetime.fromisoformat(deadline_val.replace('Z','+00:00'))
                except:
                    # Try simple date format if isoformat fails
                    try:
                        deadline = datetime.strptime(deadline_val, '%Y-%m-%d')
                    except:
                        deadline = None
            elif hasattr(deadline_val, 'strftime'):
                deadline = deadline_val
            else:
                deadline = None
        
        # Convert requirements from short codes to descriptive names
        requirements_raw = scholarship[6] or ''
        requirements_display = []
        if requirements_raw and requirements_raw != 'No specific requirements':
            from credential_matcher import CredentialMatcher
            req_codes = [req.strip() for req in requirements_raw.split(',') if req.strip()]
            for req_code in req_codes:
                if req_code in CredentialMatcher.REQUIREMENT_MAPPINGS:
                    requirements_display.append(CredentialMatcher.REQUIREMENT_MAPPINGS[req_code][0])
                else:
                    requirements_display.append(req_code)  # Keep custom requirements as-is
        
        has_applied = (existing_application_status is not None and existing_application_status.lower() in ['pending', 'approved'])
        can_apply_again = (existing_application_status is not None and existing_application_status.lower() in ['rejected', 'withdrawn'])
        
        # Check if student can renew (has approved application and semester expiring within 30 days)
        can_renew = False
        has_pending_renewal = False
        if existing_application_status and existing_application_status.lower() == 'approved':
            # Check if there's a pending renewal application
            pending_renewal = db.session.execute(
                text("""
                    SELECT id FROM scholarship_applications
                    WHERE user_id = :user_id 
                    AND scholarship_id = :scholarship_id
                    AND is_renewal = 1
                    AND status = 'pending'
                    AND is_active = 1
                """),
                {"user_id": current_user.id, "scholarship_id": scholarship_id}
            ).fetchone()
            
            if pending_renewal:
                has_pending_renewal = True
            else:
                # Check if semester is expiring within 30 days
                # Parse semester_date first
                semester_date_val = scholarship[20] if len(scholarship) > 20 else None
                if semester_date_val:
                    try:
                        semester_date_obj = None
                        if isinstance(semester_date_val, str):
                            try:
                                semester_date_obj = datetime.strptime(semester_date_val, '%Y-%m-%d').date()
                            except:
                                try:
                                    semester_date_obj = datetime.fromisoformat(semester_date_val.replace('Z','+00:00')).date()
                                except:
                                    semester_date_obj = None
                        elif isinstance(semester_date_val, datetime):
                            semester_date_obj = semester_date_val.date()
                        elif isinstance(semester_date_val, date):
                            semester_date_obj = semester_date_val
                        elif hasattr(semester_date_val, 'date'):
                            semester_date_obj = semester_date_val.date()
                        elif hasattr(semester_date_val, 'strftime'):
                            # Try to convert to date
                            try:
                                semester_date_obj = semester_date_val.date() if hasattr(semester_date_val, 'date') else None
                            except:
                                semester_date_obj = None
                        
                        if semester_date_obj:
                            today = datetime.utcnow().date()
                            days_until_expiration = (semester_date_obj - today).days
                            if 0 <= days_until_expiration <= 30:
                                can_renew = True
                    except Exception as e:
                        print(f"Error checking renewal eligibility: {e}")
                        pass
        
        # Check expiration status
        is_expired_deadline = bool(scholarship[17]) if len(scholarship) > 17 else False
        is_expired_semester = bool(scholarship[21]) if len(scholarship) > 21 else False
        is_expired = is_expired_deadline or is_expired_semester
        
        # Parse semester_date for display
        semester_date_val = scholarship[20] if len(scholarship) > 20 else None
        semester_date = None
        if semester_date_val:
            if isinstance(semester_date_val, str):
                try:
                    semester_date = datetime.fromisoformat(semester_date_val.replace('Z','+00:00'))
                except:
                    try:
                        semester_date = datetime.strptime(semester_date_val, '%Y-%m-%d')
                    except:
                        semester_date = None
            elif hasattr(semester_date_val, 'strftime'):
                semester_date = semester_date_val
        
        # Parse next_last_semester_date for display
        next_last_semester_date_val = scholarship[22] if len(scholarship) > 22 else None
        next_last_semester_date = None
        if next_last_semester_date_val:
            if isinstance(next_last_semester_date_val, str):
                try:
                    next_last_semester_date = datetime.fromisoformat(next_last_semester_date_val.replace('Z','+00:00'))
                except:
                    try:
                        next_last_semester_date = datetime.strptime(next_last_semester_date_val, '%Y-%m-%d')
                    except:
                        next_last_semester_date = None
            elif hasattr(next_last_semester_date_val, 'strftime'):
                next_last_semester_date = next_last_semester_date_val
        
        # Check if scholarship matches student's course
        is_matching_course = False
        student_course = (current_user.course or '').strip().upper()
        scholarship_course = (scholarship[11] or '').strip().upper()
        
        if student_course and scholarship_course:
            # Check if "All Programs" is selected - matches all courses
            if scholarship_course == 'ALL PROGRAMS':
                is_matching_course = True
            else:
                # Check for exact match or if scholarship course contains student course or vice versa
                # Also handle comma-separated courses in scholarship (e.g., "BSIT, BSCS, BSCE")
                scholarship_courses = [c.strip().upper() for c in scholarship_course.split(',')]
                is_matching_course = student_course in scholarship_courses or any(
                    student_course in sc or sc in student_course 
                    for sc in scholarship_courses
                )

        scholarships_data.append({
            'id': scholarship[1] or f"SCH-{scholarship_id:03d}",
            'title': scholarship[2],
            'description': scholarship[3] or 'No description available',
            'amount': scholarship[4] or 'Amount not specified',
            'deadline': deadline.strftime('%B %d, %Y') if deadline else 'No deadline',
            'requirements': requirements_display if requirements_display else [],
            'requirements_display': ', '.join(requirements_display) if requirements_display else 'No specific requirements',
            'provider': scholarship[7] or 'University of Cebu',
            'type': scholarship[8] or 'Not specified',
            'level': scholarship[9] or 'Not specified',
            'eligibility': scholarship[10] or '',  # Minimum GPA
            'program_course': scholarship[11] or '',
            'additional_criteria': scholarship[12] or '',
            'slots': scholarship[13] or 'Unlimited',
            'contact_name': scholarship[14] or '',
            'contact_email': scholarship[15] or '',
            'contact_phone': scholarship[16] or '',
            'scholarship_id': scholarship_id,
            'has_applied': has_applied,
            'application_status': existing_application_status,
            'can_apply_again': can_apply_again,
            'can_renew': can_renew,
            'has_pending_renewal': has_pending_renewal,
            'is_matching_course': is_matching_course,
            'is_expired': is_expired,
            'is_expired_deadline': is_expired_deadline,
            'is_expired_semester': is_expired_semester,
            'semester': scholarship[18] if len(scholarship) > 18 else '',
            'school_year': scholarship[19] if len(scholarship) > 19 else '',
            'semester_date': semester_date.strftime('%B %d, %Y') if semester_date else None,
            'next_last_semester_date': next_last_semester_date.strftime('%B %d, %Y') if next_last_semester_date else None
        })
    
    current_year = datetime.utcnow().year
    
    return render_template('students/scholarships.html', 
                         scholarships=scholarships_data, 
                         user=current_user, 
                         today_date=today_date,
                         is_renewal=is_renewal,
                         renewal_scholarship_id=renewal_scholarship_id,
                         current_year=current_year)

@students_bp.route('/apply-scholarship/<int:scholarship_id>', methods=['POST'])
@login_required
def apply_scholarship(scholarship_id):
    """Apply to a scholarship with credential selection"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from flask import current_app
        from datetime import datetime
        import json
        db = current_app.extensions['sqlalchemy']
        
        # Ensure current_time is always defined
        current_time = datetime.utcnow().isoformat()
        
        # Check if this is a renewal application
        is_renewal = False
        original_application_id = None
        
        # Get form data - handle both JSON and FormData
        if request.is_json:
            form_data = request.get_json()
            selected_credentials = form_data.get('selected_credentials', {})
            is_renewal = form_data.get('is_renewal', False)
            original_application_id = form_data.get('original_application_id')
        else:
            # Handle form data
            form_data = request.form.to_dict()
            # Parse selected_credentials from JSON string if it exists
            credentials_str = request.form.get('selected_credentials', '{}')
            try:
                selected_credentials = json.loads(credentials_str)
            except (json.JSONDecodeError, ValueError):
                selected_credentials = {}
            is_renewal = request.form.get('is_renewal', 'false').lower() == 'true'
            original_app_id_str = request.form.get('original_application_id')
            if original_app_id_str:
                try:
                    original_application_id = int(original_app_id_str)
                except (ValueError, TypeError):
                    original_application_id = None
        
        # If renewal, find the original approved application
        # This works the same for both regular and renewed applications
        # It finds the most recent approved active application (regardless of whether it's a renewal or not)
        if is_renewal:
            original_app = db.session.execute(
                text("""
                    SELECT id FROM scholarship_applications
                    WHERE user_id = :user_id 
                    AND scholarship_id = :scholarship_id
                    AND status = 'approved'
                    AND is_active = 1
                    ORDER BY application_date DESC
                    LIMIT 1
                """),
                {"user_id": current_user.id, "scholarship_id": scholarship_id}
            ).fetchone()
            
            if original_app:
                original_application_id = original_app[0]
            else:
                # If no original app found, don't treat as renewal
                is_renewal = False
        
        # Check if scholarship exists and is active
        today = datetime.utcnow().date()
        scholarship = db.session.execute(
            text("""
                SELECT id, status, applications_count, pending_count, requirements, 
                       deadline, is_expired_deadline, semester_date, is_expired_semester
                FROM scholarships 
                WHERE id = :id AND is_active = 1
            """),
            {"id": scholarship_id}
        ).fetchone()
                    
        if not scholarship:
            return jsonify({'success': False, 'message': 'Scholarship not found'}), 404

        # Block applying if scholarship is closed or archived (not active/approved)
        scholarship_status = (scholarship[1] or '').lower()
        if scholarship_status not in ['active', 'approved']:
             return jsonify({'success': False, 'message': 'This scholarship is closed or archived and is no longer accepting applications.'}), 400
        
        # Check if scholarship is expired (deadline or semester)
        is_expired_deadline = bool(scholarship[6]) if len(scholarship) > 6 else False
        is_expired_semester = bool(scholarship[8]) if len(scholarship) > 8 else False
        
        # Also check deadline directly if not already marked as expired
        if not is_expired_deadline and scholarship[5]:
            deadline_date = scholarship[5]
            if isinstance(deadline_date, str):
                try:
                    deadline_date = datetime.strptime(deadline_date, '%Y-%m-%d').date()
                except:
                    deadline_date = None
            if deadline_date and deadline_date < today:
                is_expired_deadline = True
        
        # Check semester_date directly if not already marked as expired
        if not is_expired_semester and scholarship[7]:
            semester_date = scholarship[7]
            if isinstance(semester_date, str):
                try:
                    semester_date = datetime.strptime(semester_date, '%Y-%m-%d').date()
                except:
                    semester_date = None
            if semester_date and semester_date < today:
                is_expired_semester = True
        
        if is_expired_deadline or is_expired_semester:
            reason = []
            if is_expired_deadline:
                reason.append("deadline has passed")
            if is_expired_semester:
                reason.append("semester date has passed")
            return jsonify({
                'success': False, 
                'message': f'This scholarship is expired. The {" and ".join(reason)}. Please contact the provider if you believe this is an error.'
            }), 400
        
        # GLOBAL CHECK: Does the student have an APPROVED application for ANY scholarship?
        # If they are already a scholar (approved anywhere), they cannot apply for new ones.
        # EXCEPTION: Allow renewal applications - students can renew even if they have approved scholarship
        if not is_renewal:
            global_approved = db.session.execute(
                text(
                    """
                    SELECT s.title 
                    FROM scholarship_applications sa
                    JOIN scholarships s ON sa.scholarship_id = s.id
                    WHERE sa.user_id = :user_id 
                      AND LOWER(sa.status) = 'approved' 
                      AND sa.is_active = 1
                      AND (sa.is_renewal = 0 OR sa.is_renewal IS NULL)
                    LIMIT 1
                    """
                ),
                {"user_id": current_user.id}
            ).fetchone()

            if global_approved:
                return jsonify({
                    'success': False, 
                    'message': f"You already have an approved scholarship ({global_approved[0]}). You cannot apply for others."
                }), 400

        # STRICT CHECK: Has the student EVER been approved for THIS scholarship?
        # Using lower() and trimming whitespace.
        # EXCEPTION: Allow renewal applications
        if not is_renewal:
            already_approved = db.session.execute(
                text(
                    """
                    SELECT id, status FROM scholarship_applications
                    WHERE user_id = :user_id 
                      AND scholarship_id = :scholarship_id 
                      AND LOWER(TRIM(status)) = 'approved' 
                      AND is_active = 1
                    LIMIT 1
                    """
                ),
                {"user_id": current_user.id, "scholarship_id": scholarship_id}
            ).fetchone()

            if already_approved:
                return jsonify({'success': False, 'message': 'You have already been approved for this scholarship.'}), 400
        else:
            # For renewals, check if there's already a pending renewal
            existing_renewal = db.session.execute(
                text(
                    """
                    SELECT id FROM scholarship_applications
                    WHERE user_id = :user_id 
                      AND scholarship_id = :scholarship_id 
                      AND is_renewal = 1
                      AND status = 'pending'
                      AND is_active = 1
                    LIMIT 1
                    """
                ),
                {"user_id": current_user.id, "scholarship_id": scholarship_id}
            ).fetchone()
            
            if existing_renewal:
                return jsonify({'success': False, 'message': 'You already have a pending renewal application for this scholarship.'}), 400

        # Check for any PENDING application for this scholarship
        pending_application = db.session.execute(
            text(
                """
                SELECT id FROM scholarship_applications 
                WHERE user_id = :user_id 
                  AND scholarship_id = :scholarship_id 
                  AND LOWER(TRIM(status)) = 'pending' 
                  AND is_active = 1
                LIMIT 1
                """
            ),
            {"user_id": current_user.id, "scholarship_id": scholarship_id}
        ).fetchone()

        if pending_application:
            return jsonify({'success': False, 'message': 'You already have a pending application for this scholarship.'}), 400
        
        # No existing row for this user/scholarship: create a brand new application
        # Check if renewal columns exist before including them
        result = db.session.execute(
            text("""\
                INSERT INTO scholarship_applications (user_id, scholarship_id, status, application_date, is_active, is_renewal, original_application_id, renewal_failed)
                VALUES (:user_id, :scholarship_id, :status, :application_date, :is_active, :is_renewal, :original_application_id, :renewal_failed)
            """),
            {
                "user_id": current_user.id,
                "scholarship_id": scholarship_id,
                "status": 'pending',
                "application_date": current_time,
                "is_active": 1,
                "is_renewal": 1 if is_renewal else 0,
                "original_application_id": original_application_id,
                "renewal_failed": 0  # Default to 0 (False) for new applications
            }
        )
        application_id = result.lastrowid
        
        # Save Family Background information
        if 'guardian' in form_data and form_data.get('guardian'):
            try:
                db.session.execute(
                    text("""
                        INSERT INTO family_backgrounds 
                        (application_id, parent_guardian_name, occupation, household_income, dependents, created_at)
                        VALUES (:application_id, :parent_guardian_name, :occupation, :household_income, :dependents, :created_at)
                    """),
                    {
                        "application_id": application_id,
                        "parent_guardian_name": form_data.get('guardian', ''),
                        "occupation": form_data.get('occupation', ''),
                        "household_income": form_data.get('income', ''),
                        "dependents": int(form_data.get('dependents', 0)) if form_data.get('dependents') else None,
                        "created_at": current_time
                    }
                )
            except Exception as e:
                print(f"Warning: Could not save family background: {e}")
        
        # Save Academic Information
        if any(form_data.get(k) for k in ['gpa', 'semester', 'school_year']):
            try:
                db.session.execute(
                    text("""
                        INSERT INTO academic_information 
                        (application_id, latest_gpa, current_semester, school_year, created_at)
                        VALUES (:application_id, :latest_gpa, :current_semester, :school_year, :created_at)
                    """),
                    {
                        "application_id": application_id,
                        "latest_gpa": form_data.get('gpa', ''),
                        "current_semester": form_data.get('semester', ''),
                        "school_year": form_data.get('school_year', ''),
                        "created_at": current_time
                    }
                )
            except Exception as e:
                print(f"Warning: Could not save academic information: {e}")
        
        # Save Personal Information (department, school, address, contact)
        if any(form_data.get(k) for k in ['department', 'school', 'address', 'contact']):
            try:
                db.session.execute(
                    text("""
                        INSERT INTO application_personal_information 
                        (application_id, department, school_university, address, contact_number, created_at)
                        VALUES (:application_id, :department, :school_university, :address, :contact_number, :created_at)
                    """),
                    {
                        "application_id": application_id,
                        "department": form_data.get('department', ''),
                        "school_university": form_data.get('school', ''),
                        "address": form_data.get('address', ''),
                        "contact_number": form_data.get('contact', ''),
                        "created_at": current_time
                    }
                )
            except Exception as e:
                print(f"Warning: Could not save personal information: {e}")
        
        # Link selected credentials to the application (if any requirements exist)
        if selected_credentials and len(selected_credentials) > 0:
            for requirement, credential_id in selected_credentials.items():
                if credential_id and credential_id != '':
                    try:
                        db.session.execute(
                            text("""
                                INSERT INTO scholarship_application_files (application_id, credential_id, requirement_type)
                                VALUES (:application_id, :credential_id, :requirement_type)
                            """),
                            {
                                "application_id": application_id,
                                "credential_id": int(credential_id),
                                "requirement_type": requirement
                            }
                        )
                    except Exception as e:
                        # Skip invalid credential selections
                        print(f"Warning: Could not link credential {credential_id} for requirement {requirement}: {e}")
                        continue
        
        # Update scholarship application count only when we created a new row.
        db.session.execute(
            text(
                """\
                UPDATE scholarships 
                SET applications_count = COALESCE(applications_count, 0) + 1, 
                    pending_count     = COALESCE(pending_count, 0) + 1
                WHERE id = :id
                """
            ),
            {"id": scholarship_id}
        )

        db.session.commit()

        # Create notification for application submission (raw SQL)
        try:
            if is_renewal:
                # Renewal submission notification
                notification_title = 'Renewal Application Submitted'
                notification_message = 'Your scholarship renewal application has been submitted successfully. Please wait for provider review.'
                
                # Send email notification for renewal
                try:
                    from email_utils import send_email
                    from flask import url_for
                    scholarship_info = db.session.execute(
                        text("SELECT title, code FROM scholarships WHERE id = :id"),
                        {"id": scholarship_id}
                    ).fetchone()
                    
                    if scholarship_info:
                        scholarship_title = scholarship_info[0] or 'Scholarship'
                        scholarship_code = scholarship_info[1] or ''
                        dashboard_url = url_for('students.dashboard', _external=True)
                        
                        send_email(
                            to=current_user.email,
                            subject=notification_title,
                            template='email/renewal_submitted.html',
                            student_name=current_user.get_full_name(),
                            scholarship_name=scholarship_title,
                            scholarship_code=scholarship_code,
                            dashboard_url=dashboard_url
                        )
                except Exception as e:
                    print(f"Error sending renewal email: {e}")
            else:
                notification_title = 'Application Submitted'
                notification_message = 'Your scholarship application has been submitted successfully.'
            
            db.session.execute(
                text("""
                    INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                    VALUES (:user_id, :type, :title, :message, :created_at, 1)
                """),
                {
                    "user_id": current_user.id,
                    "type": 'application',
                    "title": notification_title,
                    "message": notification_message,
                    "created_at": datetime.utcnow()
                }
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        
        response_data = {
            'success': True,
            'message': 'Renewal application submitted successfully' if is_renewal else 'Application submitted successfully with credentials'
        }
        
        # If renewal, add redirect flag to go to applications page
        if is_renewal:
            response_data['redirect'] = url_for('students.applications')
        
        return jsonify(response_data)
        
    except Exception as e:
        if 'db' in locals():
            db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error submitting application: {str(e)}")
        print(f"Traceback: {error_details}")
        return jsonify({'success': False, 'message': f'Failed to submit application: {str(e)}'}), 500

@students_bp.route('/api/scholarship/<int:scholarship_id>/credentials')
@login_required
def get_scholarship_credentials(scholarship_id):
    """Get available credentials for a scholarship application"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from flask import current_app
        from credential_matcher import CredentialMatcher
        db = current_app.extensions['sqlalchemy']
        
        # Get scholarship requirements
        scholarship = db.session.execute(
            text("SELECT requirements FROM scholarships WHERE id = :id AND status IN ('active','approved') AND is_active = 1"),
            {"id": scholarship_id}
        ).fetchone()
        
        if not scholarship:
            return jsonify({'success': False, 'message': 'Scholarship not found'}), 404
        
        requirements = (scholarship[0] or '').split(',')
        requirements = [req.strip() for req in requirements if req.strip()]
        
        # Get student's available credentials
        user_credentials = db.session.execute(
            text("SELECT * FROM credentials WHERE user_id = :user_id AND is_active = 1 ORDER BY upload_date DESC"),
            {"user_id": current_user.id}
        ).fetchall()
        
        # Convert to list of dictionaries
        credentials_list = []
        for cred in user_credentials:
            credentials_list.append({
                'id': cred[0],
                'user_id': cred[1],
                'credential_type': cred[2],
                'file_name': cred[3],
                'file_path': cred[4],
                'file_size': cred[5],
                'status': cred[6],
                'upload_date': cred[7],
                'is_active': cred[8]
            })
        
        # Use credential matcher to find matches
        credential_matches = CredentialMatcher.find_matching_credentials(requirements, credentials_list)
        
        # Prepare response with requirement status
        response_data = {
            'requirements': [],
            'available_credentials': credentials_list
        }
        
        for requirement in requirements:
            matches = credential_matches.get(requirement, [])
            status, best_match = CredentialMatcher.get_requirement_status(requirement, credentials_list)
            
            # Convert short code to descriptive name for display
            display_name = requirement
            if requirement in CredentialMatcher.REQUIREMENT_MAPPINGS:
                display_name = CredentialMatcher.REQUIREMENT_MAPPINGS[requirement][0]
            
            response_data['requirements'].append({
                'requirement': display_name,  # Use descriptive name for display
                'requirement_code': requirement,  # Keep original code for matching
                'status': status,
                'matches': matches,
                'best_match': best_match,
                'suggested_type': CredentialMatcher.suggest_credential_type(requirement)
            })
        
        return jsonify({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to get credentials data'}), 500

@students_bp.route('/withdraw-application/<int:application_id>', methods=['POST'])
@login_required
def withdraw_application(application_id):
    """Withdraw a scholarship application"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        
        # Find the application and its scholarship/provider
        application = db.session.execute(
            text("""\
                SELECT sa.id, sa.status, sa.scholarship_id, s.provider_id
                FROM scholarship_applications sa
                JOIN scholarships s ON sa.scholarship_id = s.id
                WHERE sa.id = :id AND sa.user_id = :user_id AND sa.is_active = 1
            """),
            {"id": application_id, "user_id": current_user.id}
        ).fetchone()
        
        if not application:
            return jsonify({'success': False, 'message': 'Application not found'}), 404
        
        current_status = (application[1] or '').lower()
        if current_status not in ['pending']:
            if current_status == 'completed':
                return jsonify({'success': False, 'message': 'Cannot withdraw a completed application'}), 400
            return jsonify({'success': False, 'message': 'Cannot withdraw application that has been reviewed'}), 400
        
        scholarship_id = application[2]
        provider_id = application[3]
        
        # Update application status (soft delete + mark as withdrawn)
        db.session.execute(
            text("""\
                UPDATE scholarship_applications 
                SET status = 'withdrawn', is_active = 0
                WHERE id = :id
            """),
            {"id": application_id}
        )
        
        # Update scholarship counts (defensive against NULLs)
        db.session.execute(
            text("""\
                UPDATE scholarships 
                SET applications_count = CASE WHEN COALESCE(applications_count,0) > 0 THEN applications_count - 1 ELSE 0 END,
                    pending_count      = CASE WHEN COALESCE(pending_count,0) > 0 THEN pending_count - 1 ELSE 0 END
                WHERE id = :id
            """),
            {"id": scholarship_id}
        )
        
        # Notifications: student + provider (if available)
        now = datetime.utcnow()
        # Student notification
        db.session.execute(
            text("""\
                INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                VALUES (:user_id, :type, :title, :message, :created_at, 1)
            """),
            {
                "user_id": current_user.id,
                "type": 'application',
                "title": 'Application Withdrawn',
                "message": 'You withdrew a scholarship application.',
                "created_at": now
            }
        )
        
        # Provider notification (if provider_id is present)
        if provider_id:
            db.session.execute(
                text("""\
                    INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                    VALUES (:user_id, :type, :title, :message, :created_at, 1)
                """),
                {
                    "user_id": provider_id,
                    "type": 'application',
                    "title": 'Student Application Withdrawn',
                    "message": 'A student has withdrawn their application for one of your scholarships.',
                    "created_at": now
                }
            )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Application withdrawn successfully'
        })
        
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to withdraw application'}), 500

@students_bp.route('/api/application/<int:application_id>/replace-file', methods=['POST'])
@login_required
def replace_application_file(application_id):
    """Replace a deleted document in an application"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
        
    try:
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        
        # Verify application ownership
        application = db.session.execute(
            text("SELECT id FROM scholarship_applications WHERE id = :id AND user_id = :uid AND is_active = 1"),
            {"id": application_id, "uid": current_user.id}
        ).fetchone()
        
        if not application:
            return jsonify({'success': False, 'message': 'Application not found'}), 404
            
        requirement_type = request.form.get('requirement_type')
        file = request.files.get('file')
        
        if not requirement_type or not file:
            return jsonify({'success': False, 'message': 'Missing file or requirement type'}), 400
            
        if file and allowed_file(file.filename):
            # 1. Upload File
            filename = secure_filename(file.filename)
            file_extension = filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4()}_{current_user.id}.{file_extension}"
            
            base_dir = os.path.join(current_app.root_path, CREDENTIALS_FOLDER)
            os.makedirs(base_dir, exist_ok=True)
            file_path = os.path.join(base_dir, unique_filename)
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            
            # 2. Create New Credential
            res = db.session.execute(
                text("""
                    INSERT INTO credentials (user_id, credential_type, file_name, file_path, file_size, status, upload_date, is_active, is_verified)
                    VALUES (:user_id, :ctype, :fname, :fpath, :fsize, 'uploaded', :udate, 1, 0)
                """),
                {
                    "user_id": current_user.id,
                    "ctype": requirement_type, # Using requirement type as credential type logic
                    "fname": filename,
                    "fpath": unique_filename,
                    "fsize": file_size,
                    "udate": datetime.utcnow()
                }
            )
            new_cred_id = res.lastrowid
            
            # 3. Link in Application Files (Upsert logic)
            existing_link = db.session.execute(
                text("SELECT id FROM scholarship_application_files WHERE application_id = :app_id AND requirement_type = :req_type"),
                {"app_id": application_id, "req_type": requirement_type}
            ).fetchone()
            
            if existing_link:
                db.session.execute(
                    text("""
                        UPDATE scholarship_application_files 
                        SET credential_id = :new_id
                        WHERE id = :link_id
                    """),
                    {"new_id": new_cred_id, "link_id": existing_link[0]}
                )
            else:
                db.session.execute(
                    text("""
                        INSERT INTO scholarship_application_files (application_id, credential_id, requirement_type)
                        VALUES (:app_id, :new_id, :req_type)
                    """),
                    {"app_id": application_id, "new_id": new_cred_id, "req_type": requirement_type}
                )
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Document uploaded/replaced successfully'})
            
        return jsonify({'success': False, 'message': 'Invalid file'}), 400
        
    except Exception as e:
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# API endpoints for AJAX requests
@students_bp.route('/api/application/<int:application_id>')
@login_required
def get_application_detail(application_id):
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    try:
        from flask import current_app
        from datetime import datetime
        from credential_matcher import CredentialMatcher
        db = current_app.extensions['sqlalchemy']
        # Verify ownership and fetch
        # Allow viewing completed, archived, and active applications
        app_row = db.session.execute(
            text("""
                SELECT sa.id, sa.status, sa.application_date, s.title, s.code, s.deadline,
                       s.type, s.level, s.eligibility, s.slots, s.contact_name, s.contact_email, s.contact_phone,
                       s.requirements, sa.is_renewal, s.next_last_semester_date, s.semester_date
                FROM scholarship_applications sa
                JOIN scholarships s ON sa.scholarship_id = s.id
                WHERE sa.id=:id AND sa.user_id=:uid
            """), {"id": application_id, "uid": current_user.id}
        ).fetchone()
        if not app_row:
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Get Family Background information
        family_bg = db.session.execute(
            text("""
                SELECT parent_guardian_name, occupation, household_income, dependents
                FROM family_backgrounds
                WHERE application_id = :id
                LIMIT 1
            """), {"id": application_id}
        ).fetchone()
        
        family_background = None
        if family_bg:
            family_background = {
                "parent_guardian_name": family_bg[0] or "",
                "occupation": family_bg[1] or "",
                "household_income": family_bg[2] or "",
                "dependents": family_bg[3] if family_bg[3] is not None else ""
            }
        
        # Get Academic Information
        academic_info = db.session.execute(
            text("""
                SELECT latest_gpa, current_semester, school_year
                FROM academic_information
                WHERE application_id = :id
                LIMIT 1
            """), {"id": application_id}
        ).fetchone()
        
        academic_information = None
        if academic_info:
            academic_information = {
                "latest_gpa": academic_info[0] or "",
                "current_semester": academic_info[1] or "",
                "school_year": academic_info[2] or ""
            }
        
        # Get Personal Information (department, school, address, contact)
        personal_info = db.session.execute(
            text("""
                SELECT department, school_university, address, contact_number
                FROM application_personal_information
                WHERE application_id = :id
                LIMIT 1
            """), {"id": application_id}
        ).fetchone()
        
        personal_information = None
        if personal_info:
            personal_information = {
                "department": personal_info[0] or "",
                "school_university": personal_info[1] or "",
                "address": personal_info[2] or "",
                "contact_number": personal_info[3] or ""
            }
            
        # Get is_renewal flag, next_last_semester_date, and semester_date from app_row
        is_renewal = bool(app_row[14]) if len(app_row) > 14 else False
        next_last_semester_date_val = app_row[15] if len(app_row) > 15 else None
        semester_date_val = app_row[16] if len(app_row) > 16 else None
        
        # Format semester dates
        def format_semester_date(val):
            if not val:
                return None
            try:
                from datetime import datetime as dt
                if isinstance(val, str):
                    return dt.strptime(val, '%Y-%m-%d').strftime('%B %d, %Y')
                elif hasattr(val, 'strftime'):
                    return val.strftime('%B %d, %Y')
            except Exception:
                return None
            return None
        
        semester_date_formatted = format_semester_date(semester_date_val)
        next_last_semester_date_formatted = format_semester_date(next_last_semester_date_val)
        
        # Add next_last_semester_date to academic_information if it's a renewal
        if is_renewal and next_last_semester_date_formatted and academic_information:
            academic_information["next_last_semester_date"] = next_last_semester_date_formatted
        
        # Get current requirements
        req_str = app_row[13] or ''
        current_requirements = [r.strip() for r in req_str.split(',') if r.strip()]
        
        # Existing Linked Documents
        docs = db.session.execute(
            text("""
                SELECT saf.requirement_type, c.file_name, c.file_path, c.credential_type, c.id, c.is_active, c.is_verified
                FROM scholarship_application_files saf
                JOIN credentials c ON c.id = saf.credential_id
                WHERE saf.application_id = :id
            """), {"id": application_id}
        ).fetchall()
        
        # Map existing docs by requirement type
        existing_docs_map = {}
        for d in docs:
            existing_docs_map[d[0]] = {
                "requirement_type": d[0], 
                "file_name": d[1], 
                "file_path": f"static/uploads/credentials/{d[2]}", 
                "credential_type": d[3],
                "id": d[4],
                "is_active": d[5],
                "is_verified": d[6],
                "status": "submitted"
            }

        # Fetch all active loose credentials for user (ordered by date desc to get latest)
        loose_creds = db.session.execute(
            text("""
                SELECT credential_type, file_name, file_path, id, is_verified, status, upload_date
                FROM credentials 
                WHERE user_id = :uid AND is_active = 1
                ORDER BY upload_date DESC
            """), {"uid": current_user.id}
        ).fetchall()
        
        # Convert to list of dicts for Matcher
        loose_creds_list = []
        for c in loose_creds:
            loose_creds_list.append({
                'credential_type': c[0],
                'file_name': c[1],
                'file_path': c[2],
                'id': c[3],
                'is_verified': c[4],
                'status': c[5],
                'upload_date': c[6]
            })
            
        # Find matches
        matched_loose = CredentialMatcher.find_matching_credentials(current_requirements, loose_creds_list)
            
        # Merge: Create final list
        documents = []
        
        # 1. Add all current requirements
        for req in current_requirements:
            if req in existing_docs_map:
                documents.append(existing_docs_map[req])
                del existing_docs_map[req] # Mark as handled
            else:
                # Check for loose match
                matches = matched_loose.get(req, [])
                if matches:
                    # Pick the first one (CredentialMatcher preserves input order? No, it appends. 
                    # But loose_creds_list is sorted by date DESC.
                    # CredentialMatcher logic: iterates requirements, then iterates available_credentials.
                    # So matches list order depends on available_credentials order.
                    # Since loose_creds_list is sorted DESC, matches[0] is the latest.)
                    match = matches[0]
                    documents.append({
                        "requirement_type": req,
                        "file_name": match['file_name'],
                        "file_path": f"static/uploads/credentials/{match['file_path']}",
                        "credential_type": match['credential_type'],
                        "id": match['id'],
                        "is_active": True,
                        "is_verified": match['is_verified'],
                        "status": "matched" # matched from profile
                    })
                else:
                    # Missing requirement
                    documents.append({
                        "requirement_type": req,
                        "file_name": None,
                        "status": "missing",
                        "is_active": True 
                    })
            
        # Documents
        # Get student remarks (remarks linked to student, not application)
        try:
            remarks = db.session.execute(
                text("""
                    SELECT sr.remark_text, sr.created_at, u.first_name, u.last_name, u.organization
                    FROM student_remarks sr
                    JOIN users u ON u.id = sr.provider_id
                    WHERE sr.student_id = :student_id
                    ORDER BY sr.created_at DESC
                """), {"student_id": current_user.id}
            ).fetchall()
        except Exception:
            remarks = []
        # Helper to safely format dates
        def format_dt(val, fmt):
            if not val: return ''
            if isinstance(val, str):
                try:
                    # Try isoformat first
                    dt_obj = datetime.fromisoformat(val.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        # Try common SQL format
                        dt_obj = datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        try:
                            # Try just date
                            dt_obj = datetime.strptime(val, '%Y-%m-%d')
                        except ValueError:
                            return val # Return as-is if parsing fails
                return dt_obj.strftime(fmt)
            return val.strftime(fmt)

        remarks_list = [{"text": r[0], "date": format_dt(r[1], '%B %d, %Y %I:%M %p'), "provider": f"{r[2]} {r[3]}", "organization": r[4] or ''} for r in remarks]
        # Schedules
        try:
            # Prefer new schedule table
            scheds = db.session.execute(
                text("""
                    SELECT schedule_date, schedule_time, location, notes, created_at
                    FROM schedule
                    WHERE application_id = :id
                    ORDER BY created_at DESC
                """), {"id": application_id}
            ).fetchall()
        except Exception:
            # Fallback to legacy table if present
            try:
                scheds = db.session.execute(
                    text("""
                        SELECT schedule_date, schedule_time, location, notes, created_at
                        FROM scholarship_application_schedules
                        WHERE application_id = :id
                        ORDER BY created_at DESC
                    """), {"id": application_id}
                ).fetchall()
            except Exception:
                scheds = []
        
        # Special handling for time which might be a string like "14:00:00"
        def format_time(val):
            if not val: return ''
            if isinstance(val, str):
                try:
                    # Try 24-hour format with seconds
                    t_obj = datetime.strptime(val, '%H:%M:%S').time()
                    return t_obj.strftime('%I:%M %p')
                except ValueError:
                    try:
                        # Try 24-hour format without seconds
                        t_obj = datetime.strptime(val, '%H:%M').time()
                        return t_obj.strftime('%I:%M %p')
                    except ValueError:
                        return val
            return val.strftime('%I:%M %p')

        schedules = [
            {
                "date": format_dt(s[0], '%B %d, %Y'),
                "time": format_time(s[1]),
                "location": s[2],
                "notes": s[3],
                "created_at": format_dt(s[4], '%B %d, %Y %I:%M %p')
            } for s in scheds
        ]
        # Format
        from datetime import datetime as dt
        app_date = app_row[2]
        try:
            app_date_fmt = dt.fromisoformat(app_date.replace('Z','+00:00')).strftime('%B %d, %Y') if app_date else ''
        except Exception:
            app_date_fmt = app_date or ''
        deadline = app_row[5]
        try:
            deadline_fmt = dt.fromisoformat(deadline.replace('Z','+00:00')).strftime('%B %d, %Y') if deadline else 'No deadline'
        except Exception:
            deadline_fmt = deadline or 'No deadline'
        payload = {
            'id': app_row[0],
            'status': (app_row[1] or 'pending').title(),
            'date_applied': app_date_fmt,
            'scholarship_title': app_row[3],
            'scholarship_code': app_row[4],
            'deadline': deadline_fmt,
            'documents': documents,
            'remarks': remarks_list,
            'schedules': schedules,
            # New fields
            'scholarship_type': app_row[6] or 'Not specified',
            'scholarship_level': app_row[7] or 'Not specified',
            'eligibility': app_row[8] or 'No specific eligibility criteria',
            'slots': app_row[9] or 'Unlimited',
            'contact_name': app_row[10] or '',
            'contact_email': app_row[11] or '',
            'contact_phone': app_row[12] or '',
            # Family Background, Academic Information, and Personal Information
            'family_background': family_background,
            'academic_information': academic_information,
            'personal_information': personal_information,
            'is_renewal': is_renewal,
            # Semester dates
            'current_semester_date': semester_date_formatted,
            'next_semester_date': next_last_semester_date_formatted
        }
        return jsonify({'success': True, 'application': payload})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@students_bp.route('/api/announcements')
@login_required
def get_student_announcements():
    """Get student announcements (notifications of type 'info' or 'announcement')"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403

    search_q = request.args.get('search', '').strip()
    
    try:
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        
        query = text("""
            SELECT id, title, message, created_at, type
            FROM notifications
            WHERE user_id = :uid AND is_active = 1 AND type IN ('info', 'announcement')
            """ + (" AND title LIKE :search" if search_q else "") + """
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        params = {"uid": current_user.id}
        if search_q:
            params["search"] = f"%{search_q}%"
            
        rows = db.session.execute(query, params).fetchall()

        def humanize(dt):
            from datetime import datetime
            if not dt: return ''
            if isinstance(dt, str):
                try: dt = datetime.fromisoformat(dt.replace('Z','+00:00'))
                except: return dt
            return dt.strftime('%B %d, %Y')

        announcements = []
        for r in rows:
            announcements.append({
                'id': r[0],
                'title': r[1],
                'message': r[2],
                'date': humanize(r[3]),
                'type': r[4]
            })

        return jsonify({'success': True, 'announcements': announcements})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@students_bp.route('/api/notifications')
@login_required
def get_notifications():
    """Get student notifications"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403

    try:
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        rows = db.session.execute(
            text("""
                SELECT id, user_id, type, title, message, created_at, read_at
                FROM notifications
                WHERE user_id = :uid AND is_active = 1
                ORDER BY created_at DESC
                LIMIT 50
            """),
            {"uid": current_user.id}
        ).fetchall()

        def humanize(dt):
            from datetime import datetime
            if not dt:
                return ''
            now = datetime.utcnow()
            diff = now - (dt if not isinstance(dt, str) else datetime.fromisoformat(dt.replace('Z','+00:00')))
            s = int(diff.total_seconds())
            if s < 60:
                return f"{s}s ago"
            m = s // 60
            if m < 60:
                return f"{m}m ago"
            h = m // 60
            if h < 24:
                return f"{h}h ago"
            d = h // 24
            return f"{d}d ago"

        notifications = []
        for n in rows:
            nid, _, ntype, ntitle, nmsg, ncreated, nread = n
            notifications.append({
                'id': nid,
                'type': ntype,
                'title': ntitle,
                'message': nmsg,
                'time': humanize(ncreated),
                'unread': (nread is None)
            })

        unread_count = sum(1 for n in notifications if n['unread'])
        return jsonify({'success': True, 'items': notifications, 'unread_count': unread_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@students_bp.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    """Mark notifications as read (all or specific ids)"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    try:
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        data = request.get_json() or {}
        ids = data.get('ids')
        from datetime import datetime
        # For simplicity, mark all current user's notifications as read
        db.session.execute(
            text("UPDATE notifications SET read_at = :ts WHERE user_id = :uid AND is_active = 1 AND read_at IS NULL"),
            {"ts": datetime.utcnow(), "uid": current_user.id}
        )
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@students_bp.route('/api/add-award', methods=['POST'])
@login_required
def add_award():
    """Add student award"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    title = request.form.get('title')
    date = request.form.get('date')
    description = request.form.get('description')
    
    if not all([title, date, description]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Here you would implement actual award addition logic
    flash('Award added successfully!', 'success')
    return jsonify({'message': 'Award added successfully'})

@students_bp.route('/upload-photo', methods=['POST'])
@login_required
def upload_photo():
    """Upload student profile photo"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': 'No photo provided'}), 400
    
    file = request.files['photo']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No photo selected'}), 400
    
    if file and allowed_file(file.filename):
        # Generate unique filename
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}_{current_user.id}.{file_extension}"
        
        # Create upload directory if it doesn't exist (absolute path)
        from flask import current_app
        base_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
        os.makedirs(base_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(base_dir, unique_filename)
        file.save(file_path)
        
        # Update user profile picture in database (raw SQL)
        try:
            db = current_app.extensions['sqlalchemy']
            db.session.execute(
                text("UPDATE users SET profile_picture = :pp, updated_at = :ts WHERE id = :id"),
                {"pp": unique_filename, "ts": datetime.utcnow(), "id": current_user.id}
            )
            # Notify photo update
            db.session.execute(
                text("""
                    INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                    VALUES (:user_id, :type, :title, :message, :created_at, 1)
                """),
                {
                    "user_id": current_user.id,
                    "type": 'profile',
                    "title": 'Profile Photo Updated',
                    "message": 'Your profile photo has been updated.',
                    "created_at": datetime.utcnow()
                }
            )
            db.session.commit()
            
            # Return success response with image URL
            profile_picture_url = f"/static/uploads/profile_pictures/{unique_filename}"
            return jsonify({
                'success': True,
                'message': 'Photo uploaded successfully',
                'profile_picture_url': profile_picture_url
            })
            
        except Exception as e:
            if 'db' in locals():
                db.session.rollback()
            # Delete the uploaded file if database update fails
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'success': False, 'message': 'Failed to update profile picture'}), 500
    
    return jsonify({'success': False, 'message': 'Invalid file type'}), 400

@students_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update student profile information including photo"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        birthday = request.form.get('birthday', '')
        year_level = request.form.get('year_level', '').strip()
        course = request.form.get('course', '').strip()
        
        # Validation
        if not all([first_name, last_name, email, birthday, year_level, course]):
            return jsonify({'success': False, 'message': 'Please complete all fields'}), 400
        
        # Email validation
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({'success': False, 'message': 'Invalid email address'}), 400
        
        # Check if email is already taken by another user
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        row = db.session.execute(
            text("SELECT id FROM users WHERE LOWER(email) = :email AND id != :id"),
            {"email": email.lower(), "id": current_user.id}
        ).fetchone()
        
        if row:
            return jsonify({'success': False, 'message': 'Email already taken by another user'}), 400
        
        # Handle photo upload
        new_profile_pic = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '' and allowed_file(file.filename):
                # Generate unique filename
                filename = secure_filename(file.filename)
                file_extension = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4()}_{current_user.id}.{file_extension}"
                
                # Create upload directory if it doesn't exist (absolute path)
                base_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
                os.makedirs(base_dir, exist_ok=True)
                
                # Save file
                file_path = os.path.join(base_dir, unique_filename)
                file.save(file_path)
                
                new_profile_pic = unique_filename
                # Update current_user object for immediate session consistency
                current_user.profile_picture = new_profile_pic
        
        # Update user information in DB
        if new_profile_pic:
             db.session.execute(
                text("""
                    UPDATE users SET first_name=:fn, last_name=:ln, email=:em, birthday=:bd, year_level=:yl, course=:cr, profile_picture=:pp, updated_at=:ts
                    WHERE id = :id
                """),
                {
                    "fn": first_name,
                    "ln": last_name,
                    "em": email,
                    "bd": datetime.strptime(birthday, '%Y-%m-%d').date(),
                    "yl": year_level,
                    "cr": course,
                    "pp": new_profile_pic,
                    "ts": datetime.utcnow(),
                    "id": current_user.id
                }
            )
        else:
             db.session.execute(
                text("""
                    UPDATE users SET first_name=:fn, last_name=:ln, email=:em, birthday=:bd, year_level=:yl, course=:cr, updated_at=:ts
                    WHERE id = :id
                """),
                {
                    "fn": first_name,
                    "ln": last_name,
                    "em": email,
                    "bd": datetime.strptime(birthday, '%Y-%m-%d').date(),
                    "yl": year_level,
                    "cr": course,
                    "ts": datetime.utcnow(),
                    "id": current_user.id
                }
            )

        # Notify profile update
        db.session.execute(
            text("""
                INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                VALUES (:user_id, :type, :title, :message, :created_at, 1)
            """),
            {
                "user_id": current_user.id,
                "type": 'profile',
                "title": 'Profile Updated',
                "message": 'Your profile information has been updated.',
                "created_at": datetime.utcnow()
            }
        )
        
        # Check for matching scholarships if course was updated
        if course:
            matching_scholarships = db.session.execute(
                text("""
                    SELECT id, code, title, program_course
                    FROM scholarships
                    WHERE status IN ('active', 'approved') AND is_active = 1
                    AND program_course IS NOT NULL AND program_course != ''
                """)
            ).fetchall()
            
            student_course_upper = course.strip().upper()
            matching_count = 0
            
            for scholarship in matching_scholarships:
                scholarship_course = (scholarship[3] or '').strip().upper()
                if scholarship_course:
                    # Check if "All Programs" is selected - matches all courses
                    if scholarship_course == 'ALL PROGRAMS':
                        is_match = True
                    else:
                        # Check if courses match (handle comma-separated courses)
                        scholarship_courses = [c.strip().upper() for c in scholarship_course.split(',')]
                        is_match = student_course_upper in scholarship_courses or any(
                            student_course_upper in sc or sc in student_course_upper 
                            for sc in scholarship_courses
                        )
                    
                    if is_match:
                        matching_count += 1
                        # Send notification for each matching scholarship
                        db.session.execute(
                            text("""
                                INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                                VALUES (:user_id, :type, :title, :message, :created_at, 1)
                            """),
                            {
                                "user_id": current_user.id,
                                "type": 'info',
                                "title": 'New Scholarship Match!',
                                "message": f'We found a scholarship that matches your course: {scholarship[2]} ({scholarship[1]}). Check it out in Browse Scholarships!',
                                "created_at": datetime.utcnow()
                            }
                        )
            
            if matching_count > 0:
                # Also send a summary notification
                db.session.execute(
                    text("""
                        INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                        VALUES (:user_id, :type, :title, :message, :created_at, 1)
                    """),
                    {
                        "user_id": current_user.id,
                        "type": 'info',
                        "title": 'Scholarship Matches Found!',
                        "message": f'We found {matching_count} scholarship(s) that match your course. Look for the "Matches Your Course" ribbon on scholarship cards!',
                        "created_at": datetime.utcnow()
                    }
                )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'message': 'Invalid date format'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to update profile'}), 500

@students_bp.route('/reset-password', methods=['POST'])
@login_required
def reset_password():
    """Reset password for logged-in student"""
    if current_user.role != 'student':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
        
        # Validation
        if not current_password or not new_password or not confirm_password:
            return jsonify({'success': False, 'message': 'Please fill in all fields'}), 400
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'New passwords do not match'}), 400
        
        if len(new_password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters long'}), 400
        
        # Get database instance
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        
        # Verify current password
        user_result = db.session.execute(
            text("SELECT id, password_hash FROM users WHERE id = :user_id"),
            {"user_id": current_user.id}
        ).fetchone()
        
        if not user_result:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        user_id, password_hash = user_result
        
        if not check_password_hash(password_hash, current_password):
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 400
        
        # Update password
        new_password_hash = generate_password_hash(new_password)
        db.session.execute(
            text("UPDATE users SET password_hash = :password_hash, updated_at = :updated_at WHERE id = :user_id"),
            {
                "password_hash": new_password_hash,
                "updated_at": datetime.utcnow(),
                "user_id": current_user.id
            }
        )
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Password reset successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to reset password'}), 500

@students_bp.route('/upload-credential', methods=['POST'])
@login_required
def upload_student_credential():
    """Upload student credential"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        credential_type = request.form.get('credential_type', '').strip()
        file = request.files.get('file')
        
        if not credential_type or not file:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            # Generate unique filename
            filename = secure_filename(file.filename)
            file_extension = filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4()}_{current_user.id}.{file_extension}"
            
            # Create upload directory if it doesn't exist (absolute path)
            from flask import current_app
            base_dir = os.path.join(current_app.root_path, CREDENTIALS_FOLDER)
            os.makedirs(base_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(base_dir, unique_filename)
            file.save(file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Save credential to database (raw SQL)
            db = current_app.extensions['sqlalchemy']
            res = db.session.execute(
                text("""
                    INSERT INTO credentials (user_id, credential_type, file_name, file_path, file_size, status, upload_date, is_active)
                    VALUES (:user_id, :ctype, :fname, :fpath, :fsize, 'uploaded', :udate, 1)
                """),
                {
                    "user_id": current_user.id,
                    "ctype": credential_type,
                    "fname": filename,
                    "fpath": unique_filename,
                    "fsize": file_size,
                    "udate": datetime.utcnow()
                }
            )
            cred_id = res.lastrowid if hasattr(res, 'lastrowid') else None

            # Notify credential upload
            db.session.execute(
                text("""
                    INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                    VALUES (:user_id, :type, :title, :message, :created_at, 1)
                """),
                {
                    "user_id": current_user.id,
                    "type": 'credential',
                    "title": 'Credential Uploaded',
                    "message": f'{credential_type} uploaded successfully.',
                    "created_at": datetime.utcnow()
                }
            )
            
            # Auto-link to pending applications if credential matches requirements
            if cred_id:
                try:
                    from credential_matcher import CredentialMatcher
                    
                    # Get all pending applications for this student
                    pending_apps = db.session.execute(
                        text("""
                            SELECT sa.id, sa.scholarship_id, s.requirements
                            FROM scholarship_applications sa
                            JOIN scholarships s ON sa.scholarship_id = s.id
                            WHERE sa.user_id = :user_id 
                            AND sa.status = 'pending' 
                            AND sa.is_active = 1
                        """),
                        {"user_id": current_user.id}
                    ).fetchall()
                    
                    # Get the uploaded credential info
                    cred_info = {
                        'credential_type': credential_type,
                        'file_name': filename,
                        'file_path': unique_filename,
                        'id': cred_id,
                        'is_verified': False,
                        'status': 'uploaded',
                        'upload_date': datetime.utcnow()
                    }
                    
                    for app in pending_apps:
                        app_id = app[0]
                        scholarship_id = app[1]
                        req_str = app[2] or ''
                        requirements = [r.strip() for r in req_str.split(',') if r.strip()]
                        
                        if not requirements:
                            continue
                        
                        # Check if credential matches any requirement
                        matched_reqs = CredentialMatcher.find_matching_credentials(requirements, [cred_info])
                        
                        for req_type, matches in matched_reqs.items():
                            if matches:
                                # Check if requirement is already linked to this application
                                existing_link = db.session.execute(
                                    text("""
                                        SELECT id FROM scholarship_application_files
                                        WHERE application_id = :app_id AND requirement_type = :req_type
                                    """),
                                    {"app_id": app_id, "req_type": req_type}
                                ).fetchone()
                                
                                if not existing_link:
                                    # Auto-link the credential to the application
                                    db.session.execute(
                                        text("""
                                            INSERT INTO scholarship_application_files 
                                            (application_id, credential_id, requirement_type)
                                            VALUES (:app_id, :cred_id, :req_type)
                                        """),
                                        {
                                            "app_id": app_id,
                                            "cred_id": cred_id,
                                            "req_type": req_type
                                        }
                                    )
                except Exception as e:
                    # Don't fail upload if auto-linking fails
                    print(f"Warning: Could not auto-link credential to applications: {e}")
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Credential uploaded successfully',
                'credential_id': cred_id
            })
            
        else:
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
            
    except Exception as e:
        if 'db' in locals():
            db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error uploading credential: {str(e)}")
        print(f"Traceback: {error_details}")
        return jsonify({'success': False, 'message': f'Failed to upload credential: {str(e)}'}), 500

@students_bp.route('/view-credential/<int:credential_id>')
@login_required
def view_credential(credential_id):
    """View credential file"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
    from flask import current_app
    db = current_app.extensions['sqlalchemy']
    row = db.session.execute(
        text("SELECT file_path FROM credentials WHERE id = :id AND user_id = :uid AND is_active = 1"),
        {"id": credential_id, "uid": current_user.id}
    ).fetchone()
    
    if not row:
        flash('Credential not found.', 'error')
        return redirect(url_for('students.credentials'))
    
    file_path = os.path.join(current_app.root_path, CREDENTIALS_FOLDER, row[0])
    
    if not os.path.exists(file_path):
        flash('File not found.', 'error')
        return redirect(url_for('students.credentials'))
    
    # Determine content type based on file extension
    file_extension = row[0].rsplit('.', 1)[1].lower()
    content_type_map = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    
    content_type = content_type_map.get(file_extension, 'application/octet-stream')
    
    from flask import send_file
    return send_file(file_path, as_attachment=False, mimetype=content_type)

@students_bp.route('/delete-credential/<int:credential_id>', methods=['DELETE'])
@login_required
def delete_credential(credential_id):
    """Delete credential (soft delete + remove file)"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    try:
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        row = db.session.execute(
            text("SELECT credential_type, file_path FROM credentials WHERE id = :id AND user_id = :uid AND is_active = 1"),
            {"id": credential_id, "uid": current_user.id}
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Credential not found'}), 404
        
        credential_type = row[0]
        file_path_in_db = row[1]

        # Check if this credential is linked to any applications
        # If it's verified and linked, we need to notify providers that verification is needed again
        linked_apps = db.session.execute(
            text("""
                SELECT saf.application_id, saf.requirement_type, c.is_verified, s.provider_id, s.title
                FROM scholarship_application_files saf
                JOIN credentials c ON saf.credential_id = c.id
                JOIN scholarship_applications sa ON saf.application_id = sa.id
                JOIN scholarships s ON sa.scholarship_id = s.id
                WHERE saf.credential_id = :cred_id
                AND sa.status = 'pending'
                AND sa.is_active = 1
            """),
            {"cred_id": credential_id}
        ).fetchall()
        
        # Delete file
        file_path_full = os.path.join(current_app.root_path, CREDENTIALS_FOLDER, file_path_in_db)
        if os.path.exists(file_path_full):
            os.remove(file_path_full)
        
        # Soft delete credential
        db.session.execute(
            text("UPDATE credentials SET is_active = 0 WHERE id = :id"),
            {"id": credential_id}
        )
        
        # Remove links to this credential from applications (so requirement shows as missing)
        # This allows the student to upload a new credential which will be auto-linked
        db.session.execute(
            text("DELETE FROM scholarship_application_files WHERE credential_id = :cred_id"),
            {"cred_id": credential_id}
        )
        
        # Notify providers if a verified document was deleted
        for app in linked_apps:
            app_id = app[0]
            req_type = app[1]
            was_verified = app[2]
            provider_id = app[3]
            scholarship_title = app[4]
            
            if was_verified:
                # Notify provider that verification is needed again
                try:
                    from credential_matcher import CredentialMatcher
                    REQUIREMENT_MAPPINGS = CredentialMatcher.REQUIREMENT_MAPPINGS
                    req_label = None
                    for code, labels in REQUIREMENT_MAPPINGS.items():
                        if code == req_type:
                            req_label = labels[0] if labels else req_type
                            break
                    if not req_label:
                        req_label = req_type
                    
                    db.session.execute(
                        text("""
                            INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                            VALUES (:user_id, :type, :title, :message, :created_at, 1)
                        """),
                        {
                            "user_id": provider_id,
                            "type": 'document',
                            "title": f'Document Replaced: {scholarship_title}',
                            "message": f'A student has replaced a verified document ({req_label}). Please verify the new document.',
                            "created_at": datetime.utcnow()
                        }
                    )
                except Exception as e:
                    print(f"Warning: Could not notify provider: {e}")
        
        # Create notification for student
        db.session.execute(
            text("""
                INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                VALUES (:user_id, :type, :title, :message, :created_at, 1)
            """),
            {
                "user_id": current_user.id,
                "type": 'credential',
                "title": 'Credential Deleted',
                "message": f'Credential "{credential_type}" has been deleted.',
                "created_at": datetime.utcnow()
            }
        )
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Credential deleted successfully'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to delete credential'}), 500

@students_bp.route('/api/renewal-failed', methods=['POST'])
@login_required
def record_renewal_failure():
    """Record that student failed to confirm renewal"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        data = request.get_json()
        scholarship_id = data.get('scholarship_id')
        
        if not scholarship_id:
            return jsonify({'success': False, 'message': 'Scholarship ID required'}), 400
        
        # Find the approved application for this scholarship
        approved_app = db.session.execute(
            text("""
                SELECT id FROM scholarship_applications
                WHERE user_id = :user_id 
                AND scholarship_id = :scholarship_id
                AND status = 'approved'
                AND is_active = 1
                ORDER BY application_date DESC
                LIMIT 1
            """),
            {"user_id": current_user.id, "scholarship_id": scholarship_id}
        ).fetchone()
        
        if approved_app:
            # Mark renewal_failed flag
            db.session.execute(
                text("""
                    UPDATE scholarship_applications
                    SET renewal_failed = 1
                    WHERE id = :app_id
                """),
                {"app_id": approved_app[0]}
            )
            db.session.commit()
            return jsonify({'success': True, 'message': 'Renewal failure recorded'})
        else:
            return jsonify({'success': False, 'message': 'Approved application not found'}), 404
            
    except Exception as e:
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
