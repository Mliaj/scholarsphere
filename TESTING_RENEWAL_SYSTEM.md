# Testing the Renewal System Locally

## Overview
This guide explains how to test the renewal system without changing your Windows system date. The recommended approach is to modify database dates directly.

## Method 1: Modify Database Dates (Recommended)

### Step 1: Set Up Test Data

1. **Create a test scholarship with a semester date:**
   - Log in as a provider
   - Create a scholarship
   - Set `semester_date` to a date in the near future (e.g., 5 days from today)
   - Set `next_last_semester_date` to a date further in the future (e.g., 6 months from today)

2. **Create an approved application:**
   - Log in as a student
   - Apply to the scholarship
   - Log in as provider and approve the application

### Step 2: Test Renewal Flow

#### Test Case 1: Renewal Banner Appears
1. **Update the scholarship's `semester_date` to be within 30 days:**
   ```sql
   -- Connect to your database (MySQL/MariaDB)
   -- Find the scholarship ID first
   SELECT id, title, semester_date FROM scholarships WHERE title = 'Your Test Scholarship';
   
   -- Update semester_date to 10 days from today
   UPDATE scholarships 
   SET semester_date = DATE_ADD(CURDATE(), INTERVAL 10 DAY)
   WHERE id = YOUR_SCHOLARSHIP_ID;
   ```

2. **Verify:**
   - Log in as student
   - Go to "My Applications" page
   - You should see: "Your semester is almost up; renew now to keep your scholarship."
   - Banner should show days until expiration

#### Test Case 2: Submit Renewal Request
1. **Click "Renew" button**
2. **Click "Continue" in the confirmation modal**
3. **Fill out the renewal application form**
4. **Submit the application**

5. **Verify:**
   - Redirected to "My Applications" page
   - Renewal banner should be hidden
   - Should see "Submitted Renewal Request" banner
   - Application status should be "Pending"

#### Test Case 3: Provider Approves Renewal
1. **Log in as provider**
2. **Go to Applications page**
3. **Find the renewal application**
4. **Verify:**
   - Should see "Renewal" badge
   - Should see "Next last semester date to be updated: [date]" if `next_last_semester_date` is set
   - Should see "No next last semester provided" if not set

5. **Approve the renewal:**
   - Click "Approve"
   - If `next_last_semester_date` is not set, you should see an error
   - Set `next_last_semester_date` in scholarship settings if needed
   - Approve again

6. **Verify:**
   - Renewal status changes to "Approved"
   - Student receives notification

#### Test Case 4: Renewal Approved but Semester Not Expired
1. **As student, check "My Applications":**
   - Current application should still be "Approved" and active
   - Renewal application should be "Approved" but inactive
   - Renewal banner should be **hidden** (because renewal is approved)
   - Should see the renewal application displayed

#### Test Case 5: Semester Expires (Renewal Activates)
1. **Update `semester_date` to be in the past:**
   ```sql
   -- Set semester_date to yesterday
   UPDATE scholarships 
   SET semester_date = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
   WHERE id = YOUR_SCHOLARSHIP_ID;
   ```

2. **Trigger expiration check:**
   - Log in as student OR provider
   - Visit any page (dashboard, applications, etc.)
   - The expiration check runs automatically

3. **Verify:**
   - Old application status changes to "Completed"
   - Renewal application becomes active
   - Scholarship's `semester_date` updates to `next_last_semester_date`
   - `next_last_semester_date` is cleared (set to NULL)
   - Student receives notification about renewal activation
   - **IMPORTANT:** Renewal application keeps `is_renewal=True` for record keeping

#### Test Case 6: Active Renewal Can Be Renewed Again (Renewal Chain)
This tests that when a renewal application becomes active, it can be renewed again.

1. **Prerequisites:**
   - You should have completed Test Case 5 (renewal is now active)
   - Active renewal should have `is_renewal=True` (for record keeping)
   - Set `next_last_semester_date` for the scholarship (for the second renewal)

