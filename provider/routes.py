from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from app import db, User, Scholarship, ScholarshipApplication, Credential, Schedule, Notification, ScholarshipApplicationFile, Announcement, StudentRemark, ApplicationRemark
from email_utils import send_email
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime # Import datetime here
from sqlalchemy import or_, text
from credential_matcher import CredentialMatcher

provider_bp = Blueprint('provider', __name__)

def is_provider_admin():
    """Check if current user is a provider admin"""
    return current_user.is_authenticated and current_user.role == 'provider_admin'

def is_provider_staff():
    """Check if current user is a provider staff"""
    return current_user.is_authenticated and current_user.role == 'provider_staff'

def is_provider_role():
    """Check if current user is any provider role (admin or staff)"""
    return current_user.is_authenticated and current_user.role in ('provider_admin', 'provider_staff')

def require_provider_admin():
    """Require provider admin access, abort with 403 if not"""
    if not is_provider_admin():
        flash('Access denied. Provider admin access required.', 'error')
        abort(403)

def require_provider_role():
    """Require any provider role access, abort with 403 if not"""
    if not is_provider_role():
        flash('Access denied. Provider access required.', 'error')
        abort(403)

def get_provider_id():
    """Get the provider ID - for staff, return their manager's ID; for admin, return their own ID"""
    if current_user.role == 'provider_staff' and current_user.managed_by:
        return current_user.managed_by
    return current_user.id

def get_scholarships_query(provider_id):
    """Get scholarships query filtered by provider_id and staff's scholarship_type if applicable"""
    query = Scholarship.query.filter_by(provider_id=provider_id)
    # Filter by type if user is provider_staff with assigned type
    if current_user.role == 'provider_staff' and current_user.scholarship_type:
        query = query.filter_by(type=current_user.scholarship_type)
    return query

def notify_matching_students(scholarship):
    """Notify students whose course matches the scholarship's program_course"""
    if not scholarship.program_course or not scholarship.program_course.strip():
        return
    
    scholarship_course_upper = scholarship.program_course.strip().upper()
    
    # Find all students with matching courses
    students = db.session.execute(
        text("""
            SELECT id, first_name, last_name, course, email
            FROM users
            WHERE role = 'student' AND course IS NOT NULL AND course != ''
        """)
    ).fetchall()
    
    matching_count = 0
    for student in students:
        student_course = (student[3] or '').strip().upper()
        if student_course:
            # Check if "All Programs" is selected - matches all courses
            if scholarship_course_upper == 'ALL PROGRAMS':
                is_match = True
            else:
                # Check if courses match
                scholarship_courses = [c.strip().upper() for c in scholarship_course_upper.split(',')]
                is_match = student_course in scholarship_courses or any(
                    student_course in sc or sc in student_course 
                    for sc in scholarship_courses
                )
            
            if is_match:
                matching_count += 1
                # Send notification
                db.session.execute(
                    text("""
                        INSERT INTO notifications (user_id, type, title, message, created_at, is_active)
                        VALUES (:user_id, :type, :title, :message, :created_at, 1)
                    """),
                    {
                        "user_id": student[0],
                        "type": 'info',
                        "title": 'New Scholarship Match!',
                        "message": f'A new scholarship "{scholarship.title}" ({scholarship.code}) matches your course! Check it out in Browse Scholarships.',
                        "created_at": datetime.utcnow()
                    }
                )
    
    return matching_count

@provider_bp.route('/dashboard')
@login_required
def dashboard():
    """Provider dashboard"""
    require_provider_role()
    
    # Check semester expirations for all students (no cron job needed - checks on page load)
    try:
        from semester_expiration_utils import check_all_students_semester_expirations
        check_all_students_semester_expirations()
    except Exception:
        # Don't fail page load if check fails
        pass
    
    provider_id = get_provider_id()
    
    # Get base query with type filtering for staff
    base_query = get_scholarships_query(provider_id)
    
    # Calculate dashboard stats
    active_scholarships = base_query.filter(
        Scholarship.status.in_(['active', 'approved'])
    ).count()
    draft_scholarships = base_query.filter_by(status='draft').count()
    
    scholarships = base_query.all()
    scholarship_ids = [s.id for s in scholarships]
    
    total_applications = ScholarshipApplication.query.filter(
        ScholarshipApplication.scholarship_id.in_(scholarship_ids)
    ).count() if scholarship_ids else 0
    
    pending_reviews = ScholarshipApplication.query.filter(
        ScholarshipApplication.scholarship_id.in_(scholarship_ids),
        ScholarshipApplication.status == 'pending'
    ).count() if scholarship_ids else 0
    
    # Get the actual provider user (admin or admin of staff)
    if current_user.role == 'provider_staff' and current_user.managed_by:
        provider_user = User.query.get(current_user.managed_by)
    else:
        provider_user = current_user
    
    # Format provider ID
    provider_id_formatted = f"PRV-{str(provider_user.id).zfill(3)}"
    
    # Prepare data dictionary
    data = {
        'stats': {
            'active_scholarships': active_scholarships,
            'draft_scholarships': draft_scholarships,
            'total_applications': total_applications,
            'new_applications': 0, # Mock for now
            'pending_reviews': pending_reviews,
            'today_reviews': 0 # Mock for now
        },
        'provider_id': provider_id_formatted,
        'organization': provider_user.organization or 'Not set'
    }
    
    return render_template('provider/dashboard.html', user=current_user, data=data)

@provider_bp.route('/scholarships')
@login_required
def scholarships():
    """Provider scholarships page - Admin only"""
    require_provider_admin()
    
    # Check semester expirations for all students (no cron job needed - checks on page load)
    try:
        from semester_expiration_utils import check_all_students_semester_expirations
        check_all_students_semester_expirations()
    except Exception:
        # Don't fail page load if check fails
        pass

    all_scholarships = Scholarship.query.filter_by(provider_id=current_user.id).all()
    
    # Calculate application counts for each scholarship (only active applications)
    for s in all_scholarships:
        # Count only active applications for this scholarship
        # Use actual count from database for accuracy (only active applications)
        active_app_count = ScholarshipApplication.query.filter_by(
            scholarship_id=s.id,
            is_active=True
        ).count()
        # Set application count attribute for template display
        s.display_app_count = active_app_count
        # Also update the stored applications_count for consistency (optional)
        # s.applications_count = active_app_count
    
    active_scholarships = [s for s in all_scholarships if s.status != 'archived']
    archived_scholarships = [s for s in all_scholarships if s.status == 'archived']

    today_date = datetime.now().strftime('%Y-%m-%d') # Get current date

    return render_template('provider/scholarships.html', 
                           user=current_user, 
                           scholarships=active_scholarships, 
                           archived_scholarships=archived_scholarships,
                           today_date=today_date) # Pass today_date to template

@provider_bp.route('/applications')
@login_required
def applications():
    """Provider applications page"""
    require_provider_role()
    
    # Check semester expirations for all students (no cron job needed - checks on page load)
    try:
        from semester_expiration_utils import check_all_students_semester_expirations
        check_all_students_semester_expirations()
    except Exception:
        # Don't fail page load if check fails
        pass
    
    provider_id = get_provider_id()
    scholarships = get_scholarships_query(provider_id).all()
    
    total_applications = 0
    # Pre-process scholarships to attach application count and formatted applications if needed by template
    for s in scholarships:
        # Ensure we are counting correctly. 
        # The template uses s.application_count (which might be a property or we set it here)
        # and s.applications (relationship).
        s.application_count = s.applications.count()
        total_applications += s.application_count
        
        # Create a list to store processed applications
        apps_list = list(s.applications)
        
        # enhance application objects for the template
        for app in apps_list:
            student = User.query.get(app.user_id)
            app.student_name = student.get_full_name() if student else "Unknown"
            app.student_email = student.email if student else ""
            app.student_id = student.student_id if student else ""
            app.application_id = app.id
            app.date_applied = app.application_date.strftime('%Y-%m-%d')
            app.is_renewal = app.is_renewal if hasattr(app, 'is_renewal') else False
            # Count files linked to this application
            app.file_count = ScholarshipApplicationFile.query.filter_by(application_id=app.id).count()
            
        s.display_applications = apps_list

    return render_template('provider/applications.html', 
                           user=current_user, 
                           scholarships=scholarships, 
                           total_applications=total_applications)

@provider_bp.route('/schedules')
@login_required
def schedules():
    """Provider schedules page"""
    require_provider_role()
    
    # Check semester expirations for all students (no cron job needed - checks on page load)
    try:
        from semester_expiration_utils import check_all_students_semester_expirations
        check_all_students_semester_expirations()
    except Exception:
        # Don't fail page load if check fails
        pass
    
    provider_id = get_provider_id()
    # Get applications to list for scheduling
    scholarships = get_scholarships_query(provider_id).all()
    scholarship_ids = [s.id for s in scholarships]
    
    raw_applications = ScholarshipApplication.query.filter(
        ScholarshipApplication.scholarship_id.in_(scholarship_ids)
    ).all()
    
    applications_data = []
    for app in raw_applications:
        student = User.query.get(app.user_id)
        scholarship = Scholarship.query.get(app.scholarship_id)
        
        applications_data.append({
            'application_id': f"APP-{str(app.id).zfill(3)}",
            'application_id_raw': app.id,
            'student_name': student.get_full_name() if student else "Unknown",
            'student_email': student.email if student else "",
            'scholarship_code': scholarship.code if scholarship else "",
            'scholarship_title': scholarship.title if scholarship else "",
            'status': app.status,
            'date_applied': app.application_date.strftime('%Y-%m-%d'),
            'is_renewal': app.is_renewal if hasattr(app, 'is_renewal') else False
        })
    
    # Also fetch existing schedules if we want to show them (template might need update or we pass both)
    # The current template iterates 'applications', so we pass that.
    
    today_date = datetime.now().strftime('%Y-%m-%d')

    return render_template('provider/schedules.html', 
                           user=current_user, 
                           applications=applications_data,
                           today_date=today_date)

