#!/usr/bin/env python3
"""
Scholarsphere - University of Cebu Scholarship Portal
Main Flask Application
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///scholarsphere.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# User model
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    student_id = db.Column(db.String(8), unique=True)
    birthday = db.Column(db.Date)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('student', 'provider', 'admin'), nullable=False, default='student')
    profile_picture = db.Column(db.String(255), nullable=True)
    year_level = db.Column(db.String(20), nullable=True)  # 1st year, 2nd year, 3rd year, 4th year
    course = db.Column(db.String(50), nullable=True)  # BSIT, BSCS, BSCE, etc.
    organization = db.Column(db.String(255), nullable=True)  # For providers
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

# Award model for storing student achievements
class Award(db.Model):
    __tablename__ = 'awards'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    award_type = db.Column(db.String(100), nullable=False)  # e.g., 'Certificate', 'Participation', 'Deadlist', etc.
    award_title = db.Column(db.String(255), nullable=False)  # Title of the award
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # File size in bytes
    academic_year = db.Column(db.String(20), nullable=True)  # e.g., '1st Year', '2nd Year', etc.
    award_date = db.Column(db.Date, nullable=True)  # Date when award was received
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    user = db.relationship('User', backref='awards')

# Credential model for storing student documents
class Credential(db.Model):
    __tablename__ = 'credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    credential_type = db.Column(db.String(100), nullable=False)  # e.g., 'Transcript', 'Certificate of Enrollment', etc.
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # File size in bytes
    status = db.Column(db.String(20), default='uploaded')  # uploaded, pending_review, approved, rejected
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    user = db.relationship('User', backref='credentials')

# Scholarship model
class Scholarship(db.Model):
    __tablename__ = 'scholarships'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='draft')  # draft, approved, active, closed
    deadline = db.Column(db.Date, nullable=True)
    amount = db.Column(db.String(100), nullable=True)  # e.g., "₱50,000 per semester"
    requirements = db.Column(db.Text, nullable=True)
    applications_count = db.Column(db.Integer, nullable=False, default=0)
    pending_count = db.Column(db.Integer, nullable=False, default=0)
    approved_count = db.Column(db.Integer, nullable=False, default=0)
    disapproved_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # Relationships
    provider = db.relationship('User', backref='scholarships')
    applications = db.relationship('ScholarshipApplication', backref='scholarship', lazy='dynamic')

# Scholarship Application model
class ScholarshipApplication(db.Model):
    __tablename__ = 'scholarship_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scholarship_id = db.Column(db.Integer, db.ForeignKey('scholarships.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected, withdrawn
    application_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # admin who reviewed
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='scholarship_applications')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_applications')
    
    # Ensure one user can only apply once per scholarship
    __table_args__ = (db.UniqueConstraint('user_id', 'scholarship_id', name='unique_user_scholarship'),)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        
        if not identifier or not password:
            flash('Please provide your ID/email and password.', 'error')
            return render_template('auth/login.html')
        
        # Check if identifier is student ID (8 digits) or email
        import re
        is_student_id = re.match(r'^\d{8}$', identifier)
        
        if is_student_id:
            user = User.query.filter_by(student_id=identifier).first()
        else:
            user = User.query.filter_by(email=identifier).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.get_full_name()}!', 'success')
            
            # Redirect based on role
            if user.role == 'student':
                return redirect(url_for('students.dashboard'))
            elif user.role == 'provider':
                return redirect(url_for('provider.dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid credentials.', 'error')
    
    return render_template('auth/login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page"""
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
        existing_user = User.query.filter(
            (User.email == email) | (User.student_id == student_id)
        ).first()
        
        if existing_user:
            flash('An account with this email or student ID already exists.', 'error')
            return render_template('auth/signup.html')
        
        # Create new user
        try:
            new_user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                student_id=student_id,
                birthday=datetime.strptime(birthday, '%Y-%m-%d').date(),
                role='student'
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Account created successfully. Please sign in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Failed to create account. Please try again.', 'error')
            return render_template('auth/signup.html')
    
    return render_template('auth/signup.html')

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

# Blueprint imports
from auth.routes import auth_bp
from admin.routes import admin_bp
from students.routes import students_bp
from provider.routes import provider_bp

# Initialize database
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Database tables already exist or error: {e}")

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(students_bp, url_prefix='/students')
app.register_blueprint(provider_bp, url_prefix='/provider')

# Custom Jinja2 filters
@app.template_filter('safe_strftime')
def safe_strftime(value, format='%Y-%m-%d'):
    """Safely format datetime objects, handling None and string values"""
    if value is None:
        return 'Not specified'
    
    if isinstance(value, str):
        try:
            # Try to parse the string as datetime
            if 'T' in value:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            else:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except:
            return 'Invalid date'
    
    if hasattr(value, 'strftime'):
        try:
            return value.strftime(format)
        except:
            return 'Invalid date'
    
    return 'Not specified'

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
