# How to Use test_renewal_dates.py

## Quick Start Guide

The `test_renewal_dates.py` script allows you to easily modify scholarship dates for testing the renewal system without using phpMyAdmin or changing your system date.

## Prerequisites

1. Make sure you're in the project directory (where `app.py` is located)
2. Ensure your Flask app's database connection is configured correctly
3. Python 3.x installed
4. **Activate your virtual environment** (if you're using one):
   ```bash
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   
   # Windows Command Prompt
   venv\Scripts\activate.bat
   
   # Linux/Mac
   source venv/bin/activate
   ```

## Step-by-Step Usage

### 1. List All Scholarships

First, find the scholarship ID you want to test:

```bash
python test_renewal_dates.py --list
```

This will show output like:
```
Available Scholarships:
--------------------------------------------------------------------------------
ID:   1 | Academic Excellence Scholarship    | Code: SCH-001  | Semester: 2024-12-31
ID:   2 | Merit Scholarship                 | Code: SCH-002  | Semester: 2025-06-30
--------------------------------------------------------------------------------
```

### 2. Check Current Dates

Before making changes, check the current dates:

```bash
python test_renewal_dates.py --scholarship-id 1 --show-dates
```

Output:
```
Scholarship: Academic Excellence Scholarship (ID: 1)
Code: SCH-001

Current Date: 2024-12-15
Semester Date: 2024-12-31
  → Expires in 16 days (Renewal banner should show)
Next Last Semester Date: Not set
```

### 3. Set Semester Date to Trigger Renewal Banner

To make the renewal banner appear (set semester to expire within 30 days):

```bash
python test_renewal_dates.py --scholarship-id 1 --set-semester-days 10
```

This sets the semester_date to 10 days from today.

### 4. Set Next Last Semester Date

Required before provider can approve a renewal:

```bash
python test_renewal_dates.py --scholarship-id 1 --set-next-semester-days 180
```

This sets next_last_semester_date to 180 days (6 months) from today.

### 5. Simulate Semester Expiration

To test what happens when the semester expires (set date to yesterday):

```bash
python test_renewal_dates.py --scholarship-id 1 --set-semester-past
```

Or set it to multiple days ago:

```bash
python test_renewal_dates.py --scholarship-id 1 --set-semester-past 5
```

This sets semester_date to 5 days ago.

### 6. Reset Dates (Clean Up)

After testing, reset dates to default:

```bash
python test_renewal_dates.py --scholarship-id 1 --reset-dates
```

This sets semester_date to 180 days from today and clears next_last_semester_date.

## Complete Testing Workflow

Here's a complete example workflow:

```bash
# Step 1: List scholarships
python test_renewal_dates.py --list

# Step 2: Check current dates
python test_renewal_dates.py --scholarship-id 1 --show-dates

# Step 3: Set semester to expire in 10 days (triggers renewal banner)
python test_renewal_dates.py --scholarship-id 1 --set-semester-days 10

# Step 4: Set next semester date (required for approval)
python test_renewal_dates.py --scholarship-id 1 --set-next-semester-days 180

# Step 5: After provider approves renewal, simulate expiration
python test_renewal_dates.py --scholarship-id 1 --set-semester-past

# Step 6: Verify dates were updated
python test_renewal_dates.py --scholarship-id 1 --show-dates

# Step 7: Clean up after testing
python test_renewal_dates.py --scholarship-id 1 --reset-dates
```

## Common Commands Reference

| Command | Description |
|---------|-------------|
| `--list` | List all scholarships with their IDs |
| `--show-dates` | Show current dates for a scholarship |
| `--set-semester-days N` | Set semester_date to N days from today |
| `--set-semester-past [N]` | Set semester_date to N days ago (default: 1) |
| `--set-next-semester-days N` | Set next_last_semester_date to N days from today |
| `--clear-next-semester` | Clear next_last_semester_date |
| `--reset-dates` | Reset all dates to default values |

## Troubleshooting

### Error: "Scholarship with ID X not found"
- Use `--list` to see available scholarship IDs
- Make sure you're using the correct ID

### Error: "No module named 'app'"
- Make sure you're running the script from the project root directory
- Ensure `app.py` is in the same directory

### Error: Database connection issues
- Check your `config.env` file has correct database credentials
- Make sure your database server is running
- Verify the database name exists

### Dates not updating?
- Check that the script completed successfully (look for ✓ checkmark)
- Refresh your browser after running the script
- Check database directly if needed

## Tips

1. **Always check dates first**: Use `--show-dates` before and after making changes
2. **Use --list frequently**: Helps you find the right scholarship ID
3. **Reset after testing**: Use `--reset-dates` to clean up test data
4. **Test incrementally**: Start with small date changes (e.g., 5 days) before testing expiration

## Example: Testing Full Renewal Flow

```bash
# 1. Find your test scholarship
python test_renewal_dates.py --list

# 2. Set up for renewal banner (10 days until expiration)
python test_renewal_dates.py --scholarship-id 1 --set-semester-days 10

# 3. Now test in browser:
#    - Student sees renewal banner
#    - Student submits renewal
#    - Provider approves renewal

# 4. Set next semester date (if not already set)
python test_renewal_dates.py --scholarship-id 1 --set-next-semester-days 180

# 5. Simulate semester expiration (set to yesterday)
python test_renewal_dates.py --scholarship-id 1 --set-semester-past

# 6. Visit any page (student or provider) to trigger expiration check
#    - Old application becomes "Completed"
#    - Renewal becomes active
#    - Dates update automatically

# 7. Verify results
python test_renewal_dates.py --scholarship-id 1 --show-dates
```

## Notes

- The script uses your Flask app's database connection
- All changes are permanent until you reset them
- The expiration check runs automatically when students/providers visit pages
- No need to restart your Flask app after running the script

