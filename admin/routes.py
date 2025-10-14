"""
Admin dashboard routes for Scholarsphere
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard"""
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('index'))
    
    # Get real-time statistics from database using raw SQLite
    import sqlite3
    import os
    
    db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
    total_students = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'provider'")
    total_providers = cursor.fetchone()[0]
    
    # Additional counts from scholarships/applications aggregates
    created_scholarships = 0
    pending_scholarships = 0
    accepted_applications = 0
    pending_applications = 0
    try:
        cursor.execute("SELECT COUNT(*) FROM scholarships")
        created_scholarships = cursor.fetchone()[0] or 0
    except Exception:
        created_scholarships = 0
    # Pending scholarships metric removed from dashboard UI
    try:
        # Aggregate application status columns if present on scholarships
        cursor.execute("SELECT IFNULL(SUM(approved_count),0), IFNULL(SUM(pending_count),0) FROM scholarships")
        row = cursor.fetchone() or (0, 0)
        accepted_applications = row[0] or 0
        pending_applications = row[1] or 0
    except Exception:
        accepted_applications = 0
        pending_applications = 0

    conn.close()

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
    
    # Get real users data from database using raw SQLite
    import sqlite3
    import os
    
    db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, first_name, last_name, email, role, created_at, student_id, COALESCE(is_active, 1) FROM users ORDER BY created_at DESC")
    users_result = cursor.fetchall()
    conn.close()
    
    # Create a simple class to mimic the User object
    class UserDict:
        def __init__(self, data):
            from datetime import datetime
            
            self.id = data[0]
            self.first_name = data[1]
            self.last_name = data[2]
            self.email = data[3]
            self.role = data[4]
            # Convert string to datetime object for strftime
            if data[5]:
                try:
                    self.created_at = datetime.fromisoformat(data[5].replace('Z', '+00:00'))
                except:
                    # If parsing fails, create a datetime from the string
                    self.created_at = datetime.strptime(data[5], '%Y-%m-%d %H:%M:%S.%f')
            else:
                self.created_at = datetime.now()
            # Student id if available
            try:
                self.student_id = data[6]
            except Exception:
                self.student_id = None
            self.course = None
            self.year_level = None
            try:
                self.is_active = bool(data[7])
            except Exception:
                self.is_active = True
            
        def get_full_name(self):
            return f"{self.first_name} {self.last_name}"
    
    users_data = []
    for user in users_result:
        user_obj = UserDict(user)
        users_data.append(user_obj)
    
    return render_template('admin/users.html', users=users_data)

@admin_bp.route('/providers')
@login_required
def providers():
    """Provider management page"""
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('index'))
    
    # Get all providers from database using raw SQLite
    import sqlite3
    import os
    
    db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, first_name, last_name, email, organization, created_at, COALESCE(is_active, 1) FROM users WHERE role = 'provider' ORDER BY created_at DESC")
    providers_result = cursor.fetchall()
    conn.close()
    
    # Create a simple class to mimic the Provider object
    class ProviderDict:
        def __init__(self, data):
            from datetime import datetime
            
            self.id = data[0]
            self.first_name = data[1]
            self.last_name = data[2]
            self.email = data[3]
            self.organization = data[4]
            # Convert string to datetime object for strftime
            if data[5]:
                try:
                    self.created_at = datetime.fromisoformat(data[5].replace('Z', '+00:00'))
                except:
                    # If parsing fails, create a datetime from the string
                    self.created_at = datetime.strptime(data[5], '%Y-%m-%d %H:%M:%S.%f')
            else:
                self.created_at = datetime.now()
            self.role = 'provider'
            try:
                self.is_active = bool(data[6])
            except Exception:
                self.is_active = True
            
        def get_full_name(self):
            return f"{self.first_name} {self.last_name}"
    
    providers_data = []
    for provider in providers_result:
        provider_obj = ProviderDict(provider)
        providers_data.append(provider_obj)
    
    return render_template('admin/providers.html', providers=providers_data)

