#!/usr/bin/env python3
"""
Script to create UC admin account for ScholarSphere
"""

from app import app, db, User
from werkzeug.security import generate_password_hash

def create_uc_admin():
    """Create a UC admin account"""
    with app.app_context():
        # Check if UC admin already exists
        existing_admin = User.query.filter_by(email='admin@uc.edu').first()
        if existing_admin:
            print("❌ UC Admin account already exists!")
            print(f"📧 Email: {existing_admin.email}")
            print(f"👤 Name: {existing_admin.first_name} {existing_admin.last_name}")
            return
        
        # Create UC admin user
        admin = User(
            first_name='UC',
            last_name='Administrator',
            email='admin@uc.edu',
            student_id='00000001',  # Special admin ID
            role='admin'
        )
        admin.set_password('admin123')
        
        try:
            db.session.add(admin)
            db.session.commit()
            print("✅ UC Admin account created successfully!")
            print("📧 Email: admin@uc.edu")
            print("🔑 Password: admin123")
            print("👤 Name: UC Administrator")
            print("🆔 Student ID: 00000001")
            print("⚠️  Please change the password after first login!")
        except Exception as e:
            print(f"❌ Error creating UC admin: {e}")

if __name__ == '__main__':
    create_uc_admin()

