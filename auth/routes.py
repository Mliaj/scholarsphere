"""
Authentication routes for Scholarsphere
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, make_response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import text
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        # Redirect based on user role
        if current_user.role == 'student':
            return redirect(url_for('students.dashboard'))
        elif current_user.role == 'provider':
            return redirect(url_for('provider.dashboard'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        
        if not identifier or not password:
            flash('Please provide your ID/email and password.', 'error')
            return render_template('auth/login.html')
        
        # Check if identifier is student ID (8 digits) or email
        is_student_id = re.match(r'^\d{8}$', identifier)
        
        # Import database and models using current_app context
        from flask import current_app
        from flask_sqlalchemy import SQLAlchemy
        from flask_login import UserMixin
        from werkzeug.security import check_password_hash
        
        # Get the database instance from the current app
        db = current_app.extensions['sqlalchemy']
        
        # Define User class for this context
        class User(UserMixin):
            def __init__(self, **kwargs):
                # Set attributes manually to avoid property conflicts
                self.id = kwargs.get('id')
                self.first_name = kwargs.get('first_name')
                self.last_name = kwargs.get('last_name')
                self.email = kwargs.get('email')
                self.student_id = kwargs.get('student_id')
                self.birthday = kwargs.get('birthday')
                self.password_hash = kwargs.get('password_hash')
                self.role = kwargs.get('role')
                self.profile_picture = kwargs.get('profile_picture')
                self.year_level = kwargs.get('year_level')
                self.course = kwargs.get('course')
                self.organization = kwargs.get('organization')
                self.created_at = kwargs.get('created_at')
                self.updated_at = kwargs.get('updated_at')
                # Store is_active as _is_active to avoid conflict with UserMixin property
                self._is_active = kwargs.get('is_active', True)
            
            @property
            def is_active(self):
                return self._is_active
            
            def check_password(self, password):
                return check_password_hash(self.password_hash, password)
            
            def get_full_name(self):
                return f"{self.first_name} {self.last_name}"
        
        if is_student_id:
            result = db.session.execute(
                text("SELECT * FROM users WHERE student_id = :student_id"),
                {"student_id": identifier}
            ).fetchone()
        else:
            # Case-insensitive email lookup
            email_lookup = identifier.lower()
            result = db.session.execute(
                text("SELECT * FROM users WHERE LOWER(email) = :email"),
                {"email": email_lookup}
            ).fetchone()
        
        if result:
            user = User(
                id=result[0],
                first_name=result[1],
                last_name=result[2],
                email=result[3],
                student_id=result[4],
                birthday=result[5],
                password_hash=result[6],
                role=result[7],
                profile_picture=result[8],
                year_level=result[9],
                course=result[10],
                organization=result[11],
                created_at=result[12],
                updated_at=result[13],
                is_active=result[14]
            )
        else:
            user = None
        
        if user and user.check_password(password):
            remember = request.form.get('remember') == 'on'
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.get_full_name()}!', 'success')
            
            # Determine redirect URL
            if user.role == 'student':
                next_url = url_for('students.dashboard')
            elif user.role == 'provider':
                next_url = url_for('provider.dashboard')
            elif user.role == 'admin':
                next_url = url_for('admin.dashboard')
            else:
                next_url = url_for('index')
            
            # Handle cookie for remember username
            resp = make_response(redirect(next_url))
            if remember:
                # Set cookie for 30 days
                expire_date = datetime.now() + timedelta(days=30)
                resp.set_cookie('remembered_identifier', identifier, expires=expire_date)
            else:
                resp.set_cookie('remembered_identifier', '', expires=0)
            
            return resp
        else:
            flash('Invalid credentials.', 'error')
    
    # GET request: Check for remembered identifier
    remembered_identifier = request.cookies.get('remembered_identifier', '')
    return render_template('auth/login.html', remembered_identifier=remembered_identifier)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        first_name = request.form.get('firstName', '').strip()
        last_name = request.form.get('lastName', '').strip()
        email = request.form.get('email', '').strip()
        student_id = request.form.get('studentId', '').strip()
        birthday = request.form.get('birthday', '')
        password = request.form.get('password', '')
        repeat_password = request.form.get('repeatPassword', '')
        
        # Validation
        if not all([first_name, last_name, email, student_id, birthday, password, repeat_password]):
            flash('Please complete all fields.', 'error')
            return render_template('auth/signup.html')
        
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('Invalid email address.', 'error')
            return render_template('auth/signup.html')
        
        if not re.match(r'^\d{8}$', student_id):
            flash('Student ID must be exactly 8 digits.', 'error')
            return render_template('auth/signup.html')
        
        if password != repeat_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/signup.html')
        
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('auth/signup.html')
        
        # Check for existing user
        from flask import current_app
        from werkzeug.security import generate_password_hash
        
        db = current_app.extensions['sqlalchemy']
        
        existing_user = db.session.execute(
            text("SELECT * FROM users WHERE LOWER(email) = :email OR student_id = :student_id"),
            {"email": email.lower(), "student_id": student_id}
        ).fetchone()
        
        if existing_user:
            flash('An account with this email or student ID already exists.', 'error')
            return render_template('auth/signup.html')
        
        # Create new user
        try:
            # Hash the password
            password_hash = generate_password_hash(password)
            
            # Insert new user into database
            db.session.execute(
                text("""
                    INSERT INTO users (first_name, last_name, email, student_id, birthday, password_hash, role, created_at, is_active)
                    VALUES (:first_name, :last_name, :email, :student_id, :birthday, :password_hash, :role, :created_at, :is_active)
                """),
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email.lower(),
                    "student_id": student_id,
                    "birthday": datetime.strptime(birthday, '%Y-%m-%d').date(),
                    "password_hash": password_hash,
                    "role": 'student',
                    "created_at": datetime.utcnow(),
                    "is_active": True
                }
            )
            db.session.commit()
            
            flash('Account created successfully. Please sign in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Failed to create account. Please try again.', 'error')
            return render_template('auth/signup.html')
    
    return render_template('auth/signup.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))