@provider_bp.route('/documents')
@login_required
def documents():
    """Provider documents page"""
    require_provider_role()
    
    provider_id = get_provider_id()
    scholarships = get_scholarships_query(provider_id).all()
    scholarship_ids = [s.id for s in scholarships]
    
    # Get all applications for these scholarships
    applications = ScholarshipApplication.query.filter(
        ScholarshipApplication.scholarship_id.in_(scholarship_ids)
    ).all()
    
    documents_data = []
    
    for app in applications:
        student = User.query.get(app.user_id)
        scholarship = Scholarship.query.get(app.scholarship_id)
        
        # Get credentials for this student
        credentials = Credential.query.filter_by(user_id=app.user_id, is_active=True).all()
        
        if not credentials:
            continue # Skip if no documents
            
        formatted_docs = []
        for cred in credentials:
            formatted_docs.append({
                'requirement_type': cred.credential_type,
                'file_name': cred.file_name,
                'credential_type': cred.credential_type, # Template uses both
                'file_path': cred.file_path # Use stored unique filename
            })
            
        documents_data.append({
            'student_name': student.get_full_name() if student else "Unknown",
            'student_id': student.student_id if student else "",
            'application_id': f"APP-{str(app.id).zfill(3)}",
            'scholarship_code': scholarship.code if scholarship else "",
            'scholarship_title': scholarship.title if scholarship else "",
            'status': app.status,
            'completion_status': 'Complete' if len(credentials) >= 1 else 'Incomplete', # Simple logic
            'document_count': len(credentials),
            'documents': formatted_docs
        })
        
    return render_template('provider/documents.html', 
                           user=current_user, 
                           documents=documents_data)

@provider_bp.route('/profile')
@login_required
def profile():
    """Provider profile page"""
    require_provider_role()
    
    # Get manager info if user is provider_staff
    manager = None
    if current_user.role == 'provider_staff' and current_user.managed_by:
        manager = User.query.get(current_user.managed_by)
        
    return render_template('provider/profile.html', user=current_user, profile=current_user, manager=manager)

