#!/usr/bin/env python3
"""
Script to create admin accounts for ScholarSphere
"""

from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin():
    """Create an admin account"""
    with app.app_context():
        # Check if admin already exists
        existing_admin = User.query.filter_by(email='admin@scholarsphere.com').first()
        if existing_admin:
            print("Admin account already exists!")
            return
        
        # Create admin user
        admin = User(
            first_name='System',
            last_name='Administrator',
            email='admin@scholarsphere.com',
            student_id='00000000',  # Special admin ID
            role='admin'
        )
        admin.set_password('admin123')  # Change this password!
        
        try:
            db.session.add(admin)
            db.session.commit()
            print("Admin account created successfully!")
            print("Email: admin@scholarsphere.com")
            print("Password: admin123")
            print("Please change the password after first login!")
        except Exception as e:
            print(f"Error creating admin: {e}")

if __name__ == '__main__':
    create_admin()
