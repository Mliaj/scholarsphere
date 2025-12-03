#!/usr/bin/env python3
"""
Setup script to create necessary upload directories
"""

import os

# Upload directories to create
UPLOAD_DIRECTORIES = [
    'static/uploads',
    'static/uploads/profile_pictures',
    'static/uploads/credentials'
]

def setup_directories():
    """Create upload directories if they don't exist"""
    created_count = 0
    
    for directory in UPLOAD_DIRECTORIES:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
            created_count += 1
        else:
            print(f"Directory already exists: {directory}")
    
    print(f"\nSetup complete! {created_count} new directories created.")

if __name__ == "__main__":
    print("Setting up upload directories...")
    print("=" * 60)
    setup_directories()
    print("=" * 60)