@admin_bp.route('/scholarships')
@login_required
def scholarships():
    """Scholarship oversight page"""
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('index'))
    
    import sqlite3
    import os
    db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT s.id, s.code, s.title, s.deadline, s.created_at, s.applications_count, s.status, u.organization
        FROM scholarships s
        LEFT JOIN users u ON u.id = s.provider_id
        ORDER BY s.id ASC
        """
    )
    rows = cursor.fetchall()
    conn.close()

    def map_row(r):
        from datetime import datetime
        created = r[4]
        try:
            created_fmt = datetime.fromisoformat(created.replace('Z','+00:00')).strftime('%b %d, %Y') if created else ''
        except Exception:
            created_fmt = created
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
    """Reports and analytics page"""
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('index'))
    import sqlite3
    import os
    db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Total students
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='student'")
    total_students = cursor.fetchone()[0] or 0

    # Total applications aggregated from scholarships table (fallback 0 if not exists)
    total_applications = 0
    pending = approved = disapproved = 0
    try:
        cursor.execute("SELECT SUM(applications_count), SUM(pending_count), SUM(approved_count), SUM(disapproved_count) FROM scholarships")
        row = cursor.fetchone()
        total_applications = (row[0] or 0)
        pending = (row[1] or 0)
        approved = (row[2] or 0)
        disapproved = (row[3] or 0)
    except Exception:
        total_applications = 0

    # Breakdown by provider (top providers)
    top_providers = []
    try:
        cursor.execute(
            """
            SELECT IFNULL(u.organization,'—') as org, COUNT(s.id) as num_sch, IFNULL(SUM(s.applications_count),0) as apps
            FROM scholarships s
            LEFT JOIN users u ON u.id = s.provider_id
            GROUP BY org
            ORDER BY apps DESC
            LIMIT 5
            """
        )
        top_providers = [{'name': r[0], 'scholarships': r[1], 'applications': r[2]} for r in cursor.fetchall()]
    except Exception:
        top_providers = []

    conn.close()

    # Percent of students who applied online (approx via applications_count)
    applied_percent = round((total_applications / total_students) * 100, 2) if total_students else 0.0

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
        import sqlite3
        import os
        
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, first_name, last_name, email, role, created_at, organization, student_id FROM users WHERE id = ?", (user_id,))
        user_result = cursor.fetchone()
        conn.close()
        
        if not user_result:
            return jsonify({'error': 'User not found'}), 404
        
        user_data = {
            'id': user_result[0],
            'first_name': user_result[1],
            'last_name': user_result[2],
            'email': user_result[3],
            'role': user_result[4],
            'created_at': user_result[5],
            'organization': user_result[6],
            'student_id': user_result[7]
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

        # If organization provided, ensure it exists in providers list
        import sqlite3
        import os
        
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # If organization present, validate against providers
        if organization:
            cursor.execute("SELECT DISTINCT organization FROM users WHERE role = 'provider' AND organization = ?", (organization,))
            org_row = cursor.fetchone()
            if not org_row:
                conn.close()
                return jsonify({'success': False, 'error': 'Organization not found among providers'}), 400

        # Update user information
        cursor.execute("""
            UPDATE users 
            SET first_name = ?, last_name = ?, email = ?, organization = ?, student_id = ?, role = ?
            WHERE id = ?
        """, (
            first_name,
            last_name,
            email,
            organization,
            student_id,
            role,
            user_id
        ))
        
        conn.commit()
        conn.close()
        
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
        import sqlite3
        import os
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT organization FROM users WHERE role = 'provider' AND organization IS NOT NULL AND TRIM(organization) <> '' ORDER BY organization ASC")
        rows = cursor.fetchall()
        conn.close()
        orgs = [r[0] for r in rows]
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
        import sqlite3
        import os
        from werkzeug.security import generate_password_hash
        
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            conn.close()
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
        
        # Hash the password
        password_hash = generate_password_hash(password)
        
        # Update password
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        conn.commit()
        conn.close()
        
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
        import sqlite3
        import os
        
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Prevent self-deletion
        if user_id == current_user.id:
            conn.close()
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        # Delete user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        
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
        import sqlite3
        import os
        
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
        total_students = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'provider'")
        total_providers = cursor.fetchone()[0]
        
        # Aggregate dynamic counts
        created_scholarships = 0
        pending_scholarships = 0
        accepted_applications = 0
        pending_applications = 0
        try:
            cursor.execute("SELECT COUNT(*) FROM scholarships")
            created_scholarships = cursor.fetchone()[0] or 0
        except Exception:
            created_scholarships = 0
        # Pending scholarships metric removed from dashboard UI
        try:
            cursor.execute("SELECT IFNULL(SUM(approved_count),0), IFNULL(SUM(pending_count),0) FROM scholarships")
            row = cursor.fetchone() or (0, 0)
            accepted_applications = row[0] or 0
            pending_applications = row[1] or 0
        except Exception:
            accepted_applications = 0
            pending_applications = 0

        conn.close()

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

@admin_bp.route('/api/scholarships/<int:scholarship_id>/status', methods=['POST'])
@login_required
def update_scholarship_status(scholarship_id):
    """Update scholarship status: approved/suspended/archived"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    import sqlite3
    import os
    data = request.get_json() or {}
    status = (data.get('status') or '').lower()
    if status not in ['approved', 'suspended', 'archived']:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
    db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM scholarships WHERE id=?", (scholarship_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': 'Scholarship not found'}), 404
    cursor.execute("UPDATE scholarships SET status=? WHERE id=?", (status, scholarship_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@admin_bp.route('/api/create-provider', methods=['POST'])
@login_required
def create_provider_api():
    """Create new provider account"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from werkzeug.security import generate_password_hash
        import sqlite3
        import os
        
        data = request.get_json()
        
        # Validate required fields (username removed; email used for login)
        required_fields = ['firstName', 'lastName', 'email', 'organization', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (data['email'],))
        existing_user = cursor.fetchone()
        if existing_user:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Email already exists'
            }), 400
        
        # Hash password
        password_hash = generate_password_hash(data['password'])
        
        # Create new provider using raw SQLite
        cursor.execute("""
            INSERT INTO users (first_name, last_name, email, role, organization, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data['firstName'],
            data['lastName'],
            data['email'].lower(),
            'provider',
            data['organization'],
            password_hash,
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        conn.close()
        
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
        import sqlite3
        import os
        
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, first_name, last_name, email, organization, role, created_at, updated_at, COALESCE(is_active, 1) FROM users WHERE id = ? AND role = 'provider'", (provider_id,))
        provider_result = cursor.fetchone()
        conn.close()
        
        if not provider_result:
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        provider_data = {
            'id': provider_result[0],
            'first_name': provider_result[1],
            'last_name': provider_result[2],
            'email': provider_result[3],
            'organization': provider_result[4],
            'role': provider_result[5],
            'created_at': provider_result[6].isoformat() if provider_result[6] else None,
            'updated_at': provider_result[7].isoformat() if provider_result[7] else None,
            'is_active': bool(provider_result[8])
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
        import sqlite3
        import os
        
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if provider exists
        cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'provider'", (provider_id,))
        provider_result = cursor.fetchone()
        
        if not provider_result:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        # Prevent admin from deleting themselves
        if provider_result[0] == current_user.id:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Cannot delete your own account'
            }), 400
        
        # Delete provider using raw SQLite
        cursor.execute("DELETE FROM users WHERE id = ?", (provider_id,))
        conn.commit()
        conn.close()
        
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
        import sqlite3
        import os
        data = request.get_json() or {}
        is_active = bool(data.get('is_active'))

        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE id = ? AND role = 'provider'", (provider_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Provider not found'}), 404

        cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, provider_id))
        conn.commit()
        conn.close()

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
        import sqlite3
        import os
        data = request.get_json() or {}
        is_active = bool(data.get('is_active'))

        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'User not found'}), 404

        # Prevent admin from deactivating themselves
        if user_id == current_user.id and not is_active:
            conn.close()
            return jsonify({'success': False, 'error': 'Cannot deactivate your own account'}), 400

        # Update user active status
        cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, user_id))
        conn.commit()
        conn.close()

        action = 'activated' if is_active else 'deactivated'
        print(f"User {action} by admin {current_user.email}: ID {user_id} at {datetime.utcnow()}")

        return jsonify({
            'success': True,
            'message': f'User {action} successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
