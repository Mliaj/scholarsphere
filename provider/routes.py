"""
Provider dashboard routes for Scholarsphere
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user

provider_bp = Blueprint('provider', __name__)

@provider_bp.route('/dashboard')
@login_required
def dashboard():
    """Provider dashboard"""
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))
    
    # Mock provider dashboard data
    dashboard_data = {
        'user': current_user,
        'stats': {
            'active_scholarships': 8,
            'draft_scholarships': 3,
            'total_applications': 156,
            'new_applications': 23,
            'pending_reviews': 45,
            'today_reviews': 12,
            'awarded_this_month': 28,
            'total_value': '₱2.1M'
        }
    }
    
    return render_template('provider/dashboard.html', data=dashboard_data)

@provider_bp.route('/scholarships')
@login_required
def scholarships():
    """Manage scholarships page"""
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))
    
    # Load from database
    import sqlite3
    import os
    from datetime import datetime
    db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, code, title, deadline, created_at, applications_count, status
        FROM scholarships
        WHERE provider_id = ?
        ORDER BY id ASC
        """,
        (current_user.id,)
    )
    rows = cursor.fetchall()
    conn.close()

    def fmt_date(s):
        if not s:
            return ''
        try:
            return datetime.fromisoformat(s.replace('Z','+00:00')).strftime('%b %d, %Y')
        except Exception:
            return s

    scholarships_data = [
        {
            'id': r[1] or f"SCH-{r[0]:03d}",
            'title': r[2],
            'deadline': fmt_date(r[3]),
            'created_date': fmt_date(r[4]),
            'applications': r[5] or 0,
            'status': (r[6] or 'draft').title()
        }
        for r in rows
    ]
    
    return render_template('provider/scholarships.html', scholarships=scholarships_data)

@provider_bp.route('/api/scholarships/<int:scholarship_id>/publish', methods=['POST'])
@login_required
def publish_scholarship(scholarship_id):
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403
    try:
        import sqlite3
        import os
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Ensure ownership
        cursor.execute("SELECT id FROM scholarships WHERE id=? AND provider_id=?", (scholarship_id, current_user.id))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Scholarship not found'}), 404
        cursor.execute("UPDATE scholarships SET status='approved' WHERE id=?", (scholarship_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/publish-by-code', methods=['POST'])
@login_required
def publish_by_code():
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    code = (data.get('code') or '').strip()
    if not code:
        return jsonify({'success': False, 'error': 'Code required'}), 400
    try:
        import sqlite3
        import os
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM scholarships WHERE code=? AND provider_id=?", (code, current_user.id))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Scholarship not found'}), 404
        cursor.execute("UPDATE scholarships SET status='approved' WHERE id=?", (row[0],))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/applications')
@login_required
def applications():
    """Student applications page"""
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))
    
    # Mock applications data
    applications_data = [
        {
            'id': 'APP-001',
            'student_name': 'John Doe',
            'scholarship': 'Academic Excellence',
            'date_applied': 'March 10, 2024',
            'status': 'Under Review',
            'documents': 'Complete'
        },
        {
            'id': 'APP-002',
            'student_name': 'Jane Smith',
            'scholarship': 'Leadership Scholarship',
            'date_applied': 'March 9, 2024',
            'status': 'Approved',
            'documents': 'Complete'
        },
        {
            'id': 'APP-003',
            'student_name': 'Mike Johnson',
            'scholarship': 'Academic Excellence',
            'date_applied': 'March 8, 2024',
            'status': 'Pending',
            'documents': 'Complete'
        },
        {
            'id': 'APP-004',
            'student_name': 'Sarah Wilson',
            'scholarship': 'Leadership Scholarship',
            'date_applied': 'March 7, 2024',
            'status': 'Rejected',
            'documents': 'Complete'
        }
    ]
    
    return render_template('provider/applications.html', applications=applications_data)

