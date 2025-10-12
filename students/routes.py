"""
Student dashboard routes for Scholarsphere
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

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
        db.text("SELECT COUNT(*) FROM credentials WHERE user_id = :user_id AND is_active = 1"),
        {"user_id": current_user.id}
    ).scalar()
    
    # Count actual awards uploaded by the student
    total_awards = db.session.execute(
        db.text("SELECT COUNT(*) FROM awards WHERE user_id = :user_id AND is_active = 1"),
        {"user_id": current_user.id}
    ).scalar()
    
    # Count actual scholarship applications
    total_applications = db.session.execute(
        db.text("SELECT COUNT(*) FROM scholarship_applications WHERE user_id = :user_id AND is_active = 1"),
        {"user_id": current_user.id}
    ).scalar()
    
    # Count approved applications
    approved_applications = db.session.execute(
        db.text("SELECT COUNT(*) FROM scholarship_applications WHERE user_id = :user_id AND status = 'approved' AND is_active = 1"),
        {"user_id": current_user.id}
    ).scalar()
    
    dashboard_data = {
        'user': current_user,
        'credentials': {
            'total': total_credentials
        },
        'awards': {
            'total': total_awards
        },
        'applications': {
            'total': total_applications,
            'approved': approved_applications
        },
        'deadlines': {
            'this_month': 0,  # Will be implemented when deadlines system is added
            'next_month': 0
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
        db.text("SELECT * FROM credentials WHERE user_id = :user_id AND is_active = 1 ORDER BY upload_date DESC"),
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
        
        credentials_list.append({
            'id': cred[0],
            'user_id': cred[1],
            'credential_type': cred[2],
            'file_name': cred[3],
            'file_path': cred[4],
            'file_size': cred[5],
            'status': cred[6],
            'upload_date': upload_date,
            'is_active': cred[8]
        })
    
    # Debug: Print credential data to identify the issue
    print("DEBUG: Credentials data:")
    for cred in credentials_list:
        print(f"  ID: {cred['id']}, Upload Date: {cred['upload_date']}, Type: {type(cred['upload_date'])}")
    
    return render_template('students/credentials.html', credentials=credentials_list, user=current_user)

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
        db.text("SELECT * FROM awards WHERE user_id = :user_id AND is_active = 1 ORDER BY award_date DESC, upload_date DESC"),
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
        db.text("""
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
        # Parse dates
        app_date = datetime.fromisoformat(app[4].replace('Z', '+00:00')) if app[4] else datetime.now()
        deadline = datetime.fromisoformat(app[6].replace('Z', '+00:00')) if app[6] else None
        
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
    
    available_scholarships = db.session.execute(
        db.text("""
            SELECT s.id, s.code, s.title, s.description, s.amount, s.deadline, s.requirements, u.organization
            FROM scholarships s
            LEFT JOIN users u ON s.provider_id = u.id
            WHERE s.status = 'active' AND s.is_active = 1
            ORDER BY s.deadline ASC
        """)
    ).fetchall()
    
    scholarships_data = []
    for scholarship in available_scholarships:
        # Check if user has already applied
        existing_application = db.session.execute(
            db.text(
                """
                SELECT status FROM scholarship_applications 
                WHERE user_id = :user_id AND scholarship_id = :scholarship_id AND is_active = 1
                ORDER BY id DESC LIMIT 1
                """
            ),
            {"user_id": current_user.id, "scholarship_id": scholarship[0]}
        ).fetchone()
        
        # Parse deadline
        deadline = None
        if scholarship[5]:
            try:
                deadline = datetime.fromisoformat(scholarship[5].replace('Z', '+00:00'))
            except:
                deadline = None
        
        scholarships_data.append({
            'id': scholarship[1] or f"SCH-{scholarship[0]:03d}",
            'title': scholarship[2],
            'description': scholarship[3] or 'No description available',
            'amount': scholarship[4] or 'Amount not specified',
            'deadline': deadline.strftime('%B %d, %Y') if deadline else 'No deadline',
            'requirements': scholarship[6] or 'No specific requirements',
            'provider': scholarship[7] or 'University of Cebu',
            'scholarship_id': scholarship[0],
            'has_applied': (existing_application is not None and (existing_application[0] or '').lower() != 'rejected'),
            'application_status': (existing_application[0] if existing_application else None),
            'can_apply_again': (existing_application is not None and (existing_application[0] or '').lower() == 'rejected')
        })
    
    return render_template('students/scholarships.html', scholarships=scholarships_data)

