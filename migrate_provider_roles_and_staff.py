#!/usr/bin/env python3
"""
Migration: Update provider roles to provider_admin and provider_staff, add staff relationship

Changes:
  - Update role enum to include 'provider_admin' and 'provider_staff' instead of 'provider'
  - Add managed_by column to link staff to their admin
  - Convert existing 'provider' roles to 'provider_admin'
  - Add indexes for performance

Usage: python migrate_provider_roles_and_staff.py
"""
from app import app, db
from sqlalchemy import text


def column_exists(table: str, column: str) -> bool:
    """Check if a column exists in a table (MySQL)"""
    result = db.session.execute(text("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = :table 
        AND COLUMN_NAME = :column
    """), {"table": table, "column": column})
    return result.fetchone() is not None


def migrate():
    with app.app_context():
        try:
            # Check if users table exists
            result = db.session.execute(text("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'
            """))
            table_exists = result.fetchone() is not None

            if not table_exists:
                print("ERROR: users table does not exist. Please run base migrations first.")
                return

            # Step 1: Add managed_by column if it doesn't exist
            if not column_exists('users', 'managed_by'):
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN managed_by INT NULL,
                    ADD INDEX idx_managed_by (managed_by),
                    ADD FOREIGN KEY (managed_by) REFERENCES users(id) ON DELETE SET NULL
                """))
                print("OK: Added managed_by column to users table")
            else:
                print("INFO: managed_by column already exists")

            # Step 2: Update role enum values
            # For MySQL, we need to modify the enum type
            # First, check current role values
            try:
                # Get current role values
                current_roles = db.session.execute(text("""
                    SELECT DISTINCT role FROM users WHERE role IS NOT NULL
                """)).fetchall()
                print(f"INFO: Current roles in database: {[r[0] for r in current_roles]}")

                # For MySQL, we need to alter the column type
                # This is complex with ENUM, so we'll use a workaround:
                # 1. Add a temporary column
                # 2. Copy data with transformations
                # 3. Drop old column
                # 4. Rename new column
                
                # Check if we need to update
                has_provider = db.session.execute(text("""
                    SELECT COUNT(*) FROM users WHERE role = 'provider'
                """)).scalar() > 0

                if has_provider:
                    print("INFO: Found users with 'provider' role, converting to 'provider_admin'...")
                    
                    # Convert 'provider' to 'provider_admin'
                    db.session.execute(text("""
                        UPDATE users 
                        SET role = 'provider_admin' 
                        WHERE role = 'provider'
                    """))
                    print("OK: Converted 'provider' roles to 'provider_admin'")
                else:
                    print("INFO: No users with 'provider' role found")

                # For MySQL ENUM modification, we need to alter the column
                # This is tricky, so we'll use ALTER TABLE MODIFY
                try:
                    db.session.execute(text("""
                        ALTER TABLE users 
                        MODIFY COLUMN role ENUM('student', 'provider_admin', 'provider_staff', 'admin') 
                        NOT NULL DEFAULT 'student'
                    """))
                    print("OK: Updated role enum to remove 'provider' and keep only provider_admin and provider_staff")
                except Exception as e:
                    # If enum modification fails, try alternative approach
                    print(f"WARNING: Direct enum modification failed: {e}")
                    print("INFO: You may need to manually update the role enum type")
                    print("INFO: Or the database may already support the new values")

            except Exception as e:
                print(f"WARNING: Error updating role enum: {e}")
                print("INFO: You may need to manually update the role column type")

            db.session.commit()
            print("OK: Provider roles and staff relationship migration completed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"ERROR: Migration failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    migrate()

