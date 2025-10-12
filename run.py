#!/usr/bin/env python3
"""
Run script for Scholarsphere Python application
"""

import os
import sys
from app import app, db

def create_tables():
    """Create database tables"""
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {e}")
            return False
    return True

def main():
    """Main function"""
    print("Starting Scholarsphere Python Application...")
    print("=" * 50)
    
    # Check if database tables exist
    print("Checking database connection...")
    if not create_tables():
        print("Failed to initialize database. Please check your configuration.")
        sys.exit(1)
    
    print("Database connection successful!")
    print("=" * 50)
    
    # Get configuration
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"Starting server on http://{host}:{port}")
    print(f"Debug mode: {'ON' if debug else 'OFF'}")
    print("=" * 50)
    print("Access the application at:")
    print(f"   • Home: http://{host}:{port}")
    print(f"   • Login: http://{host}:{port}/auth/login")
    print(f"   • Signup: http://{host}:{port}/auth/signup")
    print("=" * 50)
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