@students_bp.route('/apply-scholarship/<int:scholarship_id>', methods=['POST'])
@login_required
def apply_scholarship(scholarship_id):
    """Apply to a scholarship"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from flask import current_app
        from datetime import datetime
        db = current_app.extensions['sqlalchemy']
        
        # Check if scholarship exists and is active
        scholarship = db.session.execute(
            db.text("SELECT id, applications_count, pending_count FROM scholarships WHERE id = :id AND status = 'active' AND is_active = 1"),
            {"id": scholarship_id}
        ).fetchone()
        
        if not scholarship:
            return jsonify({'success': False, 'message': 'Scholarship not found or not available'}), 404
        
        # Check existing active application
        existing_application = db.session.execute(
            db.text(
                """
                SELECT id, status FROM scholarship_applications 
                WHERE user_id = :user_id AND scholarship_id = :scholarship_id AND is_active = 1
                ORDER BY id DESC LIMIT 1
                """
            ),
            {"user_id": current_user.id, "scholarship_id": scholarship_id}
        ).fetchone()

        if existing_application:
            existing_status = (existing_application[1] or '').lower()
            if existing_status != 'rejected':
                return jsonify({'success': False, 'message': 'You have already applied to this scholarship'}), 400
            # If rejected, deactivate previous record to allow re-apply
            db.session.execute(
                db.text(
                    "UPDATE scholarship_applications SET is_active = 0 WHERE id = :id"
                ),
                {"id": existing_application[0]}
            )
        
        # Create new application
        current_time = datetime.utcnow().isoformat()
        db.session.execute(
            db.text("""
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
        
        # Update scholarship application count
        db.session.execute(
            db.text(
                """
                UPDATE scholarships 
                SET applications_count = COALESCE(applications_count, 0) + 1, 
                    pending_count = COALESCE(pending_count, 0) + 1
                WHERE id = :id
                """
            ),
            {"id": scholarship_id}
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Application submitted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to submit application'}), 500

@students_bp.route('/withdraw-application/<int:application_id>', methods=['POST'])
@login_required
def withdraw_application(application_id):
    """Withdraw a scholarship application"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        
        # Find the application
        application = db.session.execute(
            db.text("SELECT id, status, scholarship_id FROM scholarship_applications WHERE id = :id AND user_id = :user_id AND is_active = 1"),
            {"id": application_id, "user_id": current_user.id}
        ).fetchone()
        
        if not application:
            return jsonify({'success': False, 'message': 'Application not found'}), 404
        
        if application[1] != 'pending':
            return jsonify({'success': False, 'message': 'Cannot withdraw application that has been reviewed'}), 400
        
        # Update application status
        db.session.execute(
            db.text("""
                UPDATE scholarship_applications 
                SET status = 'withdrawn', is_active = 0
                WHERE id = :id
            """),
            {"id": application_id}
        )
        
        # Update scholarship counts
        db.session.execute(
            db.text("""
                UPDATE scholarships 
                SET applications_count = applications_count - 1, pending_count = pending_count - 1
                WHERE id = :id
            """),
            {"id": application[2]}
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Application withdrawn successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to withdraw application'}), 500

# API endpoints for AJAX requests
@students_bp.route('/api/notifications')
@login_required
def get_notifications():
    """Get student notifications"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    # Mock notifications data
    notifications = [
        {
            'id': 1,
            'type': 'approved',
            'title': 'Scholarship Approved! 🎉',
            'message': 'Congratulations! Your Academic Excellence Scholarship application has been approved.',
            'time': '2 hours ago',
            'unread': True
        },
        {
            'id': 2,
            'type': 'schedule',
            'title': 'Interview Scheduled 📅',
            'message': 'Your interview for the Leadership Scholarship has been scheduled for March 20, 2024.',
            'time': '1 day ago',
            'unread': True
        },
        {
            'id': 3,
            'type': 'update',
            'title': 'Application Update Required 📝',
            'message': 'Your Computer Science Excellence application needs additional documents.',
            'time': '3 days ago',
            'unread': True
        }
    ]
    
    return jsonify(notifications)


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
        
        # Create upload directory if it doesn't exist
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save file
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Update user profile picture in database
        from app import db
        current_user.profile_picture = unique_filename
        current_user.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            
            # Return success response with image URL
            profile_picture_url = f"/static/uploads/profile_pictures/{unique_filename}"
            return jsonify({
                'success': True,
                'message': 'Photo uploaded successfully',
                'profile_picture_url': profile_picture_url
            })
            
        except Exception as e:
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
        from app import db, User
        existing_user = User.query.filter(
            User.email == email,
            User.id != current_user.id
        ).first()
        
        if existing_user:
            return jsonify({'success': False, 'message': 'Email already taken by another user'}), 400
        
        # Handle photo upload if provided
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '' and allowed_file(file.filename):
                # Generate unique filename
                filename = secure_filename(file.filename)
                file_extension = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4()}_{current_user.id}.{file_extension}"
                
                # Create upload directory if it doesn't exist
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                
                # Save file
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                
                # Update profile picture
                current_user.profile_picture = unique_filename
        
        # Update user information
        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.email = email
        current_user.birthday = datetime.strptime(birthday, '%Y-%m-%d').date()
        current_user.year_level = year_level
        current_user.course = course
        current_user.updated_at = datetime.utcnow()
        
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
            
            # Create upload directory if it doesn't exist
            os.makedirs(CREDENTIALS_FOLDER, exist_ok=True)
            
            # Save file
            file_path = os.path.join(CREDENTIALS_FOLDER, unique_filename)
            file.save(file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Save credential to database
            from app import db, Credential
            new_credential = Credential(
                user_id=current_user.id,
                credential_type=credential_type,
                file_name=filename,
                file_path=unique_filename,
                file_size=file_size,
                upload_date=datetime.utcnow()
            )
            
            db.session.add(new_credential)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Credential uploaded successfully'
            })
            
        else:
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to upload credential'}), 500