@provider_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update provider profile information"""
    require_provider_role()
    
    try:
        from flask import current_app
        from werkzeug.utils import secure_filename
        import os
        import uuid
        
        # Get form data
        organization = request.form.get('organization', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        
        # Validation
        if not all([organization, first_name, last_name, email]):
            return jsonify({'success': False, 'message': 'Please complete all required fields'}), 400
        
        # Email validation
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({'success': False, 'message': 'Invalid email address'}), 400
        
        # Check if email is already taken by another user
        existing_user = User.query.filter(
            User.email == email.lower(),
            User.id != current_user.id
        ).first()
        
        if existing_user:
            return jsonify({'success': False, 'message': 'Email already taken by another user'}), 400
        
        # Handle photo upload
        new_profile_pic = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '':
                # Check allowed extensions
                ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'jfif'}
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
                    # Generate unique filename
                    filename = secure_filename(file.filename)
                    file_extension = filename.rsplit('.', 1)[1].lower()
                    unique_filename = f"{uuid.uuid4()}_{current_user.id}.{file_extension}"
                    
                    # Create upload directory if it doesn't exist
                    UPLOAD_FOLDER = 'static/uploads/profile_pictures'
                    base_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
                    os.makedirs(base_dir, exist_ok=True)
                    
                    # Save file
                    file_path = os.path.join(base_dir, unique_filename)
                    file.save(file_path)
                    
                    # Delete old profile picture if exists
                    if current_user.profile_picture:
                        old_file_path = os.path.join(base_dir, current_user.profile_picture)
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    
                    new_profile_pic = unique_filename
        
        # Update user information using ORM (like admin routes)
        user = User.query.get(current_user.id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        user.organization = organization
        user.first_name = first_name
        user.last_name = last_name
        user.email = email.lower()
        if new_profile_pic:
            user.profile_picture = new_profile_pic
        user.updated_at = datetime.utcnow()
        
        # If provider admin updates organization, sync it to all their staff
        if current_user.role == 'provider_admin':
            staff_members = User.query.filter_by(managed_by=current_user.id).all()
            for staff in staff_members:
                staff.organization = organization
                staff.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Create notification
        try:
            notification = Notification(
                user_id=current_user.id,
                type='profile',
                title='Profile Updated',
                message='Your organization profile has been updated successfully.',
                created_at=datetime.utcnow(),
                is_active=True
            )
            db.session.add(notification)
            db.session.commit()
        except Exception as notif_error:
            print(f"Failed to create notification: {notif_error}")
            pass  # Continue even if notification fails
        
        # Prepare response with updated profile picture URL if changed
        response_data = {
            'success': True,
            'message': 'Profile updated successfully'
        }
        
        if new_profile_pic:
            response_data['profile_picture'] = new_profile_pic
            response_data['profile_picture_url'] = f"/static/uploads/profile_pictures/{new_profile_pic}"
        
        return jsonify(response_data)
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"Error updating profile: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Failed to update profile: {str(e)}'}), 500

@provider_bp.route('/reset-password', methods=['POST'])
@login_required
def reset_password():
    """Reset password for logged-in provider"""
    require_provider_role()
    
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
        
        # Verify current password
        user = User.query.get(current_user.id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        if not user.check_password(current_password):
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 400
        
        # Update password
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Password reset successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to reset password'}), 500

import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import make_response # make_response is already imported in the file

@provider_bp.route('/generate_report_pdf')
@login_required
def generate_report_pdf():
    """Generates a PDF report for the provider"""
    require_provider_role()

    # Get actual data
    provider_id = get_provider_id()
    scholarships = get_scholarships_query(provider_id).all()
    scholarship_ids = [s.id for s in scholarships]
    
    total_scholarships = len(scholarships)
    active_scholarships = len([s for s in scholarships if s.status in ['active', 'approved']])
    draft_scholarships = len([s for s in scholarships if s.status == 'draft'])
    archived_scholarships = len([s for s in scholarships if s.status == 'archived'])
    
    # Get application statistics
    if scholarship_ids:
        total_applications = ScholarshipApplication.query.filter(
            ScholarshipApplication.scholarship_id.in_(scholarship_ids)
        ).count()
        pending_applications = ScholarshipApplication.query.filter(
            ScholarshipApplication.scholarship_id.in_(scholarship_ids),
            ScholarshipApplication.status == 'pending',
            ScholarshipApplication.is_active == True
        ).count()
        approved_applications = ScholarshipApplication.query.filter(
            ScholarshipApplication.scholarship_id.in_(scholarship_ids),
            ScholarshipApplication.status == 'approved',
            ScholarshipApplication.is_active == True
        ).count()
        rejected_applications = ScholarshipApplication.query.filter(
            ScholarshipApplication.scholarship_id.in_(scholarship_ids),
            ScholarshipApplication.status == 'rejected',
            ScholarshipApplication.is_active == True
        ).count()
    else:
        total_applications = 0
        pending_applications = 0
        approved_applications = 0
        rejected_applications = 0

    # Create a file-like buffer to receive PDF data.
    buffer = io.BytesIO()
    
    # Create the PDF object, using the buffer as its "file."
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Header
    y = 750
    p.drawString(100, y, f"Provider Report for {current_user.organization or current_user.get_full_name()}")
    y -= 20
    p.drawString(100, y, f"Provider ID: PRV-{str(current_user.id).zfill(3)}")
    y -= 20
    p.drawString(100, y, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 20
    p.drawString(100, y, "-" * 60)
    
    # Scholarship Statistics
    y -= 30
    p.drawString(100, y, "SCHOLARSHIP STATISTICS:")
    y -= 20
    p.drawString(120, y, f"Total Scholarships: {total_scholarships}")
    y -= 20
    p.drawString(120, y, f"Active Scholarships: {active_scholarships}")
    y -= 20
    p.drawString(120, y, f"Draft Scholarships: {draft_scholarships}")
    y -= 20
    p.drawString(120, y, f"Archived Scholarships: {archived_scholarships}")
    
    # Application Statistics
    y -= 30
    p.drawString(100, y, "APPLICATION STATISTICS:")
    y -= 20
    p.drawString(120, y, f"Total Applications: {total_applications}")
    y -= 20
    p.drawString(120, y, f"Pending Applications: {pending_applications}")
    y -= 20
    p.drawString(120, y, f"Approved Applications: {approved_applications}")
    y -= 20
    p.drawString(120, y, f"Rejected Applications: {rejected_applications}")
    
    # List of Scholarships
    if scholarships:
        y -= 40
        if y < 100:
            p.showPage()
            y = 750
        
        p.drawString(100, y, "SCHOLARSHIP LIST:")
        y -= 20
        
        for scholarship in scholarships[:20]:  # Limit to 20 per page
            status_display = scholarship.status.upper()
            if scholarship.status == 'archived':
                status_display = "ARCHIVED"
            
            p.drawString(120, y, f"- {scholarship.code}: {scholarship.title} ({status_display})")
            y -= 20
            if y < 50:
                p.showPage()
                y = 750
        
        if len(scholarships) > 20:
            p.drawString(120, y, f"... and {len(scholarships) - 20} more scholarships")
            y -= 20

    # Close the PDF object cleanly.
    p.showPage()
    p.save()
    
    # Get the value of the BytesIO buffer and return it as a response
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=provider_report.pdf'
    return response

@provider_bp.route('/api/application/<int:application_id>/review', methods=['POST'])
@login_required
def review_application(application_id):
    """Approve or reject a scholarship application"""
    require_provider_role()

    data = request.get_json()
    action = data.get('action')

    application = ScholarshipApplication.query.get_or_404(application_id)
    scholarship = Scholarship.query.get_or_404(application.scholarship_id)

    provider_id = get_provider_id()
    if scholarship.provider_id != provider_id:
        return jsonify({'error': 'Access denied'}), 403

    # Map imperative action to status
    status_map = {
        'approve': 'approved',
        'approved': 'approved',
        'reject': 'rejected',
        'rejected': 'rejected'
    }

    if action in status_map:
        new_status = status_map[action]
        
        # Logic for approval with slots
        if new_status == 'approved' and application.status != 'approved':
            # Check if this is a renewal application (for later use)
            is_renewal = application.is_renewal if hasattr(application, 'is_renewal') else False
            original_application_id = application.original_application_id if hasattr(application, 'original_application_id') else None
            
            # For ALL applications (including renewals), check document requirements
            # Check if all required documents are provided
            req_str = scholarship.requirements or ''
            current_requirements = [r.strip() for r in req_str.split(',') if r.strip()]
            
            # Initialize unverified_docs outside the if block
            unverified_docs = []
            
            if current_requirements:
                # Requirement label mappings
                REQUIREMENT_MAPPINGS = {
                    'photo_2x2': 'Recent 2x2 or passport-size photo',
                    'valid_id': 'Valid School ID or any government-issued ID',
                    'enrollment_cert': 'Certificate of Enrollment',
                    'report_card': 'Report Card / Transcript of Records (TOR)',
                    'good_moral': 'Certificate of Good Moral Character',
                    'recommendation_letter': 'Recommendation Letter',
                    'honors_awards': 'Honors or Awards Certificates',
                    'indigency_cert': 'Certificate of Indigency',
                    'itr': "Parents' or Guardians' Income Tax Return (ITR)",
                    'proof_income': 'Proof of Income',
                    'barangay_clearance': 'Barangay Clearance or Residency Certificate',
                    'birth_cert': 'Birth Certificate (PSA or NSO)',
                    'medical_cert': 'Medical Certificate'
                }
                
                # Get linked files for this application
                linked_files = ScholarshipApplicationFile.query.filter_by(application_id=application_id).all()
                linked_map = {f.requirement_type: f.credential for f in linked_files if f.credential}
                
                # Check for missing documents
                missing_docs = []
                for req in current_requirements:
                    if req not in linked_map:
                        # Check if there's a loose credential match
                        student = User.query.get(application.user_id)
                        if student:
                            from credential_matcher import CredentialMatcher
                            loose_creds_orm = Credential.query.filter_by(user_id=student.id, is_active=True).order_by(Credential.upload_date.desc()).all()
                            loose_creds_list = [{
                                'credential_type': c.credential_type,
                                'file_name': c.file_name,
                                'file_path': c.file_path,
                                'id': c.id,
                                'is_verified': c.is_verified,
                                'status': c.status,
                                'upload_date': c.upload_date
                            } for c in loose_creds_orm]
                            matched_loose = CredentialMatcher.find_matching_credentials(current_requirements, loose_creds_list)
                            if req not in matched_loose or not matched_loose[req]:
                                missing_docs.append(req)
                
                if missing_docs:
                    req_labels = [REQUIREMENT_MAPPINGS.get(req, req) for req in missing_docs]
                    return jsonify({
                        'success': False, 
                        'error': f'Cannot approve: Missing required documents: {", ".join(req_labels)}'
                    }), 400
                
                # Check if all provided documents are verified
                for f in linked_files:
                    if f.credential and not f.credential.is_verified:
                        req_label = REQUIREMENT_MAPPINGS.get(f.requirement_type, f.requirement_type)
                        unverified_docs.append(req_label)
            
            # Only check unverified_docs if there were requirements
            if unverified_docs:
                return jsonify({
                    'success': False,
                    'error': f'Cannot approve: Please verify all documents first. Unverified: {", ".join(unverified_docs)}'
                }), 400
            
            # If this is a renewal application being approved, check next_last_semester_date
            # and handle it differently (mark as approved immediately)
            if is_renewal and new_status == 'approved':
                # Check if next_last_semester_date is set for the scholarship
                if not scholarship.next_last_semester_date:
                    return jsonify({
                        'success': False,
                        'error': 'Cannot approve renewal: Please set the "Next Last Semester Date" for this scholarship first. Go to Manage Scholarships to update the scholarship details.',
                        'error_type': 'missing_next_last_semester_date'
                    }), 400
                
                # Mark renewal as approved immediately
                # The old approved application stays approved until semester ends
                application.reviewed_at = datetime.utcnow()
                application.reviewed_by = current_user.id
                application.status = 'approved'  # Mark as approved immediately
                application.notes = (application.notes or '') + '\n[Renewal Approved - Will become active when current semester ends]'
                
                # Update scholarship counts (renewal is now approved)
                if scholarship.pending_count and scholarship.pending_count > 0:
                    scholarship.pending_count = max(0, scholarship.pending_count - 1)
                scholarship.approved_count = (scholarship.approved_count or 0) + 1
                
                # Don't update slots yet - will be done when semester ends
                # Skip the rest of approval logic for renewals (don't reject other applications)
                db.session.commit()
                
                # Send notification to student
                student = User.query.get(application.user_id)
                if student:
                    try:
                        send_email(
                            student.email,
                            f'Renewal Approved: {scholarship.title}',
                            'email/application_status.html',
                            student_name=student.get_full_name(),
                            scholarship_name=scholarship.title,
                            new_status='approved'
                        )
                    except:
                        pass
                    
                    # Create in-app notification
                    notification = Notification(
                        user_id=student.id,
                        type='application',
                        title=f'Renewal Approved: {scholarship.title}',
                        message=f'Your renewal request for {scholarship.title} has been approved. It will become active when your current semester ends.',
                        created_at=datetime.utcnow(),
                        is_active=True
                    )
                    db.session.add(notification)
                    db.session.commit()
                
                return jsonify({'success': True, 'message': 'Renewal has been approved. It will become active when the current semester ends.'})
            
            # CRITICAL: Only one scholarship can be approved per student at a time
            # Find and reject/withdraw all other applications for this student
            # EXCEPTION: Don't reject renewals or the original application if this is a renewal
            from sqlalchemy import text as sql_text
            
            # Get all other applications for this student (excluding current one and original if renewal)
            other_applications = ScholarshipApplication.query.filter(
                ScholarshipApplication.user_id == application.user_id,
                ScholarshipApplication.id != application_id,
                ScholarshipApplication.is_active == True
            ).all()
            
            # Filter out original application and other renewals if this is a renewal
            if is_renewal and original_application_id:
                other_applications = [app for app in other_applications if app.id != original_application_id]
            
            # Also filter out other renewals (they can coexist with the old approved application)
            if is_renewal:
                other_applications = [app for app in other_applications if not (hasattr(app, 'is_renewal') and app.is_renewal)]
            
            for other_app in other_applications:
                old_status = other_app.status
                # Reject other approved or pending applications
                # EXCEPTION: If this is a renewal rejection, don't reject the original approved application
                # (it should remain active until semester expires)
                if old_status in ['approved', 'pending']:
                    # Skip rejecting original application if this renewal was rejected
                    if is_renewal and new_status == 'rejected' and other_app.id == original_application_id:
                        continue
                    
                    other_app.status = 'rejected'
                    other_app.reviewed_at = datetime.utcnow()
                    other_app.reviewed_by = current_user.id
                    
                    # Update scholarship counts for rejected applications
                    other_scholarship = Scholarship.query.get(other_app.scholarship_id)
                    if other_scholarship:
                        if old_status == 'approved':
                            # Decrease approved count and increase rejected count
                            other_scholarship.approved_count = max(0, (other_scholarship.approved_count or 0) - 1)
                            other_scholarship.disapproved_count = (other_scholarship.disapproved_count or 0) + 1
                            # Return slot if applicable
                            if other_scholarship.slots is not None:
                                other_scholarship.slots += 1
                        elif old_status == 'pending':
                            # Decrease pending count and increase rejected count
                            other_scholarship.pending_count = max(0, (other_scholarship.pending_count or 0) - 1)
                            other_scholarship.disapproved_count = (other_scholarship.disapproved_count or 0) + 1
                        
                        # Notify student about rejection
                        student = User.query.get(other_app.user_id)
                        if student:
                            try:
                                send_email(
                                    student.email,
                                    f'Your Application for {other_scholarship.title} has been rejected',
                                    'email/application_status.html',
                                    student_name=student.get_full_name(),
                                    scholarship_name=other_scholarship.title,
                                    new_status='rejected'
                                )
                                
                                # Create in-app notification
                                notification = Notification(
                                    user_id=student.id,
                                    type='application',
                                    title=f'Application Rejected: {other_scholarship.title}',
                                    message=f'Your application for {other_scholarship.title} has been rejected because another application was approved.',
                                    created_at=datetime.utcnow(),
                                    is_active=True
                                )
                                db.session.add(notification)
                            except:
                                pass  # Continue even if email fails
            
            # Now proceed with approving the current application
            if scholarship.slots is not None:
                if scholarship.slots <= 0:
                    return jsonify({'success': False, 'error': 'No slots available for this scholarship.'}), 400
                scholarship.slots -= 1
            scholarship.approved_count = (scholarship.approved_count or 0) + 1
            if application.status == 'pending':
                scholarship.pending_count = max(0, (scholarship.pending_count or 0) - 1)
            
            # Set reviewed information
            application.reviewed_at = datetime.utcnow()
            application.reviewed_by = current_user.id
        
        # Logic for rejection
        elif new_status == 'rejected' and application.status != 'rejected':
            scholarship.disapproved_count = (scholarship.disapproved_count or 0) + 1
            if application.status == 'pending':
                scholarship.pending_count = max(0, (scholarship.pending_count or 0) - 1)
            
            # Set reviewed information for rejection
            application.reviewed_at = datetime.utcnow()
            application.reviewed_by = current_user.id

        application.status = new_status
        db.session.commit()

        student = User.query.get(application.user_id)
        if student:
            send_email(
                student.email,
                f'Your Application for {scholarship.title} has been {new_status}',
                'email/application_status.html',
                student_name=student.get_full_name(),
                scholarship_name=scholarship.title,
                new_status=new_status
            )
            
            # Create in-app notification for approval or rejection
            try:
                if new_status == 'approved':
                    notification = Notification(
                        user_id=student.id,
                        type='approved',
                        title=f'Application Approved: {scholarship.title}',
                        message=f'Congratulations! Your application for {scholarship.title} has been approved.',
                        created_at=datetime.utcnow(),
                        is_active=True
                    )
                elif new_status == 'rejected':
                    notification = Notification(
                        user_id=student.id,
                        type='application',
                        title=f'Application Rejected: {scholarship.title}',
                        message=f'Your application for {scholarship.title} has been rejected.',
                        created_at=datetime.utcnow(),
                        is_active=True
                    )
                else:
                    notification = None
                
                if notification:
                    db.session.add(notification)
                    db.session.commit()
            except Exception as e:
                db.session.rollback()
                # Continue even if notification creation fails - don't break the approval process
                print(f"Error creating notification: {e}")
        
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid action'}), 400

@provider_bp.route('/api/announcement/scholarship/<int:scholarship_id>', methods=['POST'])
@login_required
def send_broadcast_announcement(scholarship_id):
    """Send announcement to applicants of a scholarship, optionally filtered by status"""
    require_provider_role()

    data = request.get_json()
    message = data.get('message')
    title = data.get('title')
    status_filter = data.get('status_filter') # e.g. 'approved', 'pending', 'all'
    
    if not title or not message:
        return jsonify({'error': 'Title and message are required'}), 400
    
    scholarship = Scholarship.query.get_or_404(scholarship_id)
    provider_id = get_provider_id()
    if scholarship.provider_id != provider_id:
        return jsonify({'error': 'Access denied'}), 403

    # Build query
    query = ScholarshipApplication.query.filter_by(scholarship_id=scholarship_id)
    
    if status_filter and status_filter.lower() != 'all':
        query = query.filter(ScholarshipApplication.status == status_filter.lower())
        
    applications = query.all()
    students = [User.query.get(app.user_id) for app in applications]
    
    # Filter out None values just in case
    students = [s for s in students if s]

    if not students:
        return jsonify({'success': False, 'error': 'No recipients found matching criteria'})

    # Send emails and notifications
    for student in students:
        # Email
        send_email(
            student.email,
            f'{title} - {scholarship.title}',
            'email/new_announcement.html',
            student_name=student.get_full_name(),
            announcement_title=title,
            announcement_message=message
        )
        
        # In-app Notification
        notification = Notification(
            user_id=student.id,
            type='info',
            title=title,
            message=f"Announcement regarding {scholarship.title}: {message}",
            created_at=datetime.utcnow(),
            is_active=True
        )
        db.session.add(notification)

    # Record Announcement History
    filter_desc = f"Scholarship: {scholarship.code} ({status_filter.title() if status_filter else 'All'})"
    announcement = Announcement(
        provider_id=provider_id,
        type='broadcast',
        recipient_filter=filter_desc,
        recipient_count=len(students),
        title=title,
        message=message,
        created_at=datetime.utcnow()
    )
    db.session.add(announcement)
    db.session.commit()
    
    return jsonify({'success': True, 'recipient_count': len(students), 'scholarship': scholarship.title, 'message': 'Announcement sent successfully'})

@provider_bp.route('/api/announcement/individual', methods=['POST'])
@login_required
def send_individual_announcement():
    """Send announcement to a specific student by looking them up"""
    require_provider_role()

    data = request.get_json()
    recipient_str = data.get('recipient') # Name, ID, or Email string
    title = data.get('title')
    message = data.get('message')

    if not recipient_str or not title or not message:
        return jsonify({'error': 'Recipient, title, and message are required'}), 400

    # Find the student
    # We search for a student who has applied to ANY of this provider's scholarships
    provider_id = get_provider_id()
    scholarships = get_scholarships_query(provider_id).all()
    scholarship_ids = [s.id for s in scholarships]
    
    if not scholarship_ids:
        return jsonify({'error': 'You have no scholarships/students'}), 400

    # Helper to parse input (could be "John Doe (12345678)")
    search_term = recipient_str
    if '(' in recipient_str:
         # Extract ID if present in format "Name (ID)"
         import re
         # Match content inside the last pair of parentheses
         match = re.search(r'\(([^)]+)\)$', recipient_str.strip())
         if match:
             search_term = match.group(1)

    # Query logic: Join User with Applications
    student = User.query.join(ScholarshipApplication, User.id == ScholarshipApplication.user_id).filter(
        ScholarshipApplication.scholarship_id.in_(scholarship_ids),
        or_(
            User.student_id == search_term,
            User.email == search_term,
            (User.first_name + ' ' + User.last_name).like(f"%{search_term}%")
        )
    ).first()

    if not student:
         return jsonify({'error': 'Student not found or not an applicant to your scholarships'}), 404

    # Send Email
    send_email(
        student.email,
        f'{title}',
        'email/new_announcement.html',
        student_name=student.get_full_name(),
        announcement_title=title,
        announcement_message=message
    )
    
    # In-app Notification
    notification = Notification(
        user_id=student.id,
        type='info',
        title=title,
        message=message,
        created_at=datetime.utcnow(),
        is_active=True
    )
    db.session.add(notification)

    # Record History
    announcement = Announcement(
        provider_id=provider_id,
        type='individual',
        recipient_filter=f"Student: {student.get_full_name()} ({student.student_id})",
        recipient_count=1,
        title=title,
        message=message,
        created_at=datetime.utcnow()
    )
    db.session.add(announcement)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Announcement sent successfully'})

@provider_bp.route('/api/application/<int:application_id>/schedule', methods=['POST'])
@login_required
def create_schedule(application_id):
    """Create a schedule for an application"""
    require_provider_role()

    data = request.get_json()
    schedule_date = data.get('schedule_date')
    schedule_time = data.get('schedule_time')
    location = data.get('location')
    notes = data.get('notes')

    application = ScholarshipApplication.query.get_or_404(application_id)
    scholarship = Scholarship.query.get_or_404(application.scholarship_id)

    provider_id = get_provider_id()
    if scholarship.provider_id != provider_id:
        return jsonify({'error': 'Access denied'}), 403

    schedule = Schedule(
        application_id=application_id,
        provider_id=current_user.id,
        user_id=application.user_id,
        schedule_date=schedule_date,
        schedule_time=schedule_time,
        location=location,
        notes=notes
    )
    db.session.add(schedule)
    
    # Create in-app notification for the student
    notification = Notification(
        user_id=application.user_id,
        type='schedule',
        title=f'Interview Scheduled: {scholarship.title}',
        message=f'An interview has been scheduled for {schedule_date} at {schedule_time}. Location: {location}.',
        created_at=datetime.utcnow(),
        is_active=True
    )
    db.session.add(notification)
    
    db.session.commit()

    student = User.query.get(application.user_id)
    if student:
        send_email(
            student.email,
            f'Schedule for {scholarship.title}',
            'email/new_schedule.html',
            student_name=student.get_full_name(),
            scholarship_name=scholarship.title,
            schedule_date=schedule_date,
            schedule_time=schedule_time,
            location=location,
            notes=notes
        )

    return jsonify({'success': True})

@provider_bp.route('/api/credential/<int:credential_id>/review', methods=['POST'])
@login_required
def review_credential(credential_id):
    """Approve or reject a credential; notify student"""
    require_provider_role()
    try:
        from flask import current_app
        from datetime import datetime
        db = current_app.extensions['sqlalchemy']
        data = request.get_json() or {}
        action = (data.get('action') or '').strip().lower()
        if action not in ('approve', 'reject'):
            return jsonify({'success': False, 'error': 'Invalid action'}), 400

        # Load credential and verify ownership
        credential = Credential.query.get(credential_id)
        if not credential:
            return jsonify({'success': False, 'error': 'Credential not found'}), 404

        # Check that the provider has access to this student's application
        provider_id = get_provider_id()
        application = ScholarshipApplication.query.join(Scholarship).filter(
            Scholarship.provider_id == provider_id,
            ScholarshipApplication.user_id == credential.user_id
        ).first()

        if not application:
            return jsonify({'success': False, 'error': 'Access to this credential is not authorized'}), 403

        # Map action to status (past tense)
        new_status = 'approved' if action == 'approve' else 'rejected'
        credential.status = new_status
        credential.is_verified = (new_status == 'approved')
        
        # Create in-app notification for the student
        notification = Notification(
            user_id=credential.user_id,
            type='document',
            title=f'Document Reviewed: {credential.credential_type}',
            message=f'Your document "{credential.credential_type}" has been {new_status}.',
            created_at=datetime.utcnow(),
            is_active=True
        )
        db.session.add(notification)
        
        db.session.commit()

        # Send email notification
        student = User.query.get(credential.user_id)
        if student:
            send_email(
                student.email,
                f'Your Document {credential.credential_type} has been {new_status}',
                'email/document_status.html',
                student_name=student.get_full_name(),
                document_name=credential.credential_type,
                new_status=new_status.capitalize()
            )

        return jsonify({'success': True})
    except Exception as e:
        if 'db' in locals():
            db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# --- New API Endpoints for Dashboard & Management ---

@provider_bp.route('/api/scholarships/list')
@login_required
def api_scholarships_list():
    """Get list of scholarships for dashboard charts/tables"""
    require_provider_role()
    
    provider_id = get_provider_id()
    scholarships = get_scholarships_query(provider_id).all()
    data = []
    for s in scholarships:
        data.append({
            'id': s.id,
            'code': s.code,
            'title': s.title,
            'status': s.status,
            'applications_count': s.applications.count(), # Use dynamic count
            'deadline': s.deadline.strftime('%Y-%m-%d') if s.deadline else None,
            'created_at': s.created_at.strftime('%Y-%m-%d')
        })
    return jsonify({'success': True, 'scholarships': data})

@provider_bp.route('/api/applications/list')
@login_required
def api_applications_list():
    """Get list of applications for dashboard"""
    require_provider_role()
    
    provider_id = get_provider_id()
    scholarships = get_scholarships_query(provider_id).all()
    scholarship_ids = [s.id for s in scholarships]
    
    applications = ScholarshipApplication.query.filter(
        ScholarshipApplication.scholarship_id.in_(scholarship_ids)
    ).all()
    
    data = []
    for app in applications:
        student = User.query.get(app.user_id)
        scholarship = Scholarship.query.get(app.scholarship_id)
        data.append({
            'id': app.id,
            'scholarship_name': scholarship.title if scholarship else 'Unknown',
            'applicant_name': student.get_full_name() if student else 'Unknown',
            'status': app.status,
            'date': app.application_date.strftime('%Y-%m-%d')
        })
    return jsonify(data)

@provider_bp.route('/api/scholarships/search')
@login_required
def api_scholarships_search():
    """Autocomplete search for scholarships"""
    require_provider_role()
    
    provider_id = get_provider_id()
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])

    # Find matching scholarships for this provider
    provider_id = get_provider_id()
    base_query = get_scholarships_query(provider_id)
    scholarships = base_query.filter(or_(
        Scholarship.title.like(f"%{query}%"),
        Scholarship.code.like(f"%{query}%")
    )).limit(10).all()
        
    data = []
    for s in scholarships:
        # Format: "Title (Code)"
        display = f"{s.title} ({s.code})"
        data.append({
            'id': s.id,
            'display': display,
            'title': s.title,
            'code': s.code
        })
        
    return jsonify(data)

@provider_bp.route('/api/students/search')
@login_required
def api_students_search():
    """Autocomplete search for students"""
    require_provider_role()
    
    provider_id = get_provider_id()
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify([])

    scholarships = get_scholarships_query(provider_id).all()
    scholarship_ids = [s.id for s in scholarships]
    
    if not scholarship_ids:
        return jsonify([])

    # Find matching students
    results = db.session.query(User.id, User.first_name, User.last_name, User.student_id, User.email)\
        .join(ScholarshipApplication, User.id == ScholarshipApplication.user_id)\
        .filter(ScholarshipApplication.scholarship_id.in_(scholarship_ids))\
        .filter(or_(
            User.student_id.like(f"%{query}%"),
            User.email.like(f"%{query}%"),
            (User.first_name + ' ' + User.last_name).like(f"%{query}%")
        ))\
        .distinct().limit(10).all()
        
    data = []
    for r in results:
        full_name = f"{r[1]} {r[2]}"
        # Format: "Name (ID)"
        display = f"{full_name} ({r[3]})"
        data.append({
            'id': r[0],
            'display': display,
            'name': full_name,
            'student_id': r[3],
            'email': r[4]
        })
        
    return jsonify(data)

@provider_bp.route('/api/announcements/history')
@login_required
def api_announcements_history():
    """Get history of sent announcements with search"""
    require_provider_role()
    
    provider_id = get_provider_id()
    search_q = request.args.get('search', '').strip()
    
    query = Announcement.query.filter_by(provider_id=provider_id)
    
    if search_q:
        query = query.filter(Announcement.title.like(f"%{search_q}%"))
        
    # Latest 10
    announcements = query.order_by(Announcement.created_at.desc()).limit(10).all()
    
    def format_time(dt):
        now = datetime.utcnow()
        diff = now - dt
        s = int(diff.total_seconds())
        if s < 60: return "Just now"
        if s < 3600: return f"{s//60}m ago"
        if s < 86400: return f"{s//3600}h ago"
        return dt.strftime('%b %d, %Y')
    
    data = []
    for ann in announcements:
        data.append({
            'id': ann.id,
            'title': ann.title,
            'type': ann.type,
            'recipient_filter': ann.recipient_filter,
            'message': ann.message,
            'count': ann.recipient_count,
            'created_at': format_time(ann.created_at),
            'created_at_full': ann.created_at.strftime('%Y-%m-%d %I:%M %p')
        })
        
    return jsonify({'success': True, 'announcements': data})

@provider_bp.route('/api/scholarship/<int:id>/publish', methods=['POST'])
@login_required
def api_publish_scholarship(id):
    """Publish a scholarship by its ID"""
    require_provider_admin()
        
    scholarship = Scholarship.query.get_or_404(id)
    
    if scholarship.provider_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    scholarship.status = 'approved'
    
    # Notify matching students when scholarship is published
    notify_matching_students(scholarship)
    
    db.session.commit()
    
    return jsonify({'success': True})

@provider_bp.route('/api/create-scholarship', methods=['POST'])
@login_required
def api_create_scholarship():
    """Create a new scholarship"""
    require_provider_admin()
        
    data = request.get_json()
    
    # Basic Validation
    if not data.get('title') or not data.get('code'):
        return jsonify({'success': False, 'error': 'Title and Code are required'}), 400
        
    try:
        # Get provider ID (for admin, this is their own ID)
        provider_id = get_provider_id()
        
        # Check for duplicate code
        if Scholarship.query.filter_by(code=data['code']).first():
            return jsonify({'success': False, 'error': 'Scholarship code already exists'}), 400

        new_scholarship = Scholarship(
            provider_id=provider_id,
            title=data['title'],
            code=data['code'],
            description=data.get('description', ''),
            amount=data.get('amount', ''),
            status='draft', # Default to draft
            requirements=data.get('requirements', ''),
            # Parse deadline if provided
            deadline=datetime.strptime(data['deadline'], '%Y-%m-%d').date() if data.get('deadline') else None,
            # New fields
            type=data.get('type', ''),
            level=data.get('level', ''),
            eligibility=data.get('minimum_gpa', ''),  # Minimum GPA goes in eligibility column
            program_course=data.get('program_course', ''),
            additional_criteria=data.get('additional_criteria', ''),
            slots=int(data.get('slots')) if data.get('slots') else None,
            contact_name=data.get('contact_name', ''),
            contact_email=data.get('contact_email', ''),
            contact_phone=data.get('contact_phone', ''),
            # Semester and school year fields
            semester=data.get('semester', ''),
            school_year=data.get('school_year', ''),
            semester_date=datetime.strptime(data['semester_date'], '%Y-%m-%d').date() if data.get('semester_date') and str(data.get('semester_date', '')).strip() else None,
            next_last_semester_date=datetime.strptime(data['next_last_semester_date'], '%Y-%m-%d').date() if data.get('next_last_semester_date') and str(data.get('next_last_semester_date', '')).strip() else None
        )
        
        db.session.add(new_scholarship)
        db.session.flush()  # Flush to get the ID without committing
        
        # If scholarship is created as approved/active, notify matching students
        if new_scholarship.status in ('approved', 'active'):
            notify_matching_students(new_scholarship)
        
        db.session.commit()
        
        return jsonify({'success': True, 'id': new_scholarship.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/scholarship/<int:id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_scholarship_detail(id):
    """Get, Update, or Archive a scholarship"""
    require_provider_admin()
        
    scholarship = Scholarship.query.get_or_404(id)
    
    if scholarship.provider_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'scholarship': {
                'id': scholarship.id,
                'code': scholarship.code,
                'title': scholarship.title,
                'description': scholarship.description or '',
                'amount': scholarship.amount or '',
                'deadline': scholarship.deadline.strftime('%Y-%m-%d') if scholarship.deadline else '',
                'created_date': scholarship.created_at.strftime('%Y-%m-%d') if scholarship.created_at else '',
                'requirements': scholarship.requirements,
                'status': scholarship.status,
                'applications_count': scholarship.applications.count(),
                # New fields
                'type': scholarship.type or '',
                'level': scholarship.level or '',
                'eligibility': scholarship.eligibility or '',  # Minimum GPA
                'program_course': scholarship.program_course or '',
                'additional_criteria': scholarship.additional_criteria or '',
                'slots': scholarship.slots or '',
                'contact_name': scholarship.contact_name or '',
                'contact_email': scholarship.contact_email or '',
                'contact_phone': scholarship.contact_phone or '',
                'semester': scholarship.semester or '',
                'school_year': scholarship.school_year or '',
                'semester_date': scholarship.semester_date.strftime('%Y-%m-%d') if scholarship.semester_date else '',
                'next_last_semester_date': scholarship.next_last_semester_date.strftime('%Y-%m-%d') if scholarship.next_last_semester_date else ''
            }
        })
        
    elif request.method == 'POST':
        data = request.get_json()
        try:
            old_status = scholarship.status
            old_program_course = scholarship.program_course
            
            if 'title' in data: scholarship.title = data['title']
            if 'description' in data: scholarship.description = data['description']
            if 'amount' in data: scholarship.amount = data['amount']
            if 'requirements' in data: scholarship.requirements = data['requirements']
            if 'deadline' in data and data['deadline']:
                scholarship.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date()
            if 'status' in data: scholarship.status = data['status']
            # New fields update
            if 'type' in data: scholarship.type = data['type']
            if 'level' in data: scholarship.level = data['level']
            if 'minimum_gpa' in data: scholarship.eligibility = data['minimum_gpa']  # Minimum GPA in eligibility column
            if 'program_course' in data: scholarship.program_course = data['program_course']
            if 'additional_criteria' in data: scholarship.additional_criteria = data['additional_criteria']
            if 'slots' in data: scholarship.slots = int(data['slots']) if data['slots'] else None
            if 'contact_name' in data: scholarship.contact_name = data['contact_name']
            if 'contact_email' in data: scholarship.contact_email = data['contact_email']
            if 'contact_phone' in data: scholarship.contact_phone = data['contact_phone']
            # Semester and school year fields
            if 'semester' in data: scholarship.semester = data['semester']
            if 'school_year' in data: scholarship.school_year = data['school_year']
            if 'semester_date' in data and data['semester_date'] and str(data['semester_date']).strip():
                scholarship.semester_date = datetime.strptime(data['semester_date'], '%Y-%m-%d').date()
            elif 'semester_date' in data:
                scholarship.semester_date = None
            if 'next_last_semester_date' in data and data['next_last_semester_date'] and str(data['next_last_semester_date']).strip():
                scholarship.next_last_semester_date = datetime.strptime(data['next_last_semester_date'], '%Y-%m-%d').date()
            elif 'next_last_semester_date' in data:
                scholarship.next_last_semester_date = None
            
            # Notify matching students if:
            # 1. Status changed to approved/active (from draft or other status)
            # 2. Program course was updated and scholarship is active/approved
            should_notify = False
            if 'status' in data:
                new_status = data['status']
                if new_status in ('approved', 'active') and old_status not in ('approved', 'active'):
                    should_notify = True
            elif 'program_course' in data and scholarship.status in ('approved', 'active'):
                if data['program_course'] != old_program_course:
                    should_notify = True
            
            if should_notify:
                notify_matching_students(scholarship)
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            # Get all active applications for this scholarship before archiving
            applications = ScholarshipApplication.query.filter_by(
                scholarship_id=id,
                is_active=True
            ).all()
            
            # Archive the scholarship
            scholarship.status = 'archived'
            db.session.commit()
            
            # Send notifications and emails to students who have applications
            for app in applications:
                student = User.query.get(app.user_id)
                if student:
                    # Create in-app notification
                    notification = Notification(
                        user_id=student.id,
                        type='application',
                        title=f'Scholarship Archived: {scholarship.title}',
                        message=f'Your applied scholarship "{scholarship.title}" has been archived by the provider. Your application status may be affected.',
                        created_at=datetime.utcnow(),
                        is_active=True
                    )
                    db.session.add(notification)
                    
                    # Send email notification
                    try:
                        send_email(
                            student.email,
                            f'Your Applied Scholarship Has Been Archived',
                            'email/application_status.html',
                            student_name=student.get_full_name(),
                            scholarship_name=scholarship.title,
                            new_status='archived'
                        )
                    except Exception as e:
                        print(f"Failed to send email to {student.email}: {e}")
            
            # Commit notifications
            if applications:
                db.session.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/scholarship/<int:id>/restore', methods=['POST'])
@login_required
def api_scholarship_restore(id):
    """Restore an archived scholarship and remove all student applications"""
    require_provider_admin()
    
    scholarship = Scholarship.query.get_or_404(id)
    
    if scholarship.provider_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    try:
        from sqlalchemy import text as sql_text
        
        # Get all active applications for this scholarship before removing
        applications = ScholarshipApplication.query.filter_by(
            scholarship_id=id,
            is_active=True
        ).all()
        
        # Track counts before removal
        pending_before = sum(1 for app in applications if app.status == 'pending')
        approved_before = sum(1 for app in applications if app.status == 'approved')
        rejected_before = sum(1 for app in applications if app.status == 'rejected')
        total_before = len(applications)
        
        # Store student information before removing applications (for notifications)
        students_to_notify = []
        for app in applications:
            student = User.query.get(app.user_id)
            if student:
                students_to_notify.append({
                    'student': student,
                    'app_status': app.status
                })
        
        # Remove all student applications for this scholarship
        for app in applications:
            app.is_active = False
            app.status = 'withdrawn'  # Mark as withdrawn since scholarship was restored
        
        # Recalculate and update scholarship application counts from database
        # This ensures counts are accurate based on active applications only
        counts = db.session.execute(
            sql_text("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' AND is_active = 1 THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'approved' AND is_active = 1 THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN status = 'rejected' AND is_active = 1 THEN 1 ELSE 0 END) as rejected
                FROM scholarship_applications
                WHERE scholarship_id = :scholarship_id AND is_active = 1
            """),
            {"scholarship_id": id}
        ).fetchone()
        
        # Update counts (should all be 0 after deactivation, but recalculate to be sure)
        scholarship.applications_count = counts[0] or 0
        scholarship.pending_count = counts[1] or 0
        scholarship.approved_count = counts[2] or 0
        scholarship.disapproved_count = counts[3] or 0
        
        # Restore scholarship status to draft
        scholarship.status = 'draft'
        
        db.session.commit()
        
        # Send notifications and emails to students who had applications
        for student_info in students_to_notify:
            student = student_info['student']
            app_status = student_info['app_status']
            
            # Create in-app notification
            notification = Notification(
                user_id=student.id,
                type='application',
                title=f'Scholarship Restored: {scholarship.title}',
                message=f'Your previous applied scholarship "{scholarship.title}" has been restored. Your previous application has been removed and you will need to apply again if you are still interested.',
                created_at=datetime.utcnow(),
                is_active=True
            )
            db.session.add(notification)
            
            # Send email notification
            try:
                send_email(
                    student.email,
                    f'Your Previous Applied Scholarship Has Been Restored',
                    'email/application_status.html',
                    student_name=student.get_full_name(),
                    scholarship_name=scholarship.title,
                    new_status='restored'
                )
            except Exception as e:
                print(f"Failed to send email to {student.email}: {e}")
        
        # Commit notifications
        if students_to_notify:
            db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Scholarship restored. {total_before} application(s) were removed. Application counts have been reset to zero.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/scholarship/<int:id>/permanent-delete', methods=['DELETE'])
