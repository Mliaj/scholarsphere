#!/usr/bin/env python3
"""
List all providers from MySQL database
"""
import json
from app import app, db
from sqlalchemy import text

with app.app_context():
    result = db.session.execute(
        text("SELECT id, first_name, last_name, email, organization, role FROM users WHERE role='provider' ORDER BY id")
    )
    rows = result.fetchall()
    
    # Convert rows to list of dictionaries
    providers = []
    for row in rows:
        providers.append({
            'id': row[0],
            'first_name': row[1],
            'last_name': row[2],
            'email': row[3],
            'organization': row[4],
            'role': row[5]
        })
    
    print(json.dumps(providers, indent=2))