@students_bp.route('/view-credential/<int:credential_id>')
@login_required
def view_credential(credential_id):
    """View credential file"""
    if current_user.role != 'student':
        flash('Access denied. Student access required.', 'error')
        return redirect(url_for('index'))
    
    from app import db, Credential
    credential = Credential.query.filter_by(
        id=credential_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not credential:
        flash('Credential not found.', 'error')
        return redirect(url_for('students.credentials'))
    
    file_path = os.path.join(CREDENTIALS_FOLDER, credential.file_path)
    
    if not os.path.exists(file_path):
        flash('File not found.', 'error')
        return redirect(url_for('students.credentials'))
    
    # Determine content type based on file extension
    file_extension = credential.file_path.rsplit('.', 1)[1].lower()
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
            
            # Create upload directory if it doesn't exist
            os.makedirs(AWARDS_FOLDER, exist_ok=True)
            
            # Save file
            file_path = os.path.join(AWARDS_FOLDER, unique_filename)
            file.save(file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Save award to database
            from app import db, Award
            new_award = Award(
                user_id=current_user.id,
                award_type=award_type,
                award_title=award_title,
                academic_year=academic_year,
                award_date=datetime.strptime(award_date, '%Y-%m-%d').date(),
                file_name=filename,
                file_path=unique_filename,
                file_size=file_size,
                upload_date=datetime.utcnow()
            )
            
            db.session.add(new_award)
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
    
    from app import db, Award
    award = Award.query.filter_by(
        id=award_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not award:
        flash('Award not found.', 'error')
        return redirect(url_for('students.awards'))
    
    file_path = os.path.join(AWARDS_FOLDER, award.file_path)
    
    if not os.path.exists(file_path):
        flash('File not found.', 'error')
        return redirect(url_for('students.awards'))
    
    # Determine content type based on file extension
    file_extension = award.file_path.rsplit('.', 1)[1].lower()
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

@students_bp.route('/delete-award/<int:award_id>', methods=['DELETE'])
@login_required
def delete_award(award_id):
    """Delete award"""
    if current_user.role != 'student':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from app import db, Award
        award = Award.query.filter_by(
            id=award_id,
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not award:
            return jsonify({'success': False, 'message': 'Award not found'}), 404
        
        # Delete file from filesystem
        file_path = os.path.join(AWARDS_FOLDER, award.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Mark as inactive in database (soft delete)
        award.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Award deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to delete award'}), 500
