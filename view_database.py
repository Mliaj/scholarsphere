#!/usr/bin/env python3
"""
Script to view SQLite database contents
"""

from app import app, db, User
from datetime import datetime

def view_database():
    """View all users in the database"""
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("Database is empty - No users found")
            return
        
        print("ScholarSphere SQLite Database Contents")
        print("=" * 60)
        print(f"Total Users: {len(users)}")
        print("=" * 60)
        
        for user in users:
            print(f"User ID: {user.id}")
            print(f"   Name: {user.first_name} {user.last_name}")
            print(f"   Email: {user.email}")
            print(f"   Student ID: {user.student_id}")
            print(f"   Birthday: {user.birthday}")
            print(f"   Year Level: {user.year_level or 'Not specified'}")
            print(f"   Course: {user.course or 'Not specified'}")
            print(f"   Role: {user.role}")
            print(f"   Created: {user.created_at}")
            print("-" * 40)

if __name__ == '__main__':
    view_database()
