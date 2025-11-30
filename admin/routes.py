"""
Admin dashboard routes for Scholarsphere
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import text
from app import db, User, Scholarship, ScholarshipApplication

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard"""
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('index'))
    
    # Get real-time statistics from database using SQLAlchemy
    total_students = db.session.execute(
        text("SELECT COUNT(*) FROM users WHERE role = 'student'")
    ).scalar() or 0
    
    total_providers = db.session.execute(
        text("SELECT COUNT(*) FROM users WHERE role = 'provider'")
    ).scalar() or 0
    
    # Additional counts from scholarships/applications aggregates
    created_scholarships = 0
    pending_scholarships = 0
    accepted_applications = 0
    pending_applications = 0
    try:
        created_scholarships = db.session.execute(
            text("SELECT COUNT(*) FROM scholarships WHERE COALESCE(is_active, 1) = 1")
        ).scalar() or 0
    except Exception:
        created_scholarships = 0
    
    # Get real application counts from scholarship_applications table
    try:
        result = db.session.execute(text("""
            SELECT 
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved_count,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count
            FROM scholarship_applications 
            WHERE COALESCE(is_active, 1) = 1
        """))
        row = result.fetchone() or (0, 0)
        accepted_applications = row[0] or 0
        pending_applications = row[1] or 0
    except Exception:
        accepted_applications = 0
        pending_applications = 0

    dashboard_data = {
        'user': current_user,
        'stats': {
            'total_students': total_students,
            'total_providers': total_providers,
            'created_scholarships': created_scholarships,
            'accepted_applications': accepted_applications,
            'pending_applications': pending_applications
        },
        'recent_users': [
            {
                'id': 'USR-001',
                'name': 'John Doe',
                'email': 'cpareja073@gmail.com',
                'role': 'Student',
                'status': 'Active',
                'created_date': 'Jan 15, 2024'
            },
            {
                'id': 'USR-002',
                'name': 'University of Cebu',
                'email': 'uc.edu@scholarship.com',
                'role': 'Provider',
                'status': 'Active',
                'created_date': 'Jan 10, 2024'
            }
        ],
        'recent_applications': [
            {
                'id': 'APP-001',
                'student': 'John Doe',
                'scholarship': 'Academic Excellence',
                'provider': 'University of Cebu',
                'status': 'Under Review',
                'date_applied': 'March 10, 2024'
            }
        ]
    }
    
    return render_template('admin/dashboard.html', data=dashboard_data)

@admin_bp.route('/users')
@login_required
def users():
    """User management page"""
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('index'))
    
    # Get real users data from database using SQLAlchemy
    users_data = User.query.order_by(User.created_at.desc()).all()
    
    return render_template('admin/users.html', users=users_data)

@admin_bp.route('/providers')
@login_required
def providers():
    """Provider management page"""
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('index'))
    
    # Get all providers from database using SQLAlchemy
    providers_data = User.query.filter_by(role='provider').order_by(User.created_at.desc()).all()
    
    return render_template('admin/providers.html', providers=providers_data)

@admin_bp.route('/scholarships')
@login_required
def scholarships():
    """Scholarship oversight page"""
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('index'))
    
    # Get scholarships with application counts using SQLAlchemy
    result = db.session.execute(text("""
        SELECT s.id, s.code, s.title, s.deadline, s.created_at, 
               COALESCE(app_counts.app_count, 0) as applications_count, 
               s.status, u.organization
        FROM scholarships s
        LEFT JOIN users u ON u.id = s.provider_id
        LEFT JOIN (
            SELECT scholarship_id, COUNT(*) as app_count 
            FROM scholarship_applications 
            WHERE COALESCE(is_active, 1) = 1
            GROUP BY scholarship_id
        ) app_counts ON app_counts.scholarship_id = s.id
        WHERE COALESCE(s.is_active, 1) = 1
        ORDER BY s.id ASC
    """))
    rows = result.fetchall()

    def map_row(r):
        created = r[4]
        if created:
            if isinstance(created, str):
                try:
                    created_fmt = datetime.fromisoformat(created.replace('Z','+00:00')).strftime('%b %d, %Y')
                except Exception:
                    created_fmt = created
            else:
                created_fmt = created.strftime('%b %d, %Y') if hasattr(created, 'strftime') else str(created)
        else:
            created_fmt = ''
        return {
            'id': r[1] or f"SCH-{r[0]:03d}",
            'title': r[2],
            'deadline': r[3] or '',
            'created_date': created_fmt,
            'applications': r[5] or 0,
            'status': (r[6] or '').title(),
            'provider': r[7] or '—',
            'pk': r[0],
        }

    scholarships_data = [map_row(r) for r in rows]
    return render_template('admin/scholarships.html', scholarships=scholarships_data)

