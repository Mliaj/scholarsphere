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
            print(f"Email: {existing_admin.email}")
            print(f"Name: {existing_admin.first_name} {existing_admin.last_name}")
            print(f"Role: {existing_admin.role}")
            return
        
        # Create admin user
        admin = User(
            first_name='System',
            last_name='Administrator',
            email='admin@scholarsphere.com',
            student_id='00000000',  # Special admin ID
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')  # Change this password!
        
        try:
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin account created successfully!")
            print("📧 Email: admin@scholarsphere.com")
            print("🔑 Password: admin123")
            print("👤 Name: System Administrator")
            print("🆔 Student ID: 00000000")
            print("🔐 Role: admin")
            print("⚠️  Please change the password after first login!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating admin: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    create_admin()