@provider_bp.route('/schedules')
@login_required
def schedules():
    """Scholarship schedules page"""
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))
    
    # Mock schedules data
    schedules_data = [
        {
            'title': 'Interview Schedule - Academic Excellence',
            'date': 'March 20, 2024',
            'time': '9:00 AM - 5:00 PM',
            'location': 'UC Main Campus, Room 301',
            'description': 'Final interview for shortlisted candidates'
        },
        {
            'title': 'Orientation - Leadership Scholarship',
            'date': 'March 25, 2024',
            'time': '2:00 PM - 4:00 PM',
            'location': 'UC Auditorium',
            'description': 'Welcome orientation for approved scholars'
        }
    ]
    
    return render_template('provider/schedules.html', schedules=schedules_data)

@provider_bp.route('/documents')
@login_required
def documents():
    """Application documents page"""
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))
    
    # Mock documents data
    documents_data = [
        {
            'application_id': 'APP-001',
            'student_name': 'John Doe',
            'documents_submitted': 'Transcript, Enrollment Cert, Valid ID, Photo',
            'completion_status': 'Complete',
            'review_status': 'Under Review'
        },
        {
            'application_id': 'APP-002',
            'student_name': 'Jane Smith',
            'documents_submitted': 'All Required Documents',
            'completion_status': 'Complete',
            'review_status': 'Approved'
        }
    ]
    
    return render_template('provider/documents.html', documents=documents_data)

@provider_bp.route('/remarks')
@login_required
def remarks():
    """Review remarks page"""
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))
    
    # Mock remarks data
    remarks_data = [
        {
            'application_id': 'APP-001',
            'student_name': 'John Doe',
            'status': 'Under Review',
            'reviewer': 'Dr. Maria Santos',
            'date': 'March 12, 2024',
            'message': 'Strong academic performance. Need to verify financial need documents. Schedule interview for final assessment.'
        },
        {
            'application_id': 'APP-002',
            'student_name': 'Jane Smith',
            'status': 'Approved',
            'reviewer': 'Dr. Juan Dela Cruz',
            'date': 'March 11, 2024',
            'message': 'Excellent leadership record and academic standing. All requirements met. Approved for Leadership Scholarship.'
        }
    ]
    
    return render_template('provider/remarks.html', remarks=remarks_data)

@provider_bp.route('/profile')
@login_required
def profile():
    """Organization profile page"""
    if current_user.role != 'provider':
        flash('Access denied. Provider access required.', 'error')
        return redirect(url_for('index'))
    
    # Mock profile data
    profile_data = {
        'provider_id': 'PRV-001',
        'organization_name': 'University of Cebu Main Campus',
        'contact_number': '+63 32 255 7777',
        'email': 'scholarships@uc.edu.ph',
        'address': 'Sanciangko Street, Cebu City, Cebu, Philippines 6000',
        'organization_type': 'Educational Institution',
        'website': 'https://www.uc.edu.ph',
        'description': 'The University of Cebu is a premier educational institution committed to academic excellence and community development. We provide various scholarship programs to support deserving students in their educational journey.'
    }
    
    return render_template('provider/profile.html', profile=profile_data)