@admin_bp.route('/applications')
@login_required
def applications():
    """Application management page"""
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('index'))
    
    # Mock applications data
    applications_data = [
        {
            'id': 'APP-001',
            'student': 'John Doe',
            'scholarship': 'Academic Excellence',
            'provider': 'University of Cebu',
            'status': 'Under Review',
            'date_applied': 'March 10, 2024'
        }
    ]
    
    return render_template('admin/applications.html', applications=applications_data)

@admin_bp.route('/reports')
@login_required
def reports():
    """Reports and analytics page (real data)"""
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('index'))

    # Use SQLAlchemy session from current_app for consistency
    try:
        from flask import current_app
        db = current_app.extensions['sqlalchemy']

        # Total active students (match portal definition of active users)
        total_students = db.session.execute(
            text("SELECT COUNT(*) FROM users WHERE role='student' AND COALESCE(is_active,1) = 1")
        ).scalar() or 0

        # Status counts from scholarship_applications table (active records only)
        status_row = db.session.execute(
            text("""
                SELECT 
                  SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                  SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved,
                  SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS disapproved,
                  COUNT(*) AS total
                FROM scholarship_applications
                WHERE COALESCE(is_active,1) = 1
            """)
        ).fetchone() or (0,0,0,0)
        pending = int(status_row[0] or 0)
        approved = int(status_row[1] or 0)
        disapproved = int(status_row[2] or 0)
        total_applications = int(status_row[3] or 0)

        # Breakdown by provider (top providers by active applications)
        rows = db.session.execute(
            text(
                """
                SELECT IFNULL(NULLIF(TRIM(u.organization),''),'—') as org, COUNT(sa.id) as apps
                FROM scholarship_applications sa
                JOIN scholarships s ON sa.scholarship_id = s.id
                LEFT JOIN users u ON u.id = s.provider_id
                WHERE COALESCE(sa.is_active,1) = 1
                GROUP BY org
                ORDER BY apps DESC, org ASC
                LIMIT 5
                """
            )
        ).fetchall()
        top_providers = [{'name': r[0], 'applications': int(r[1] or 0), 'scholarships': None} for r in rows]

        # Percent of active students who have at least one active application
        if total_students:
            applicants_row = db.session.execute(
                text("SELECT COUNT(DISTINCT user_id) FROM scholarship_applications WHERE COALESCE(is_active,1) = 1")
            ).fetchone()
            applicants = int(applicants_row[0] or 0)
            applied_percent = round((applicants / total_students) * 100, 2)
        else:
            applied_percent = 0.0

        data = {
            'totals': {
                'total_students': total_students,
                'total_applications': total_applications,
                'applied_percent': applied_percent
            },
            'top_providers': top_providers,
            'status_counts': {
                'pending': pending,
                'approved': approved,
                'disapproved': disapproved
            }
        }
        return render_template('admin/reports.html', data=data)
    except Exception as e:
        # Fallback to existing behavior if needed
        flash('Failed to load reports data', 'error')
        return render_template('admin/reports.html', data={'totals': {'total_students':0,'total_applications':0,'applied_percent':0}, 'top_providers': [], 'status_counts': {'pending':0,'approved':0,'disapproved':0}})

