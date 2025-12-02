# Semester Expiration - Code-Based Approach (No Cron Job Required)

This document explains how semester expiration checking works without requiring a cron job or scheduled task.

## How It Works

Instead of running a scheduled task, the system checks for semester expirations **on-demand** when students interact with the application. This happens automatically in the background without any user-visible delay.

## Integration Points

The semester expiration check runs automatically at these points:

1. **Student Login** (`auth/routes.py`)
   - After successful login, before redirecting to dashboard
   - Ensures expirations are checked every time a student logs in

2. **Student Dashboard** (`students/routes.py` - `dashboard()`)
   - When students view their dashboard
   - Catches expirations even if they skip login check

3. **Student Applications Page** (`students/routes.py` - `applications()`)
   - When students view their applications
   - Ensures notifications are sent when students check their applications

## What Gets Checked

For each logged-in student, the system:

1. **Finds all approved applications** for that student
2. **Checks each scholarship's semester date** against today's date
3. **Sends advance notifications** if:
   - 30 days (1 month) before expiration
   - 14 days (2 weeks) before expiration
   - 7 days (1 week) before expiration
   - 3 days before expiration
4. **Processes expired semesters** if:
   - Semester date has passed
   - Archives the application
   - Sends expiration notification

## Features

### ✅ Advantages

- **No cron job needed** - Works on free hosting plans
- **Automatic catch-up** - If a student hasn't logged in for a while, they'll get all missed notifications when they do log in
- **Lightweight** - Only checks the current student's applications
- **Non-blocking** - Errors don't break login/dashboard functionality
- **Duplicate prevention** - Uses tracking table to prevent sending same notification twice

### ⚠️ Considerations

- **Requires student activity** - Notifications are sent when students log in or view pages
- **Not real-time** - If a student never logs in, they won't get advance notifications (but will be processed when they do log in)
- **Email delivery** - Email sending happens asynchronously and failures don't block the process

## Files Involved

1. **`semester_expiration_utils.py`**
   - Contains all the logic for checking and processing expirations
   - Can be called from any route

2. **`auth/routes.py`**
   - Calls `check_student_semester_expirations()` after student login

3. **`students/routes.py`**
   - Calls `check_student_semester_expirations()` in dashboard and applications routes

4. **`migrate_add_semester_expiration_notifications_table.py`**
   - Creates the tracking table to prevent duplicate notifications

5. **Email Templates:**
   - `templates/email/semester_expiring_advance.html`
   - `templates/email/semester_expired.html`

## How Notifications Work

### Advance Notifications

When a student logs in or views their dashboard/applications:
- System checks if semester expires in 30, 14, 7, or 3 days
- If within window and notification not sent, sends:
  - In-app notification (stored in database)
  - Email notification (if email configured)
- Records notification in tracking table to prevent duplicates

### Expiration Processing

When semester has expired:
- Archives the application (sets status to 'archived', is_active to False)
- Creates in-app notification
- Sends email notification
- Records in tracking table

## Testing

To test the system:

1. **Create a test scholarship** with a semester date:
   - Set `semester_date` to today + 30 days (for 1 month test)
   - Set `semester_date` to today + 14 days (for 2 weeks test)
   - Set `semester_date` to yesterday (for expiration test)

2. **Create an approved application** for a test student

3. **Log in as that student** - Check should run automatically

4. **Check notifications:**
   - In-app: Student dashboard should show notification
   - Email: Check student's email inbox

5. **Verify tracking:**
   - Check `semester_expiration_notifications` table
   - Should see one record per notification type sent

## Migration Required

Before using this system, run the migration:

```bash
python migrate_add_semester_expiration_notifications_table.py
```

Or include it in your migration suite:

```bash
python run_all_migrations.py
```

## Fallback Option

If you prefer scheduled tasks for more reliable timing, you can still use `process_semester_expirations.py` with a cron job. Both approaches can coexist - the code-based approach will catch anything the cron job misses, and vice versa.

## Error Handling

All checks are wrapped in try-except blocks to ensure:
- Login never fails due to expiration check errors
- Dashboard/applications pages always load
- Email failures don't block the process
- Database errors are handled gracefully

Errors are silently caught (in production, you might want to log them for monitoring).

