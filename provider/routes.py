from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db, User, Scholarship, ScholarshipApplication, Credential, Schedule, Notification, ScholarshipApplicationFile
from email_utils import send_email
from datetime import datetime # Import datetime here

provider_bp = Blueprint('provider', __name__)

@provider_bp.route('/dashboard')
@login_required
def dashboard():
    """Provider dashboard"""
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))
    
    # Calculate dashboard stats
    active_scholarships = Scholarship.query.filter(
        Scholarship.provider_id == current_user.id,
        Scholarship.status.in_(['active', 'approved'])
    ).count()
    draft_scholarships = Scholarship.query.filter_by(provider_id=current_user.id, status='draft').count()
    
    scholarships = Scholarship.query.filter_by(provider_id=current_user.id).all()
    scholarship_ids = [s.id for s in scholarships]
    
    total_applications = ScholarshipApplication.query.filter(
        ScholarshipApplication.scholarship_id.in_(scholarship_ids)
    ).count() if scholarship_ids else 0
    
    pending_reviews = ScholarshipApplication.query.filter(
        ScholarshipApplication.scholarship_id.in_(scholarship_ids),
        ScholarshipApplication.status == 'pending'
    ).count() if scholarship_ids else 0
    
    # Prepare data dictionary
    data = {
        'stats': {
            'active_scholarships': active_scholarships,
            'draft_scholarships': draft_scholarships,
            'total_applications': total_applications,
            'new_applications': 0, # Mock for now
            'pending_reviews': pending_reviews,
            'today_reviews': 0 # Mock for now
        }
    }
    
    return render_template('provider/dashboard.html', user=current_user, data=data)

@provider_bp.route('/scholarships')
@login_required
def scholarships():
    """Provider scholarships page"""
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))

    all_scholarships = Scholarship.query.filter_by(provider_id=current_user.id).all()
    
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
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))

    scholarships = Scholarship.query.filter_by(provider_id=current_user.id).all()
    
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
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))
    
    # Get applications to list for scheduling
    scholarships = Scholarship.query.filter_by(provider_id=current_user.id).all()
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
            'date_applied': app.application_date.strftime('%Y-%m-%d')
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
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))

    scholarships = Scholarship.query.filter_by(provider_id=current_user.id).all()
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
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))
        
    return render_template('provider/profile.html', user=current_user, profile=current_user)

from datetime import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import make_response # make_response is already imported in the file