# API endpoints for admin functions
@admin_bp.route('/api/create-user', methods=['POST'])
@login_required
def create_user():
    """Create new user"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    # Mock user creation
    flash('User created successfully!', 'success')
    return jsonify({'message': 'User created successfully'})

@admin_bp.route('/api/user/<int:user_id>', methods=['GET'])
@login_required
def get_user_details(user_id):
    """Get user details"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_data = {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': user.role,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'organization': user.organization,
            'student_id': user.student_id
        }
        
        return jsonify({'success': True, 'user': user_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/user/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """Update user information"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        # Basic server-side validation
        email = (data.get('email') or '').strip()
        first_name = (data.get('first_name') or '').strip()
        last_name = (data.get('last_name') or '').strip()
        role = (data.get('role') or '').strip()
        organization = (data.get('organization') or '').strip()
        student_id = (data.get('student_id') or '').strip()

        # Validate email format
        import re
        email_regex = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        if email and not re.match(email_regex, email):
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400

        # Validate student ID: if provided, must be exactly 8 digits
        if student_id and not re.fullmatch(r"\d{8}", student_id):
            return jsonify({'success': False, 'error': 'Student ID must be exactly 8 digits'}), 400

        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # If organization present, validate against providers
        if organization:
            org_exists = db.session.execute(
                text("SELECT DISTINCT organization FROM users WHERE role = 'provider' AND organization = :org"),
                {'org': organization}
            ).fetchone()
            if not org_exists:
                return jsonify({'success': False, 'error': 'Organization not found among providers'}), 400

        # Update user information
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.organization = organization
        user.student_id = student_id
        user.role = role
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/organizations', methods=['GET'])
@login_required
def list_organizations():
    """Return list of unique provider organizations for selection in UI"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    try:
        result = db.session.execute(text("""
            SELECT DISTINCT organization FROM users 
            WHERE role = 'provider' AND organization IS NOT NULL AND TRIM(organization) <> '' 
            ORDER BY organization ASC
        """))
        orgs = [r[0] for r in result.fetchall()]
        return jsonify({'success': True, 'organizations': orgs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/reset-password/<int:user_id>', methods=['POST'])
@login_required
def reset_user_password(user_id):
    """Reset user password"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        from werkzeug.security import generate_password_hash
        
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Determine option: support both 'password_type' and 'option' keys
        option = data.get('password_type') or data.get('option')
        
        # Debug logging
        print(f"Reset password request data: {data}")
        print(f"Selected option: {option}")
        
        # Generate or use provided password
        if option == 'random':
            import secrets
            import string
            password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        else:
            password = data.get('password')
            if not password:
                return jsonify({'success': False, 'error': 'Password is required'}), 400
        
        # Hash the password and update
        user.set_password(password)
        db.session.commit()
        
        if option == 'random':
            return jsonify({'success': True, 'new_password': password})
        else:
            return jsonify({'success': True, 'message': 'Password reset successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/delete-user/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Delete user"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Prevent self-deletion
        if user_id == current_user.id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/create-provider-old', methods=['POST'])
@login_required
def create_provider_old():
    """Create new provider"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    # Mock provider creation
    flash('Provider created successfully!', 'success')
    return jsonify({'message': 'Provider created successfully'})

@admin_bp.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """Get real-time statistics"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        total_students = db.session.execute(
            text("SELECT COUNT(*) FROM users WHERE role = 'student'")
        ).scalar() or 0
        
        total_providers = db.session.execute(
            text("SELECT COUNT(*) FROM users WHERE role = 'provider'")
        ).scalar() or 0
        
        # Aggregate dynamic counts
        created_scholarships = 0
        pending_scholarships = 0
        accepted_applications = 0
        pending_applications = 0
        try:
            created_scholarships = db.session.execute(
                text("SELECT COUNT(*) FROM scholarships WHERE COALESCE(is_active, 1) = 1")
            ).scalar() or 0
        except Exception:
            created_scholarships = 0
        
        # Get real application counts from scholarship_applications table
        try:
            result = db.session.execute(text("""
                SELECT 
                    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved_count,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count
                FROM scholarship_applications 
                WHERE COALESCE(is_active, 1) = 1
            """))
            row = result.fetchone() or (0, 0)
            accepted_applications = row[0] or 0
            pending_applications = row[1] or 0
        except Exception:
            accepted_applications = 0
            pending_applications = 0

        return jsonify({
            'success': True,
            'stats': {
                'total_students': total_students,
                'total_providers': total_providers,
                'created_scholarships': created_scholarships,
                'accepted_applications': accepted_applications,
                'pending_applications': pending_applications
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/export-data', methods=['POST'])
@login_required
def export_data():
    """Export data"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    data_type = request.form.get('type')
    
    # Mock export functionality
    flash(f'{data_type} data exported successfully!', 'success')
    return jsonify({'message': f'{data_type} data exported successfully'})

@admin_bp.route('/api/scholarships/<int:scholarship_id>', methods=['GET', 'POST'])
@login_required
def admin_scholarship_detail(scholarship_id):
    """Get or update scholarship details (admin)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    scholarship = Scholarship.query.get_or_404(scholarship_id)
    
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
                'type': scholarship.type or '',
                'level': scholarship.level or '',
                'eligibility': scholarship.eligibility or '',
                'slots': scholarship.slots or '',
                'contact_name': scholarship.contact_name or '',
                'contact_email': scholarship.contact_email or '',
                'contact_phone': scholarship.contact_phone or ''
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
            if 'type' in data: scholarship.type = data['type']
            if 'level' in data: scholarship.level = data['level']
            if 'eligibility' in data: scholarship.eligibility = data['eligibility']
            if 'slots' in data: scholarship.slots = int(data['slots']) if data['slots'] else None
            if 'contact_name' in data: scholarship.contact_name = data['contact_name']
            if 'contact_email' in data: scholarship.contact_email = data['contact_email']
            if 'contact_phone' in data: scholarship.contact_phone = data['contact_phone']
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/scholarships/<int:scholarship_id>/status', methods=['POST'])
@login_required
def update_scholarship_status(scholarship_id):
    """Update scholarship status: approved/suspended/archived"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    status = (data.get('status') or '').lower()
    if status not in ['approved', 'suspended', 'archived']:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
    
    scholarship = Scholarship.query.get(scholarship_id)
    if not scholarship:
        return jsonify({'success': False, 'error': 'Scholarship not found'}), 404
    
    scholarship.status = status
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/api/cleanup-mock', methods=['POST'])
@login_required
def cleanup_mock_scholarships():
    """Remove known mock/seed scholarships and related applications."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    try:
        # Find mock scholarships inserted by seed script
        scholarships = Scholarship.query.filter(
            (Scholarship.code == 'SCH-001') | (Scholarship.title.like('Academic Excellence%'))
        ).all()
        ids = [s.id for s in scholarships]
        removed_apps = 0
        removed_sch = 0
        if ids:
            # Delete related applications first
            removed_apps = ScholarshipApplication.query.filter(
                ScholarshipApplication.scholarship_id.in_(ids)
            ).delete(synchronize_session=False)
            # Delete scholarships
            removed_sch = Scholarship.query.filter(Scholarship.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'success': True, 'removed_scholarships': removed_sch, 'removed_applications': removed_apps})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/create-provider', methods=['POST'])
@login_required
def create_provider_api():
    """Create new provider account"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from werkzeug.security import generate_password_hash
        
        data = request.get_json()
        
        # Validate required fields (username removed; email used for login)
        required_fields = ['firstName', 'lastName', 'email', 'organization', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=data['email'].lower()).first()
        if existing_user:
            return jsonify({
                'success': False,
                'error': 'Email already exists'
            }), 400
        
        # Create new provider
        new_provider = User(
            first_name=data['firstName'],
            last_name=data['lastName'],
            email=data['email'].lower(),
            role='provider',
            organization=data['organization']
        )
        new_provider.set_password(data['password'])
        db.session.add(new_provider)
        db.session.commit()
        
        # Log the provider creation
        print(f"Provider created by admin {current_user.email}: {data['email']} at {datetime.utcnow()}")
        
        return jsonify({
            'success': True,
            'message': 'Provider created successfully',
            'password': data['password']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/provider/<int:provider_id>', methods=['GET'])
@login_required
def get_provider_details(provider_id):
    """Get detailed provider information"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        provider = User.query.filter_by(id=provider_id, role='provider').first()
        
        if not provider:
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        provider_data = {
            'id': provider.id,
            'first_name': provider.first_name,
            'last_name': provider.last_name,
            'email': provider.email,
            'organization': provider.organization,
            'role': provider.role,
            'created_at': provider.created_at.isoformat() if provider.created_at else None,
            'updated_at': provider.updated_at.isoformat() if provider.updated_at else None,
            'is_active': provider.is_active if provider.is_active is not None else True
        }
        
        return jsonify({
            'success': True,
            'provider': provider_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/api/delete-provider/<int:provider_id>', methods=['DELETE'])
@login_required
def delete_provider(provider_id):
    """Delete provider"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Check if provider exists
        provider = User.query.filter_by(id=provider_id, role='provider').first()
        
        if not provider:
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        # Prevent admin from deleting themselves
        if provider.id == current_user.id:
            return jsonify({
                'success': False,
                'error': 'Cannot delete your own account'
            }), 400
        
        # Delete provider
        db.session.delete(provider)
        db.session.commit()
        
        # Log the provider deletion
        print(f"Provider deleted by admin {current_user.email}: ID {provider_id} at {datetime.utcnow()}")
        
        return jsonify({
            'success': True,
            'message': 'Provider deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/provider/<int:provider_id>/active', methods=['POST'])
@login_required
def set_provider_active(provider_id):
    """Activate/deactivate provider account"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    try:
        data = request.get_json() or {}
        is_active = bool(data.get('is_active'))

        provider = User.query.filter_by(id=provider_id, role='provider').first()
        if not provider:
            return jsonify({'success': False, 'error': 'Provider not found'}), 404

        provider.is_active = is_active
        db.session.commit()

        return jsonify({'success': True, 'is_active': is_active})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/user/<int:user_id>/active', methods=['POST'])
@login_required
def set_user_active(user_id):
    """Activate/deactivate user account"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    try:
        data = request.get_json() or {}
        is_active = bool(data.get('is_active'))

        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        # Prevent admin from deactivating themselves
        if user_id == current_user.id and not is_active:
            return jsonify({'success': False, 'error': 'Cannot deactivate your own account'}), 400

        # Update user active status
        user.is_active = is_active
        db.session.commit()

        action = 'activated' if is_active else 'deactivated'
        print(f"User {action} by admin {current_user.email}: ID {user_id} at {datetime.utcnow()}")

        return jsonify({
            'success': True,
            'message': f'User {action} successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
