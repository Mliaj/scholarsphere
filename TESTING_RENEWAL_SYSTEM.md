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
- [ ] When semester expires:
  - [ ] Old application becomes "Completed"
  - [ ] Renewal becomes active
  - [ ] semester_date updates to next_last_semester_date
  - [ ] next_last_semester_date is cleared
  - [ ] Student receives notification

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

## Notes

- The expiration check runs automatically when students/providers visit pages
- No cron job needed - checks happen on page load
- All date comparisons use `date.today()` which gets the current system date
- Database dates should be in `YYYY-MM-DD` format