@provider_bp.route('/generate_report_pdf')
@login_required
def generate_report_pdf():
    """Generates a PDF report for the provider"""
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))

    # Create a file-like buffer to receive PDF data.
    buffer = io.BytesIO()
    
    # Create the PDF object, using the buffer as its "file."
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Draw things on the PDF. Here's where the PDF generation happens.
    p.drawString(100, 750, f"Provider Report for {current_user.organization or current_user.get_full_name()}")
    p.drawString(100, 730, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p.drawString(100, 710, "--------------------------------------------------")
    
    # Add some dummy data for now
    p.drawString(100, 690, "Summary of Activities:")
    p.drawString(120, 670, "- Total Scholarships: N/A")
    p.drawString(120, 650, "- Total Applications: N/A")

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
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    action = data.get('action')

    application = ScholarshipApplication.query.get_or_404(application_id)
    scholarship = Scholarship.query.get_or_404(application.scholarship_id)

    if scholarship.provider_id != current_user.id:
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
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid action'}), 400

@provider_bp.route('/api/announcement/scholarship/<int:scholarship_id>', methods=['POST'])
@login_required
def send_scholarship_announcement(scholarship_id):
    """Send announcement to all applicants of a scholarship"""
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    message = data.get('message')
    
    scholarship = Scholarship.query.get_or_404(scholarship_id)
    if scholarship.provider_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    applications = ScholarshipApplication.query.filter_by(scholarship_id=scholarship_id).all()
    students = [User.query.get(app.user_id) for app in applications]

    for student in students:
        if student:
            send_email(
                student.email,
                f'Announcement for {scholarship.title}',
                'email/new_announcement.html',
                student_name=student.get_full_name(),
                announcement_title=f'Announcement for {scholarship.title}',
                announcement_message=message
            )
    
    return jsonify({'success': True, 'recipient_count': len(students), 'scholarship': scholarship.title})

@provider_bp.route('/api/application/<int:application_id>/announcement', methods=['POST'])
@login_required
def send_application_announcement(application_id):
    """Send announcement to a single applicant"""
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    message = data.get('message')

    application = ScholarshipApplication.query.get_or_404(application_id)
    scholarship = Scholarship.query.get_or_404(application.scholarship_id)

    if scholarship.provider_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403

    student = User.query.get(application.user_id)
    if student:
        send_email(
            student.email,
            f'Announcement for {scholarship.title}',
            'email/new_announcement.html',
            student_name=student.get_full_name(),
            announcement_title=f'Announcement for {scholarship.title}',
            announcement_message=message
        )

    return jsonify({'success': True})

@provider_bp.route('/api/application/<int:application_id>/schedule', methods=['POST'])
@login_required
def create_schedule(application_id):
    """Create a schedule for an application"""
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()
    schedule_date = data.get('schedule_date')
    schedule_time = data.get('schedule_time')
    location = data.get('location')
    notes = data.get('notes')

    application = ScholarshipApplication.query.get_or_404(application_id)
    scholarship = Scholarship.query.get_or_404(application.scholarship_id)

    if scholarship.provider_id != current_user.id:
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
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403
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
        application = ScholarshipApplication.query.join(Scholarship).filter(
            Scholarship.provider_id == current_user.id,
            ScholarshipApplication.user_id == credential.user_id
        ).first()

        if not application:
            return jsonify({'success': False, 'error': 'Access to this credential is not authorized'}), 403

        credential.status = action
        db.session.commit()

        # Send email notification
        student = User.query.get(credential.user_id)
        if student:
            send_email(
                student.email,
                f'Your Document {credential.credential_type} has been {action}d',
                'email/document_status.html',
                student_name=student.get_full_name(),
                document_name=credential.credential_type,
                new_status=action.capitalize()
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
    if current_user.role != 'provider':
        return jsonify([])
    
    scholarships = Scholarship.query.filter_by(provider_id=current_user.id).all()
    data = []
    for s in scholarships:
        data.append({
            'id': s.id,
            'title': s.title,
            'status': s.status,
            'applications_count': s.applications.count(), # Use dynamic count
            'deadline': s.deadline.strftime('%Y-%m-%d') if s.deadline else None,
            'created_at': s.created_at.strftime('%Y-%m-%d')
        })
    return jsonify(data)

@provider_bp.route('/api/applications/list')
@login_required
def api_applications_list():
    """Get list of applications for dashboard"""
    if current_user.role != 'provider':
        return jsonify([])

    scholarships = Scholarship.query.filter_by(provider_id=current_user.id).all()
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

@provider_bp.route('/api/announcements/history')
@login_required
def api_announcements_history():
    """Get history of sent announcements (mock data for now or query notifications)"""
    if current_user.role != 'provider':
        return jsonify([])
    # Ideally, we would query a 'SentNotifications' table or similar. 
    # For now, return an empty list or basic mock to prevent 404.
    return jsonify([])

@provider_bp.route('/api/scholarship/<int:id>/publish', methods=['POST'])
@login_required
def api_publish_scholarship(id):
    """Publish a scholarship by its ID"""
    if current_user.role != 'provider':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    scholarship = Scholarship.query.get_or_404(id)
    
    if scholarship.provider_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    scholarship.status = 'approved'
    db.session.commit()
    
    return jsonify({'success': True})

@provider_bp.route('/api/create-scholarship', methods=['POST'])
@login_required
def api_create_scholarship():
    """Create a new scholarship"""
    if current_user.role != 'provider':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    
    # Basic Validation
    if not data.get('title') or not data.get('code'):
        return jsonify({'success': False, 'error': 'Title and Code are required'}), 400
        
    try:
        # Check for duplicate code
        if Scholarship.query.filter_by(code=data['code']).first():
            return jsonify({'success': False, 'error': 'Scholarship code already exists'}), 400

        new_scholarship = Scholarship(
            provider_id=current_user.id,
            title=data['title'],
            code=data['code'],
            description=data.get('description', ''),
            amount=data.get('amount', ''),
            status='draft', # Default to draft
            requirements=data.get('requirements', ''),
            # Parse deadline if provided
            deadline=datetime.strptime(data['deadline'], '%Y-%m-%d').date() if data.get('deadline') else None
        )
        
        db.session.add(new_scholarship)
        db.session.commit()
        
        return jsonify({'success': True, 'id': new_scholarship.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/scholarship/<int:id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_scholarship_detail(id):
    """Get, Update, or Archive a scholarship"""
    if current_user.role != 'provider':
        return jsonify({'error': 'Unauthorized'}), 403
        
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
                'applications_count': scholarship.applications.count()
            }
        })
        
    elif request.method == 'POST':
        data = request.get_json()
        try:
            if 'title' in data: scholarship.title = data['title']
            if 'description' in data: scholarship.description = data['description']
            if 'amount' in data: scholarship.amount = data['amount']
            if 'requirements' in data: scholarship.requirements = data['requirements']
            if 'deadline' in data and data['deadline']:
                scholarship.deadline = datetime.strptime(data['deadline'], '%Y-%m-%d').date()
            if 'status' in data: scholarship.status = data['status']
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            scholarship.status = 'archived'
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/scholarship/<int:id>/restore', methods=['POST'])
@login_required
def api_scholarship_restore(id):
    """Restore an archived scholarship"""
    if current_user.role != 'provider':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    scholarship = Scholarship.query.get_or_404(id)
    
    if scholarship.provider_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    try:
        scholarship.status = 'draft'
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/scholarship/<int:id>/permanent-delete', methods=['DELETE'])
@login_required
def api_scholarship_permanent_delete(id):
    """Permanently delete a scholarship"""
    if current_user.role != 'provider':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
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
    if current_user.role != 'provider':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    application = ScholarshipApplication.query.get_or_404(id)
    scholarship = Scholarship.query.get(application.scholarship_id)
    
    if not scholarship:
        return jsonify({'success': False, 'error': 'Scholarship not found'}), 404
    
    if scholarship.provider_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
    student = User.query.get(application.user_id)
    
    # Fetch only the files linked to this specific application
    application_files = ScholarshipApplicationFile.query.filter_by(application_id=application.id).all()
    
    cred_list = []
    for app_file in application_files:
        cred = app_file.credential
        if cred and cred.is_active:
            cred_list.append({
                'id': cred.id,
                'requirement_type': app_file.requirement_type,
                'file_name': cred.file_name,
                'file_path': cred.file_path,
                'status': cred.status
            })
        
    return jsonify({
        'success': True,
        'application': {
            'id': application.id,
            'student_name': student.get_full_name() if student else 'Unknown',
            'student_email': student.email if student else '',
            'student_id': student.student_id if student else '',
            'scholarship_title': scholarship.title,
            'date_applied': application.application_date.strftime('%Y-%m-%d'),
            'status': application.status
        },
        'credentials': cred_list
    })

@provider_bp.route('/api/scholarship/<int:id>/report-pdf')
@login_required
def api_scholarship_report_pdf(id):
    """Download PDF report for a specific scholarship"""
    if current_user.role != 'provider':
        return redirect(url_for('index'))

    scholarship = Scholarship.query.get_or_404(id)
    if scholarship.provider_id != current_user.id:
        flash('Unauthorized', 'error')
        return redirect(url_for('provider.scholarships'))

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.drawString(100, 750, f"Scholarship Report: {scholarship.title}")
    p.drawString(100, 730, f"Code: {scholarship.code}")
    p.drawString(100, 710, f"Generated: {datetime.now().strftime('%Y-%m-%d')}")
    p.drawString(100, 690, "-" * 50)
    
    y = 660
    p.drawString(100, y, f"Status: {scholarship.status}")
    y -= 20
    p.drawString(100, y, f"Applicants: {scholarship.applications.count()}")
    
    # List applicants
    y -= 40
    p.drawString(100, y, "Applicant List:")
    y -= 20
    
    for app in scholarship.applications:
        student = User.query.get(app.user_id)
        name = student.get_full_name() if student else "Unknown"
        p.drawString(120, y, f"- {name} ({app.status})")
        y -= 20
        if y < 50: # New page if needed
            p.showPage()
            y = 750

    p.showPage()
    p.save()
    
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=report_{scholarship.code}.pdf'
    return response
