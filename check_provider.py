#!/usr/bin/env python3
"""
Check provider information from MySQL database
"""
from app import app, db
from sqlalchemy import text

with app.app_context():
    result = db.session.execute(
        text("SELECT id, first_name, last_name, email, role, organization, LENGTH(password_hash) FROM users WHERE email = :email"),
        {"email": "gayo@uc.edu"}
    )
    row = result.fetchone()
    if row:
        print(row)
    else:
        print("Provider not found")
