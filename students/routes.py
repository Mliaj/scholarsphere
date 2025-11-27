"""
Student dashboard routes for Scholarsphere
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from sqlalchemy import text

students_bp = Blueprint('students', __name__)

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads/profile_pictures'
CREDENTIALS_FOLDER = 'static/uploads/credentials'
AWARDS_FOLDER = 'static/uploads/awards'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@students_bp.route('/dashboard')
@login_required
def dashboard():
    """Student dashboard"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
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
    
    # Deadlines: nearest counts for current and next month
    from datetime import date
    today = date.today()
    first_of_month = today.replace(day=1)
    if first_of_month.month == 12:
        first_next_month = first_of_month.replace(year=first_of_month.year + 1, month=1)
    else:
        first_next_month = first_of_month.replace(month=first_of_month.month + 1)
    if first_next_month.month == 12:
        first_after_next = first_next_month.replace(year=first_next_month.year + 1, month=1)
    else:
        first_after_next = first_next_month.replace(month=first_next_month.month + 1)

    # Count scholarships with deadlines this month and next month
    this_month_deadlines = db.session.execute(
        text("""
            SELECT COUNT(*) FROM scholarships
            WHERE status IN ('active','approved') AND is_active = 1
              AND deadline IS NOT NULL
              AND DATE(deadline) >= :start AND DATE(deadline) < :end
        """),
        {"start": first_of_month.isoformat(), "end": first_next_month.isoformat()}
    ).scalar() or 0

    next_month_deadlines = db.session.execute(
        text("""
            SELECT COUNT(*) FROM scholarships
            WHERE status IN ('active','approved') AND is_active = 1
              AND deadline IS NOT NULL
              AND DATE(deadline) >= :start AND DATE(deadline) < :end
        """),
        {"start": first_next_month.isoformat(), "end": first_after_next.isoformat()}
    ).scalar() or 0

    dashboard_data = {
        'user': current_user,
        'credentials': {
            'total': total_credentials
        },
        'applications': {
            'total': total_applications,
            'approved': approved_applications
        },
        'deadlines': {
            'this_month': this_month_deadlines,
            'next_month': next_month_deadlines
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
    
    return render_template('students/profile.html', user=current_user)

@students_bp.route('/credentials')
@login_required
def credentials():
    """Student credentials page"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
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
    
    # Get approved scholarship for the student
    approved_scholarship = db.session.execute(
        text("""
            SELECT s.title, s.code
            FROM scholarship_applications sa
            JOIN scholarships s ON sa.scholarship_id = s.id
            WHERE sa.user_id = :user_id AND sa.status = 'approved' AND sa.is_active = 1
            ORDER BY sa.reviewed_at DESC
            LIMIT 1
        """),
        {"user_id": current_user.id}
    ).fetchone()
    
    scholarship_name = None
    if approved_scholarship:
        scholarship_name = approved_scholarship[0]  # title
    
    return render_template('students/credentials.html', credentials=credentials_list, user=current_user, scholarship_name=scholarship_name)

@students_bp.route('/awards')
@login_required
def awards():
    """Student awards page"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
    # Get actual awards from database using raw SQL
    from flask import current_app
    db = current_app.extensions['sqlalchemy']
    
    user_awards = db.session.execute(
        text("SELECT * FROM awards WHERE user_id = :user_id AND is_active = 1 ORDER BY award_date DESC, upload_date DESC"),
        {"user_id": current_user.id}
    ).fetchall()
    
    # Convert to list of dictionaries for template compatibility
    awards_list = []
    for award in user_awards:
        # Ensure upload_date is a proper datetime object
        upload_date = award[9]
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
        
        awards_list.append({
            'id': award[0],
            'user_id': award[1],
            'award_type': award[2],
            'award_title': award[3],
            'file_name': award[4],
            'file_path': award[5],
            'file_size': award[6],
            'academic_year': award[7],
            'award_date': award[8],
            'upload_date': upload_date,
            'is_active': award[10]
        })
    
    return render_template('students/awards.html', awards=awards_list, user=current_user)

@students_bp.route('/applications')
@login_required
def applications():
    """Student applications page"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
    # Get actual applications from database using raw SQL
    from flask import current_app
    from datetime import datetime
    db = current_app.extensions['sqlalchemy']
    
    user_applications = db.session.execute(
        text("""
            SELECT sa.id, sa.user_id, sa.scholarship_id, sa.status, sa.application_date, 
                   s.title, s.deadline
            FROM scholarship_applications sa
            JOIN scholarships s ON sa.scholarship_id = s.id
            WHERE sa.user_id = :user_id AND sa.is_active = 1
            ORDER BY sa.application_date DESC
        """),
        {"user_id": current_user.id}
    ).fetchall()
    
    applications_data = []
    for app in user_applications:
        # Parse dates robustly
        app_date_str = str(app[4]) if app[4] else None
        deadline_str = str(app[6]) if app[6] else None

        app_date = None
        if app_date_str:
            try:
                app_date = datetime.fromisoformat(app_date_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    app_date = datetime.strptime(app_date_str, '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    app_date = datetime.now() # Fallback
        else:
            app_date = datetime.now()

        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    # For Date objects that get stringified
                    deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
                except (ValueError, TypeError):
                    try:
                        # For datetime strings without T
                        deadline = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        deadline = None
        
        applications_data.append({
            'id': f"APP-{app[0]:03d}",
            'scholarship': app[5],
            'status': app[3].title(),
            'date_applied': app_date.strftime('%B %d, %Y'),
            'deadline': deadline.strftime('%B %d, %Y') if deadline else 'No deadline',
            'scholarship_id': app[2],
            'application_id': app[0]
        })
    
    return render_template('students/applications.html', applications=applications_data, user=current_user)

@students_bp.route('/scholarships')
@login_required
def scholarships():
    """Available scholarships page"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
    # Get actual scholarships from database using raw SQL
    from flask import current_app
    from datetime import datetime
    db = current_app.extensions['sqlalchemy']

    # Archive scholarships with past deadlines
    db.session.execute(
        text(
            """
            UPDATE scholarships
            SET is_active = 0, status = 'closed'
            WHERE deadline < :today AND is_active = 1
            """
        ),
        {"today": datetime.utcnow().date()}
    )
    db.session.commit()
    
    available_scholarships = db.session.execute(
        text(
            """
            SELECT s.id, s.code, s.title, s.description, s.amount, s.deadline, s.requirements, u.organization
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
        deadline = None
        if scholarship[5]:
            try:
                deadline = datetime.fromisoformat(scholarship[5].replace('Z','+00:00'))
            except:
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

        scholarships_data.append({
            'id': scholarship[1] or f"SCH-{scholarship_id:03d}",
            'title': scholarship[2],
            'description': scholarship[3] or 'No description available',
            'amount': scholarship[4] or 'Amount not specified',
            'deadline': deadline.strftime('%B %d, %Y') if deadline else 'No deadline',
            'requirements': ', '.join(requirements_display) if requirements_display else 'No specific requirements',
            'provider': scholarship[7] or 'University of Cebu',
            'scholarship_id': scholarship_id,
            'has_applied': has_applied,
            'application_status': existing_application_status,
            'can_apply_again': can_apply_again
        })
    
    return render_template('students/scholarships.html', scholarships=scholarships_data, user=current_user)

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
        
        # Get form data - handle both JSON and FormData
        if request.is_json:
            form_data = request.get_json()
            selected_credentials = form_data.get('selected_credentials', {})
        else:
            # Handle form data
            form_data = request.form.to_dict()
            # Parse selected_credentials from JSON string if it exists
            credentials_str = request.form.get('selected_credentials', '{}')
            try:
                selected_credentials = json.loads(credentials_str)
            except (json.JSONDecodeError, ValueError):
                selected_credentials = {}
        
        # Check if scholarship exists and is active
        scholarship = db.session.execute(
            text("SELECT id, applications_count, pending_count, requirements FROM scholarships WHERE id = :id AND status IN ('active','approved') AND is_active = 1"),
            {"id": scholarship_id}
        ).fetchone()
        
        if not scholarship:
            return jsonify({'success': False, 'message': 'Scholarship not found or not available'}), 404
        
        # Block if student already has an approved active scholarship application
        has_approved = db.session.execute(
            text(
                """
                SELECT id FROM scholarship_applications
                WHERE user_id = :user_id AND status = 'approved' AND is_active = 1
                LIMIT 1
                """
            ),
            {"user_id": current_user.id}
        ).fetchone()
        if has_approved:
            return jsonify({'success': False, 'message': 'You already have an approved scholarship. Please contact your provider to revoke (soft delete) it before applying again.'}), 400
        
        # Check existing application for this scholarship (any status)
        existing_application = db.session.execute(
            text(
                """\
                SELECT id, status FROM scholarship_applications 
                WHERE user_id = :user_id AND scholarship_id = :scholarship_id AND status IN ('pending', 'approved')
                ORDER BY id DESC LIMIT 1
                """
            ),
            {"user_id": current_user.id, "scholarship_id": scholarship_id}
        ).fetchone()

        if existing_application:
            return jsonify({'success': False, 'message': 'You have already applied to this scholarship'}), 400

        current_time = datetime.utcnow().isoformat()
        
        # No existing row for this user/scholarship: create a brand new application
        result = db.session.execute(
            text("""\
                INSERT INTO scholarship_applications (user_id, scholarship_id, status, application_date, is_active)
                VALUES (:user_id, :scholarship_id, :status, :application_date, :is_active)
            """),
            {
                "user_id": current_user.id,
                "scholarship_id": scholarship_id,
                "status": 'pending',
                "application_date": current_time,
                "is_active": 1
            }
        )

        application_id = result.lastrowid
        
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
            db.session.execute(
                text("""
                    INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                    VALUES (:user_id, :type, :title, :message, :created_at, 1)
                """),
                {
                    "user_id": current_user.id,
                    "type": 'application',
                    "title": 'Application Submitted',
                    "message": 'Your scholarship application has been submitted successfully.',
                    "created_at": datetime.utcnow()
                }
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        
        return jsonify({
            'success': True,
            'message': 'Application submitted successfully with credentials'
        })
        
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
        if current_status != 'pending':
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

# API endpoints for AJAX requests
@students_bp.route('/api/application/<int:application_id>')
@login_required
def get_application_detail(application_id):
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    try:
        from flask import current_app
        from datetime import datetime
        db = current_app.extensions['sqlalchemy']
        # Verify ownership and fetch
        app_row = db.session.execute(
            text("""
                SELECT sa.id, sa.status, sa.application_date, s.title, s.code, s.deadline
                FROM scholarship_applications sa
                JOIN scholarships s ON sa.scholarship_id = s.id
                WHERE sa.id=:id AND sa.user_id=:uid AND sa.is_active=1
            """), {"id": application_id, "uid": current_user.id}
        ).fetchone()
        if not app_row:
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        # Documents
        docs = db.session.execute(
            text("""
                SELECT saf.requirement_type, c.file_name, c.file_path, c.credential_type
                FROM scholarship_application_files saf
                JOIN credentials c ON c.id = saf.credential_id
                WHERE saf.application_id = :id
                ORDER BY saf.requirement_type
            """), {"id": application_id}
        ).fetchall()
        documents = [{"requirement_type": d[0], "file_name": d[1], "file_path": f"static/uploads/credentials/{d[2]}", "credential_type": d[3]} for d in docs]
        # Remarks
        try:
            remarks = db.session.execute(
                text("""
                    SELECT ar.remark_text, ar.status, ar.created_at, u.first_name, u.last_name
                    FROM application_remarks ar
                    JOIN scholarship_applications sa ON sa.id = ar.application_id
                    JOIN scholarships s ON sa.scholarship_id = s.id
                    JOIN users u ON u.id = ar.provider_id
                    WHERE ar.application_id = :id
                    ORDER BY ar.created_at DESC
                """), {"id": application_id}
            ).fetchall()
        except Exception:
            remarks = []
        remarks_list = [{"text": r[0], "status": (r[1] or '').title(), "date": (r[2] or ''), "provider": f"{r[3]} {r[4]}"} for r in remarks]
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
        schedules = [{"date": s[0], "time": s[1], "location": s[2], "notes": s[3], "created_at": s[4]} for s in scheds]
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
            'schedules': schedules
        }
        return jsonify({'success': True, 'application': payload})
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
        
        # Handle photo upload if provided
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '' and allowed_file(file.filename):
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
                
                # Update profile picture
                current_user.profile_picture = unique_filename
        
        # Update user information
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

@students_bp.route('/upload-award', methods=['POST'])
@login_required
def upload_award():
    """Upload student award"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        award_type = request.form.get('award_type', '').strip()
        award_title = request.form.get('award_title', '').strip()
        academic_year = request.form.get('academic_year', '').strip()
        award_date = request.form.get('award_date', '').strip()
        file = request.files.get('file')
        
        if not all([award_type, award_title, academic_year, award_date]) or not file:
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
            base_dir = os.path.join(current_app.root_path, AWARDS_FOLDER)
            os.makedirs(base_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(base_dir, unique_filename)
            file.save(file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Save award to database (raw SQL)
            db = current_app.extensions['sqlalchemy']
            db.session.execute(
                text("""
                    INSERT INTO awards (user_id, award_type, award_title, file_name, file_path, file_size, academic_year, award_date, upload_date, is_active)
                    VALUES (:user_id, :atype, :atitle, :fname, :fpath, :fsize, :ayear, :adate, :udate, 1)
                """),
                {
                    "user_id": current_user.id,
                    "atype": award_type,
                    "atitle": award_title,
                    "fname": filename,
                    "fpath": unique_filename,
                    "fsize": file_size,
                    "ayear": academic_year,
                    "adate": datetime.strptime(award_date, '%Y-%m-%d').date(),
                    "udate": datetime.utcnow()
                }
            )

            # Notify award upload
            db.session.execute(
                text("""
                    INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                    VALUES (:user_id, :type, :title, :message, :created_at, 1)
                """),
                {
                    "user_id": current_user.id,
                    "type": 'award',
                    "title": 'Award Uploaded',
                    "message": f'Award "{award_title}" has been uploaded.',
                    "created_at": datetime.utcnow()
                }
            )
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Award uploaded successfully'
            })
            
        else:
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
            
    except ValueError as e:
        return jsonify({'success': False, 'message': 'Invalid date format'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to upload award'}), 500

@students_bp.route('/view-award/<int:award_id>')
@login_required
def view_award(award_id):
    """View award file"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
    from flask import current_app
    db = current_app.extensions['sqlalchemy']
    row = db.session.execute(
        text("SELECT file_path FROM awards WHERE id = :id AND user_id = :uid AND is_active = 1"),
        {"id": award_id, "uid": current_user.id}
    ).fetchone()
    
    if not row:
        flash('Award not found.', 'error')
        return redirect(url_for('students.awards'))
    
    file_path = os.path.join(current_app.root_path, AWARDS_FOLDER, row[0])
    
    if not os.path.exists(file_path):
        flash('File not found.', 'error')
        return redirect(url_for('students.awards'))
    
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
            text("SELECT file_path FROM credentials WHERE id = :id AND user_id = :uid AND is_active = 1"),
            {"id": credential_id, "uid": current_user.id}
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Credential not found'}), 404
        # Delete file
        file_path = os.path.join(current_app.root_path, CREDENTIALS_FOLDER, row[0])
        if os.path.exists(file_path):
            os.remove(file_path)
        # Soft delete
        db.session.execute(
            text("UPDATE credentials SET is_active = 0 WHERE id = :id"),
            {"id": credential_id}
        )
        db.session.commit()
        return jsonify({'success': True, 'message': 'Credential deleted successfully'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to delete credential'}), 500

@students_bp.route('/delete-award/<int:award_id>', methods=['DELETE'])
@login_required
def delete_award(award_id):
    """Delete award"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        row = db.session.execute(
            text("SELECT file_path FROM awards WHERE id=:id AND user_id=:uid AND is_active=1"),
            {"id": award_id, "uid": current_user.id}
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Award not found'}), 404
        
        # Delete file from filesystem
        file_path = os.path.join(current_app.root_path, AWARDS_FOLDER, row[0])
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Mark as inactive in database (soft delete)
        db.session.execute(
            text("UPDATE awards SET is_active = 0 WHERE id = :id"),
            {"id": award_id}
        )
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Award deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to delete award'}), 500