2. **Set semester_date for the active renewal:**
   ```sql
   -- Set semester_date to 10 days from today (within renewal window)
   UPDATE scholarships 
   SET semester_date = DATE_ADD(CURDATE(), INTERVAL 10 DAY)
   WHERE id = YOUR_SCHOLARSHIP_ID;
   
   -- Set next_last_semester_date for the second renewal
   UPDATE scholarships 
   SET next_last_semester_date = DATE_ADD(CURDATE(), INTERVAL 180 DAY)
   WHERE id = YOUR_SCHOLARSHIP_ID;
   ```

3. **Verify renewal eligibility:**
   - Log in as student
   - Go to "My Applications" page
   - **Expected:** Renewal banner SHOULD appear for the active renewal
   - The active renewal (which was originally a renewal) should be eligible for renewal

4. **Submit second renewal:**
   - Click "Renew" button on the active renewal
   - Fill out and submit the renewal application
   - **Expected:** Second renewal application is created with `is_renewal=True`

5. **Provider approves second renewal:**
   - Log in as provider
   - Approve the second renewal
   - **Expected:** Second renewal is approved and marked as inactive (waiting for semester to expire)

6. **Verify record keeping:**
   ```sql
   -- Check that all renewals have is_renewal=True
   SELECT id, status, is_renewal, is_active, original_application_id
   FROM scholarship_applications
   WHERE user_id = YOUR_STUDENT_ID
     AND scholarship_id = YOUR_SCHOLARSHIP_ID
   ORDER BY application_date;
   ```
   - **Expected:** All renewal applications should have `is_renewal=True`
   - Provider should be able to see that applications are renewals

7. **Test using automated test script:**
   ```bash
   python test_renewal_chain.py --scholarship-id YOUR_SCHOLARSHIP_ID --student-id YOUR_STUDENT_ID --verbose
   ```
   - This will verify the complete renewal chain
   - Checks that active renewals can be renewed again
   - Verifies `is_renewal=True` persists for record keeping

### Step 3: Reset Test Data

After testing, reset dates:
```sql
-- Reset semester_date
UPDATE scholarships 
SET semester_date = DATE_ADD(CURDATE(), INTERVAL 6 MONTH)
WHERE id = YOUR_SCHOLARSHIP_ID;

-- Clear next_last_semester_date
UPDATE scholarships 
SET next_last_semester_date = NULL
WHERE id = YOUR_SCHOLARSHIP_ID;
```

## Method 2: Change System Date (Not Recommended)

⚠️ **Warning:** Changing system date affects all applications on your computer.

### Steps:
1. **Backup your work** (save all files)
2. **Change Windows date:**
   - Right-click on date/time in taskbar
   - Select "Adjust date/time"
   - Turn off "Set time automatically"
   - Click "Change" and set a future date
3. **Restart your Flask app**
4. **Test the renewal flow**
5. **Change date back** when done

### Issues with this method:
- Affects all applications on your computer
- May cause issues with other software
- Requires app restart
- Can cause confusion

## Quick SQL Commands for Testing

### Check current dates:
```sql
SELECT 
    id, 
    title, 
    semester_date, 
    next_last_semester_date,
    DATEDIFF(semester_date, CURDATE()) as days_until_expiration
FROM scholarships 
WHERE id = YOUR_SCHOLARSHIP_ID;
```

### Check applications:
```sql
SELECT 
    sa.id,
    sa.status,
    sa.is_renewal,
    sa.is_active,
    s.title as scholarship_title,
    s.semester_date
FROM scholarship_applications sa
JOIN scholarships s ON sa.scholarship_id = s.id
WHERE sa.user_id = YOUR_STUDENT_ID
ORDER BY sa.application_date DESC;
```

### Set semester to expire in 5 days:
```sql
UPDATE scholarships 
SET semester_date = DATE_ADD(CURDATE(), INTERVAL 5 DAY)
WHERE id = YOUR_SCHOLARSHIP_ID;
```

### Set semester to expire yesterday:
```sql
UPDATE scholarships 
SET semester_date = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
WHERE id = YOUR_SCHOLARSHIP_ID;
```