# API endpoints for provider functions
@provider_bp.route('/api/create-scholarship', methods=['POST'])
@login_required
def create_scholarship():
    """Create new scholarship"""
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    # Validate required fields
    required_fields = ['code', 'title', 'deadline', 'requirements']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'{field} is required'}), 400
    
    try:
        import sqlite3
        import os
        from datetime import datetime
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if code already exists
        cursor.execute("SELECT id FROM scholarships WHERE code = ?", (data['code'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Scholarship code already exists'}), 400
        
        # Insert new scholarship
        cursor.execute("""
            INSERT INTO scholarships (code, title, deadline, requirements, provider_id, status, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, 'draft', ?, 1)
        """, (
            data['code'],
            data['title'],
            data['deadline'],
            data['requirements'],
            current_user.id,
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Scholarship created successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/scholarship/<scholarship_id>', methods=['GET'])
@login_required
def get_scholarship(scholarship_id):
    """Get scholarship details"""
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        import sqlite3
        import os
        from datetime import datetime
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get scholarship by code (since we're using code as ID in the frontend)
        cursor.execute("""
            SELECT id, code, title, deadline, requirements, status, applications_count, created_at
            FROM scholarships
            WHERE code = ? AND provider_id = ?
        """, (scholarship_id, current_user.id))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'success': False, 'error': 'Scholarship not found'}), 404
        
        def fmt_date(s):
            if not s:
                return ''
            try:
                return datetime.fromisoformat(s.replace('Z','+00:00')).strftime('%Y-%m-%d')
            except Exception:
                return s
        
        scholarship = {
            'id': row[0],
            'code': row[1],
            'title': row[2],
            'deadline': fmt_date(row[3]),
            'requirements': row[4] or '',
            'status': (row[5] or 'draft').title(),
            'applications': row[6] or 0,
            'created_date': fmt_date(row[7])
        }
        
        return jsonify({'success': True, 'scholarship': scholarship})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/scholarship/<scholarship_id>', methods=['PUT'])
@login_required
def update_scholarship(scholarship_id):
    """Update scholarship"""
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    # Validate required fields
    required_fields = ['code', 'title', 'deadline', 'requirements']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'{field} is required'}), 400
    
    try:
        import sqlite3
        import os
        from datetime import datetime
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if scholarship exists and belongs to current provider
        cursor.execute("SELECT id FROM scholarships WHERE code = ? AND provider_id = ?", (scholarship_id, current_user.id))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Scholarship not found'}), 404
        
        # Check if new code already exists (if code is being changed)
        if data['code'] != scholarship_id:
            cursor.execute("SELECT id FROM scholarships WHERE code = ? AND code != ?", (data['code'], scholarship_id))
            if cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'error': 'Scholarship code already exists'}), 400
        
        # Update scholarship
        cursor.execute("""
            UPDATE scholarships 
            SET code = ?, title = ?, deadline = ?, requirements = ?, updated_at = ?
            WHERE code = ? AND provider_id = ?
        """, (
            data['code'],
            data['title'],
            data['deadline'],
            data['requirements'],
            datetime.utcnow().isoformat(),
            scholarship_id,
            current_user.id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Scholarship updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/scholarship/<scholarship_id>', methods=['DELETE'])
@login_required
def delete_scholarship(scholarship_id):
    """Delete scholarship"""
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        import sqlite3
        import os
        db_path = os.path.join(current_app.instance_path, 'scholarsphere.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if scholarship exists and belongs to current provider
        cursor.execute("SELECT id FROM scholarships WHERE code = ? AND provider_id = ?", (scholarship_id, current_user.id))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Scholarship not found'}), 404
        
        # Delete scholarship
        cursor.execute("DELETE FROM scholarships WHERE code = ? AND provider_id = ?", (scholarship_id, current_user.id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Scholarship deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@provider_bp.route('/api/approve-application', methods=['POST'])
@login_required
def approve_application():
    """Approve application"""
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403
    
    application_id = request.form.get('application_id')
    
    # Mock approval functionality
    flash(f'Application {application_id} approved successfully!', 'success')
    return jsonify({'message': f'Application {application_id} approved successfully'})

@provider_bp.route('/api/reject-application', methods=['POST'])
@login_required
def reject_application():
    """Reject application"""
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403
    
    application_id = request.form.get('application_id')
    
    # Mock rejection functionality
    flash(f'Application {application_id} rejected.', 'info')
    return jsonify({'message': f'Application {application_id} rejected'})

@provider_bp.route('/api/add-remarks', methods=['POST'])
@login_required
def add_remarks():
    """Add application remarks"""
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403
    
    # Mock remarks addition
    flash('Review remarks submitted successfully!', 'success')
    return jsonify({'message': 'Review remarks submitted successfully'})

@provider_bp.route('/api/create-schedule', methods=['POST'])
@login_required
def create_schedule():
    """Create scholarship schedule"""
    if current_user.role != 'provider':
        return jsonify({'error': 'Access denied'}), 403
    
    # Mock schedule creation
    flash('Schedule created successfully!', 'success')
    return jsonify({'message': 'Schedule created successfully'})