@login_required
def api_scholarship_permanent_delete(id):
    """Permanently delete a scholarship"""
    require_provider_admin()
    
    scholarship = Scholarship.query.get_or_404(id)
    
    if scholarship.provider_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    try:
        # Try to delete. If foreign key constraints fail, it will raise an error.
        db.session.delete(scholarship)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        # Check if error is due to integrity constraint (related records)
        return jsonify({'success': False, 'error': 'Cannot delete scholarship. It may have related applications.'}), 500

@provider_bp.route('/api/application/<int:id>')
@login_required
def api_application_detail(id):
    """Get application details for modal"""
    try:
        require_provider_role()
        
        provider_id = get_provider_id()
        application = ScholarshipApplication.query.get_or_404(id)
        scholarship = Scholarship.query.get(application.scholarship_id)
        
        if not scholarship:
            return jsonify({'success': False, 'error': 'Scholarship not found'}), 404
        
        if scholarship.provider_id != provider_id:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
            
        student = User.query.get(application.user_id)
        
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        # Get current scholarship requirements
        req_str = scholarship.requirements or ''
        current_requirements = [r.strip() for r in req_str.split(',') if r.strip()]
        
        # Fetch files linked to this specific application
        linked_files = ScholarshipApplicationFile.query.filter_by(application_id=application.id).all()
        
        # Fetch all active loose credentials for user
        loose_creds_orm = Credential.query.filter_by(user_id=student.id, is_active=True).order_by(Credential.upload_date.desc()).all()
        
        # Convert to list of dicts for Matcher
        loose_creds_list = []
        for c in loose_creds_orm:
            loose_creds_list.append({
                'credential_type': c.credential_type,
                'file_name': c.file_name,
                'file_path': c.file_path,
                'id': c.id,
                'is_verified': c.is_verified,
                'status': c.status,
                'upload_date': c.upload_date
            })
            
        # Find matches using advanced logic
        matched_loose = CredentialMatcher.find_matching_credentials(current_requirements, loose_creds_list)
        
        # Map linked files by requirement type
        linked_map = {f.requirement_type: f.credential for f in linked_files if f.credential}
        
        cred_list = []
        
        # Iterate requirements to build the list - include ALL required documents
        for req in current_requirements:
            cred = linked_map.get(req)
            
            # Check if linked credential is active
            if cred and cred.is_active:
                # Linked file exists and is active
                cred_list.append({
                    'id': cred.id,
                    'requirement_type': req,
                    'file_name': cred.file_name,
                    'file_path': cred.file_path,
                    'status': cred.status,
                    'is_verified': cred.is_verified,
                    'is_active': cred.is_active,
                    'is_missing': False
                })
            else:
                # Linked credential doesn't exist or is inactive - check for loose match
                matches = matched_loose.get(req, [])
                if matches:
                    # Use the best match (first one, as loose_creds is sorted DESC - newest first)
                    match = matches[0]
                    cred_list.append({
                        'id': match['id'],
                        'requirement_type': req,
                        'file_name': match['file_name'],
                        'file_path': match['file_path'],
                        'status': match['status'],
                        'is_verified': match['is_verified'],
                        'is_active': True,
                        'is_missing': False
                    })
                else:
                    # Document is missing - add it to the list with missing flag
                    cred_list.append({
                        'id': None,
                        'requirement_type': req,
                        'file_name': None,
                        'file_path': None,
                        'status': None,
                        'is_verified': False,
                        'is_active': False,
                        'is_missing': True
                    })
        
        # Also include any linked files that are NOT in current requirements (extra/old requirements)
        for req, cred in linked_map.items():
            if req not in current_requirements:
                 cred_list.append({
                    'id': cred.id,
                    'requirement_type': req,
                    'file_name': cred.file_name,
                    'file_path': cred.file_path,
                    'status': cred.status,
                    'is_verified': cred.is_verified,
                    'is_active': cred.is_active
                })
        
        # Get Family Background information
        family_bg = db.session.execute(
            text("""
                SELECT parent_guardian_name, occupation, household_income, dependents
                FROM family_backgrounds
                WHERE application_id = :id
                LIMIT 1
            """), {"id": application.id}
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
            """), {"id": application.id}
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
            """), {"id": application.id}
        ).fetchone()
        
        personal_information = None
        if personal_info:
            personal_information = {
                "department": personal_info[0] or "",
                "school_university": personal_info[1] or "",
                "address": personal_info[2] or "",
                "contact_number": personal_info[3] or ""
            }
        
        # Get remarks made by current provider for this student
        provider_id = get_provider_id()
        remarks = StudentRemark.query.filter_by(
            student_id=student.id,
            provider_id=provider_id
        ).order_by(StudentRemark.created_at.desc()).all()
        
        remarks_list = []
        for remark in remarks:
            remarks_list.append({
                'id': remark.id,
                'remark_text': remark.remark_text,
                'created_at': remark.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': remark.updated_at.strftime('%Y-%m-%d %H:%M:%S') if remark.updated_at else None
            })
            
        # Get renewal status
        is_renewal = application.is_renewal if hasattr(application, 'is_renewal') else False
        renewal_failed = application.renewal_failed if hasattr(application, 'renewal_failed') else False
        original_application_id = application.original_application_id if hasattr(application, 'original_application_id') else None
        
        return jsonify({
            'success': True,
            'application': {
                'id': application.id,
                'student_name': student.get_full_name() if student else 'Unknown',
                'student_email': student.email if student else '',
                'student_id': student.student_id if student else '',
                'scholarship_title': scholarship.title,
                'date_applied': application.application_date.strftime('%Y-%m-%d'),
                'status': application.status,
                'is_renewal': is_renewal,
                'renewal_failed': renewal_failed,
                'original_application_id': original_application_id
            },
            'credentials': cred_list,
            'family_background': family_background,
            'academic_information': academic_information,
            'personal_information': personal_information,
            'remarks': remarks_list
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error loading application details: {str(e)}'}), 500

@provider_bp.route('/api/student/<int:student_id>/remarks', methods=['GET'])
@login_required
def api_get_student_remarks(student_id):
    """Get all remarks for a student (only remarks made by current provider)"""
    try:
        require_provider_role()
        
        provider_id = get_provider_id()
        # Verify student exists
        student = User.query.get_or_404(student_id)
        if student.role != 'student':
            return jsonify({'success': False, 'error': 'Invalid student'}), 400
        
        # Get remarks made by current provider (admin or staff's admin) for this student
        remarks = StudentRemark.query.filter_by(
            student_id=student_id,
            provider_id=provider_id
        ).order_by(StudentRemark.created_at.desc()).all()
        
        remarks_list = []
        for remark in remarks:
            remarks_list.append({
                'id': remark.id,
                'remark_text': remark.remark_text,
                'created_at': remark.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': remark.updated_at.strftime('%Y-%m-%d %H:%M:%S') if remark.updated_at else None
            })
        
        return jsonify({'success': True, 'remarks': remarks_list})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error loading remarks: {str(e)}'}), 500

@provider_bp.route('/api/student/<int:student_id>/remarks', methods=['POST'])
@login_required
def api_add_student_remark(student_id):
    """Add a new remark for a student"""
    try:
        require_provider_role()
        
        provider_id = get_provider_id()
        data = request.get_json()
        remark_text = data.get('remark_text', '').strip()
        
        if not remark_text:
            return jsonify({'success': False, 'error': 'Remark text is required'}), 400
        
        # Verify student exists
        student = User.query.get_or_404(student_id)
        if student.role != 'student':
            return jsonify({'success': False, 'error': 'Invalid student'}), 400
        
        # Create new remark
        remark = StudentRemark(
            student_id=student_id,
            provider_id=provider_id,
            remark_text=remark_text
        )
        
        db.session.add(remark)
        
        # Create in-app notification for the student
        provider_name = current_user.organization or current_user.get_full_name()
        # Truncate remark text for notification (first 150 chars)
        remark_preview = remark_text[:150] + ('...' if len(remark_text) > 150 else '')
        
        notification = Notification(
            user_id=student_id,
            type='info',
            title=f'New Remark from {provider_name}',
            message=f'A provider has added a remark about your application. View your application details to see the full remark.',
            created_at=datetime.utcnow(),
            is_active=True
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'remark': {
                'id': remark.id,
                'remark_text': remark.remark_text,
                'created_at': remark.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error adding remark: {str(e)}'}), 500

@provider_bp.route('/api/add-remarks', methods=['POST'])
@login_required
def api_add_remarks():
    """Add a remark to an application (ApplicationRemark)"""
    try:
        require_provider_role()
        
        provider_id = get_provider_id()
        data = request.get_json()
        application_id = data.get('application_id')
        remark_text = data.get('remark_text', '').strip()
        status = data.get('status', 'review')
        
        if not application_id or not remark_text:
            return jsonify({'success': False, 'error': 'Application ID and remark text are required'}), 400
        
        # Verify application exists and belongs to provider
        application = ScholarshipApplication.query.get_or_404(application_id)
        scholarship = Scholarship.query.get(application.scholarship_id)
        
        if not scholarship or scholarship.provider_id != provider_id:
            return jsonify({'success': False, 'error': 'Unauthorized access to this application'}), 403
        
        # Create ApplicationRemark
        remark = ApplicationRemark(
            application_id=application_id,
            provider_id=provider_id,
            remark_text=remark_text,
            status=status
        )
        
        db.session.add(remark)
        
        # Create in-app notification for the student
        student = User.query.get(application.user_id)
        if student:
            provider_name = current_user.organization or current_user.get_full_name()
            notification = Notification(
                user_id=student.id,
                type='info',
                title=f'New Remark from {provider_name}',
                message=f'A provider has added a remark to your application for {scholarship.title}.',
                created_at=datetime.utcnow(),
                is_active=True
            )
            db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Remark added successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error adding remark: {str(e)}'}), 500

@provider_bp.route('/api/scholarship/<int:id>/report-pdf')
@login_required
def api_scholarship_report_pdf(id):
    """Download PDF report for a specific scholarship (works for both active and archived)"""
    require_provider_role()

    scholarship = Scholarship.query.get_or_404(id)
    provider_id = get_provider_id()
    if scholarship.provider_id != provider_id:
        flash('Unauthorized', 'error')
        return redirect(url_for('provider.scholarships'))

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Header
    y = 750
    p.drawString(100, y, f"Scholarship Report: {scholarship.title}")
    y -= 20
    p.drawString(100, y, f"Code: {scholarship.code}")
    y -= 20
    p.drawString(100, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 20
    p.drawString(100, y, "-" * 60)
    
    # Scholarship Details
    y -= 30
    p.drawString(100, y, "SCHOLARSHIP DETAILS:")
    y -= 20
    
    status_display = scholarship.status.upper()
    if scholarship.status == 'archived':
        status_display = "ARCHIVED"
    
    p.drawString(120, y, f"Status: {status_display}")
    y -= 20
    
    if scholarship.description:
        # Handle long descriptions with word wrapping
        desc_lines = []
        words = scholarship.description.split()
        current_line = ""
        for word in words:
            if len(current_line + word) < 60:
                current_line += word + " "
            else:
                if current_line:
                    desc_lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            desc_lines.append(current_line.strip())
        
        p.drawString(120, y, "Description:")
        y -= 15
        for line in desc_lines[:5]:  # Limit to 5 lines
            p.drawString(140, y, line)
            y -= 15
        if len(desc_lines) > 5:
            p.drawString(140, y, "...")
            y -= 15
    
    if scholarship.amount:
        p.drawString(120, y, f"Amount: {scholarship.amount}")
        y -= 20
    
    if scholarship.deadline:
        p.drawString(120, y, f"Deadline: {scholarship.deadline.strftime('%Y-%m-%d')}")
        y -= 20
    
    if scholarship.type:
        p.drawString(120, y, f"Type: {scholarship.type}")
        y -= 20
    
    if scholarship.level:
        p.drawString(120, y, f"Level: {scholarship.level}")
        y -= 20
    
    if scholarship.slots is not None:
        p.drawString(120, y, f"Slots: {scholarship.slots}")
        y -= 20
    
    if scholarship.eligibility:
        p.drawString(120, y, f"Minimum GPA: {scholarship.eligibility}")
        y -= 20
    
    if scholarship.program_course:
        p.drawString(120, y, f"Program/Course: {scholarship.program_course}")
        y -= 20
    
    if scholarship.additional_criteria:
        # Handle long additional criteria with word wrapping
        criteria_lines = []
        words = scholarship.additional_criteria.split()
        current_line = ""
        for word in words:
            if len(current_line + word) < 60:
                current_line += word + " "
            else:
                if current_line:
                    criteria_lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            criteria_lines.append(current_line.strip())
        
        p.drawString(120, y, "Additional Criteria:")
        y -= 15
        for line in criteria_lines[:5]:  # Limit to 5 lines
            p.drawString(140, y, line)
            y -= 15
        if len(criteria_lines) > 5:
            p.drawString(140, y, "...")
            y -= 15
    
    if scholarship.requirements:
        # Convert requirements from short codes to descriptive names
        from credential_matcher import CredentialMatcher
        req_codes = [req.strip() for req in scholarship.requirements.split(',') if req.strip()]
        requirements_list = []
        for req_code in req_codes:
            if req_code in CredentialMatcher.REQUIREMENT_MAPPINGS:
                requirements_list.append(CredentialMatcher.REQUIREMENT_MAPPINGS[req_code][0])
            else:
                requirements_list.append(req_code)  # Keep custom requirements as-is
        
        if requirements_list:
            p.drawString(120, y, "Required Documents:")
            y -= 20
            for req in requirements_list:
                p.drawString(140, y, f"• {req}")
                y -= 18
                if y < 50:  # New page if needed
                    p.showPage()
                    y = 750
    
    if scholarship.contact_name or scholarship.contact_email or scholarship.contact_phone:
        y -= 10
        p.drawString(120, y, "Contact Information:")
        y -= 15
        if scholarship.contact_name:
            p.drawString(140, y, f"Name: {scholarship.contact_name}")
            y -= 15
        if scholarship.contact_email:
            p.drawString(140, y, f"Email: {scholarship.contact_email}")
            y -= 15
        if scholarship.contact_phone:
            p.drawString(140, y, f"Phone: {scholarship.contact_phone}")
            y -= 15
    
    # Application Statistics - use actual counts from database for accuracy
    y -= 30
    p.drawString(100, y, "APPLICATION STATISTICS:")
    y -= 20
    
    # Get actual counts from database for accuracy
    total_apps = ScholarshipApplication.query.filter_by(scholarship_id=scholarship.id).count()
    active_apps_count = ScholarshipApplication.query.filter_by(scholarship_id=scholarship.id, is_active=True).count()
    pending_count = ScholarshipApplication.query.filter_by(scholarship_id=scholarship.id, status='pending', is_active=True).count()
    approved_count = ScholarshipApplication.query.filter_by(scholarship_id=scholarship.id, status='approved', is_active=True).count()
    rejected_count = ScholarshipApplication.query.filter_by(scholarship_id=scholarship.id, status='rejected', is_active=True).count()
    
    p.drawString(120, y, f"Total Applications: {total_apps}")
    y -= 20
    p.drawString(120, y, f"Active Applications: {active_apps_count}")
    y -= 20
    p.drawString(120, y, f"Pending: {pending_count}")
    y -= 20
    p.drawString(120, y, f"Approved: {approved_count}")
    y -= 20
    p.drawString(120, y, f"Rejected: {rejected_count}")
    
    # List applicants (only active applications)
    active_apps = [app for app in scholarship.applications if app.is_active]
    if active_apps:
        y -= 40
        if y < 100:  # Check if we need a new page
            p.showPage()
            y = 750
        
        p.drawString(100, y, "APPLICANT LIST:")
        y -= 20
        
        for app in active_apps[:30]:  # Limit to 30 applicants per page
            student = User.query.get(app.user_id)
            name = student.get_full_name() if student else "Unknown"
            student_id = student.student_id if student and hasattr(student, 'student_id') else "N/A"
            p.drawString(120, y, f"- {name} (ID: {student_id}) - Status: {app.status.upper()}")
            y -= 20
            if y < 50:  # New page if needed
                p.showPage()
                y = 750
        
        if len(active_apps) > 30:
            p.drawString(120, y, f"... and {len(active_apps) - 30} more applicants")
            y -= 20
    else:
        y -= 40
        if y < 100:
            p.showPage()
            y = 750
        p.drawString(100, y, "APPLICANT LIST:")
        y -= 20
        p.drawString(120, y, "No active applications")

    p.showPage()
    p.save()
    
    buffer.seek(0)
    filename = f"scholarship_report_{scholarship.code}_{'archived' if scholarship.status == 'archived' else 'active'}.pdf"
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

# ==================== Staff Account Management Routes ====================

@provider_bp.route('/staff')
@login_required
def staff_management():
    """Staff Account Management page - Admin only"""
    require_provider_admin()
    
    # Get all staff members managed by this admin (using relationship)
    staff_members = current_user.get_staff_members()
    
    staff_data = []
    for staff in staff_members:
        staff_data.append({
            'id': staff.id,
            'first_name': staff.first_name,
            'last_name': staff.last_name,
            'email': staff.email,
            'organization': staff.organization or '',
            'scholarship_type': staff.scholarship_type or None,
            'is_active': staff.is_active,
            'created_at': staff.created_at.strftime('%Y-%m-%d') if staff.created_at else ''
        })
    
    return render_template('provider/staff.html', user=current_user, staff_members=staff_data)

@provider_bp.route('/api/scholarship-types', methods=['GET'])
@login_required
def get_scholarship_types():
    """Get all unique scholarship types for this provider - Admin only"""
    require_provider_admin()
    
    try:
        # Get all unique scholarship types from provider's scholarships
        types = db.session.execute(
            text("""
                SELECT DISTINCT type 
                FROM scholarships 
                WHERE provider_id = :provider_id 
                AND type IS NOT NULL 
                AND type != ''
                ORDER BY type
            """),
            {"provider_id": current_user.id}
        ).fetchall()
        
        type_list = [t[0] for t in types]
        return jsonify({'success': True, 'types': type_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/staff', methods=['POST'])
@login_required
def create_staff():
    """Create a new staff member - Admin only"""
    require_provider_admin()
    
    data = request.get_json()
    
    # Validation
    if not all([data.get('first_name'), data.get('last_name'), data.get('email'), data.get('password')]):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400
    
    # Check if email already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'success': False, 'error': 'Email already exists'}), 400
    
    # Validate scholarship_type if provided (must be from provider's scholarships)
    scholarship_type = data.get('scholarship_type', '').strip()
    if scholarship_type:
        # Verify the type exists in provider's scholarships
        type_exists = db.session.execute(
            text("""
                SELECT COUNT(*) 
                FROM scholarships 
                WHERE provider_id = :provider_id 
                AND type = :scholarship_type
            """),
            {"provider_id": current_user.id, "scholarship_type": scholarship_type}
        ).scalar() > 0
        
        if not type_exists:
            return jsonify({'success': False, 'error': 'Invalid scholarship type'}), 400
    
    try:
        # Use admin's organization automatically
        admin_organization = current_user.organization or ''
        
        new_staff = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            organization=admin_organization,
            role='provider_staff',
            managed_by=current_user.id,
            scholarship_type=scholarship_type if scholarship_type else None,
            is_active=True
        )
        new_staff.set_password(data['password'])
        
        db.session.add(new_staff)
        db.session.commit()
        
        return jsonify({'success': True, 'id': new_staff.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/staff/<int:staff_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def staff_detail(staff_id):
    """Get, Update, or Deactivate a staff member - Admin only"""
    require_provider_admin()
    
    staff = User.query.get_or_404(staff_id)
    
    # Verify staff belongs to this admin
    if staff.managed_by != current_user.id or staff.role != 'provider_staff':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'staff': {
                'id': staff.id,
                'first_name': staff.first_name,
                'last_name': staff.last_name,
                'email': staff.email,
                'organization': staff.organization or '',
                'scholarship_type': staff.scholarship_type or '',
                'is_active': staff.is_active
            }
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        try:
            if 'first_name' in data: staff.first_name = data['first_name']
            if 'last_name' in data: staff.last_name = data['last_name']
            if 'email' in data: 
                # Check if email is already taken by another user
                existing = User.query.filter_by(email=data['email']).first()
                if existing and existing.id != staff.id:
                    return jsonify({'success': False, 'error': 'Email already taken'}), 400
                staff.email = data['email']
            if 'organization' in data: staff.organization = data['organization']
            if 'scholarship_type' in data:
                scholarship_type = data['scholarship_type'].strip() if data['scholarship_type'] else None
                # Validate scholarship_type if provided
                if scholarship_type:
                    # Verify the type exists in provider's scholarships
                    type_exists = db.session.execute(
                        text("""
                            SELECT COUNT(*) 
                            FROM scholarships 
                            WHERE provider_id = :provider_id 
                            AND type = :scholarship_type
                        """),
                        {"provider_id": current_user.id, "scholarship_type": scholarship_type}
                    ).scalar() > 0
                    
                    if not type_exists:
                        return jsonify({'success': False, 'error': 'Invalid scholarship type'}), 400
                staff.scholarship_type = scholarship_type
            if 'password' in data and data['password']:
                staff.set_password(data['password'])
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        # Deactivate instead of delete
        try:
            staff.is_active = False
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/staff/<int:staff_id>/activate', methods=['POST'])
@login_required
def activate_staff(staff_id):
    """Activate a deactivated staff member - Admin only"""
    require_provider_admin()
    
    staff = User.query.get_or_404(staff_id)
    
    if staff.managed_by != current_user.id or staff.role != 'provider_staff':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        staff.is_active = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Reports & Analytics Routes ====================

@provider_bp.route('/reports')
@login_required
def reports():
    """Reports and analytics page - Admin only"""
    require_provider_admin()
    
    try:
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        
        provider_id = current_user.id
        
        # Get scholarships created by this provider
        scholarship_ids = db.session.execute(
            text("SELECT id FROM scholarships WHERE provider_id = :provider_id"),
            {"provider_id": provider_id}
        ).fetchall()
        scholarship_ids = [s[0] for s in scholarship_ids]
        
        if not scholarship_ids:
            # Return empty data if no scholarships
            return render_template('provider/reports.html', data={
                'totals': {'total_applications': 0},
                'top_scholarships': [],
                'status_counts': {'pending': 0, 'approved': 0, 'disapproved': 0}
            }, user=current_user)
        
        # Status counts from scholarship_applications table (only for this provider's scholarships)
        scholarship_ids_str = ','.join(map(str, scholarship_ids))
        status_row = db.session.execute(
            text(f"""
                SELECT 
                  SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                  SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved,
                  SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS disapproved,
                  COUNT(*) AS total
                FROM scholarship_applications
                WHERE scholarship_id IN ({scholarship_ids_str}) AND COALESCE(is_active,1) = 1
            """)
        ).fetchone() or (0,0,0,0)
        
        pending = int(status_row[0] or 0)
        approved = int(status_row[1] or 0)
        disapproved = int(status_row[2] or 0)
        total_applications = int(status_row[3] or 0)
        
        # Top scholarships by applications (only this provider's scholarships)
        rows = db.session.execute(
            text("""
                SELECT s.title, COUNT(sa.id) as apps
                FROM scholarship_applications sa
                JOIN scholarships s ON sa.scholarship_id = s.id
                WHERE s.provider_id = :provider_id AND COALESCE(sa.is_active,1) = 1
                GROUP BY s.id, s.title
                ORDER BY apps DESC, s.title ASC
                LIMIT 5
            """),
            {"provider_id": provider_id}
        ).fetchall()
        top_scholarships = [{'name': r[0], 'applications': int(r[1] or 0)} for r in rows]
        
        data = {
            'totals': {
                'total_applications': total_applications
            },
            'top_scholarships': top_scholarships,
            'status_counts': {
                'pending': pending,
                'approved': approved,
                'disapproved': disapproved
            }
        }
        return render_template('provider/reports.html', data=data, user=current_user)
    except Exception as e:
        flash('Failed to load reports data', 'error')
        return render_template('provider/reports.html', data={
            'totals': {'total_applications': 0},
            'top_scholarships': [],
            'status_counts': {'pending': 0, 'approved': 0, 'disapproved': 0}
        }, user=current_user)