### Set next_last_semester_date:
```sql
UPDATE scholarships 
SET next_last_semester_date = DATE_ADD(CURDATE(), INTERVAL 6 MONTH)
WHERE id = YOUR_SCHOLARSHIP_ID;
```

## Testing Checklist

### Basic Renewal Flow
- [ ] Renewal banner appears when semester expires within 30 days
- [ ] "Renew" button works and shows confirmation modal
- [ ] "Do Not Renew" records failure correctly
- [ ] "Continue" redirects to Browse Scholarships with renewal filter
- [ ] "For Renewal" badge appears on scholarship card
- [ ] Renewal application can be submitted
- [ ] Renewal application shows as "Pending" in My Applications
- [ ] Provider sees renewal badge in Applications page
- [ ] Provider sees next_last_semester_date status
- [ ] Provider cannot approve without next_last_semester_date
- [ ] Provider can approve renewal (with next_last_semester_date set)
- [ ] Renewal shows as "Approved" but inactive when current app is still active
- [ ] Renewal banner is hidden when renewal is approved
- [ ] Current application remains active until semester expires

### Renewal Activation
- [ ] When semester expires:
  - [ ] Old application becomes "Completed"
  - [ ] Renewal becomes active
  - [ ] semester_date updates to next_last_semester_date
  - [ ] next_last_semester_date is cleared
  - [ ] Student receives notification
  - [ ] **Active renewal keeps `is_renewal=True` for record keeping**

### Renewal Chain (Active Renewal Can Be Renewed Again)
- [ ] Active renewal (originally a renewal) can be renewed again
- [ ] Renewal banner appears for active renewal when semester expires within 30 days
- [ ] Second renewal application can be submitted
- [ ] Second renewal has `is_renewal=True`
- [ ] Provider can see that all renewals are marked as renewals (`is_renewal=True`)
- [ ] Active renewals don't block future renewals
- [ ] Only inactive renewals block future renewals
- [ ] "Renewed" tag shows for active renewals (via `was_renewal` check)

## Troubleshooting

### Renewal banner not appearing?
- Check that `semester_date` is within 30 days
- Check that application status is "approved"
- Check that there's no pending or approved renewal already
- Verify `is_active = 1` for the scholarship

### Expiration not processing?
- Check that `semester_date` is in the past
- Visit a page (dashboard/applications) to trigger the check
- Check database for any errors
- Verify the renewal application exists and is approved

### Dates not updating?
- Check database connection
- Verify SQL syntax
- Check for transaction commits
- Refresh the page after updating dates

## Automated Testing

### Test Renewal Chain
Use the automated test script to verify the complete renewal chain:

```bash
# List available scholarships and students
python test_renewal_chain.py --list

# Test renewal chain for specific scholarship and student
python test_renewal_chain.py --scholarship-id 1 --student-id 1

# Verbose output
python test_renewal_chain.py --scholarship-id 1 --student-id 1 --verbose
```

The test verifies:
- Active renewal has `is_renewal=True` (persistent for record keeping)
- Active renewal can be renewed again when semester expires
- Only inactive renewals block future renewals
- Renewal eligibility logic works correctly

### Test Renewal Dates
Use the date manipulation script for testing:

```bash
# Show current dates
python test_renewal_dates.py --scholarship-id 1 --show-dates

# Set semester to expire in 10 days
python test_renewal_dates.py --scholarship-id 1 --set-semester-days 10

# Set semester to expire yesterday (to trigger activation)
python test_renewal_dates.py --scholarship-id 1 --set-semester-past

# Set next semester date
python test_renewal_dates.py --scholarship-id 1 --set-next-semester-days 180
```

## Notes

- The expiration check runs automatically when students/providers visit pages
- No cron job needed - checks happen on page load
- All date comparisons use `date.today()` which gets the current system date
- Database dates should be in `YYYY-MM-DD` format
- **Important:** `is_renewal=True` persists even after renewal becomes active for record keeping
- Active renewals (approved + active) can be renewed again when their semester expires
- Only inactive renewals (approved but not yet active) block future renewals

