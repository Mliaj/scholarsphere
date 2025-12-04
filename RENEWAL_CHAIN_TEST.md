# Renewal Chain Test Guide

## Overview

This test verifies that renewal applications can be renewed again after becoming active. This tests the complete renewal chain:

1. **First Application** → Approved
2. **First Renewal** → Approved → Becomes Active
3. **Second Renewal** → Should be possible when semester expires

## Key Requirements

- `is_renewal=True` persists for record keeping (providers can see renewal status)
- Active renewals can be renewed again when their semester expires
- Only inactive renewals block future renewals

## Quick Start

### 1. List Available Test Data

```bash
python test_renewal_chain.py --list
```

This shows:
- Available scholarships with their IDs
- Available students with their IDs and approved application counts

### 2. Run the Test

```bash
python test_renewal_chain.py --scholarship-id 1 --student-id 1
```

### 3. Verbose Output

```bash
python test_renewal_chain.py --scholarship-id 1 --student-id 1 --verbose
```

## Test Prerequisites

Before running the test, ensure:

1. **Student has an approved application** for the scholarship
2. **First renewal has been approved** and is active
   - If not, follow the renewal flow:
     - Submit renewal application
     - Provider approves it
     - Set `semester_date` to past to activate renewal
3. **Scholarship has `semester_date` set** (can be in future or past)

## What the Test Checks

### Step 1: Initial Application
- Verifies original approved application exists
- Checks application status and active state

### Step 2: Active Renewal
- Verifies active renewal exists
- **Key Check:** Confirms `is_renewal=True` (for record keeping)
- Checks `original_application_id` is set

### Step 3: Scholarship Semester Date
- Verifies scholarship has `semester_date` set
- Calculates days until expiration

### Step 4: Renewal Eligibility
- Checks if renewal banner should appear
- Verifies no pending renewals blocking
- Verifies no inactive renewals blocking

### Step 5: Active Renewal Doesn't Block
- **Key Test:** Verifies active renewals don't block future renewals
- Only inactive renewals should block
- Active renewals should allow future renewals

### Step 6: Eligibility Simulation
- Simulates the actual renewal eligibility check from `students/routes.py`
- Verifies all conditions are met for renewal banner to appear
- Provides detailed reasons if not eligible

## Expected Results

### ✓ Test Passes When:

- Original application exists and is approved
- Active renewal exists with `is_renewal=True`
- Active renewal is eligible for renewal (when semester expires within 30 days)
- No inactive renewals blocking future renewals
- Provider can see `is_renewal=True` for record keeping

### ✗ Test Fails When:

- No original application found
- No active renewal found
- Active renewal has `is_renewal=False` (should be True)
- Inactive renewals are blocking future renewals
- Renewal eligibility conditions not met

## Example Test Scenarios

### Scenario 1: Renewal Eligible (Semester Expires Soon)

```bash
# Set semester to expire in 10 days
python test_renewal_dates.py --scholarship-id 1 --set-semester-days 10

# Run test
python test_renewal_chain.py --scholarship-id 1 --student-id 1 --verbose
```

**Expected:** Test passes, renewal banner should appear

### Scenario 2: Renewal Not Yet Eligible (Semester Expires Later)

```bash
# Set semester to expire in 60 days
python test_renewal_dates.py --scholarship-id 1 --set-semester-days 60

# Run test
python test_renewal_chain.py --scholarship-id 1 --student-id 1 --verbose
```

**Expected:** Test passes, but renewal banner won't appear yet (> 30 days)

### Scenario 3: Semester Already Expired

```bash
# Set semester to yesterday
python test_renewal_dates.py --scholarship-id 1 --set-semester-past

# Run test
python test_renewal_chain.py --scholarship-id 1 --student-id 1 --verbose
```

**Expected:** Test passes, but semester has expired (should trigger expiration processing)

## Troubleshooting

### "No active renewal found"

**Solution:**
1. Create a renewal application
2. Approve it as provider
3. Set `semester_date` to past to activate renewal:
   ```bash
   python test_renewal_dates.py --scholarship-id 1 --set-semester-past
   ```
4. Visit student applications page to trigger expiration processing
5. Run test again

### "Active renewal has is_renewal=False"

**Solution:**
- This should not happen with the updated code
- Check that `semester_expiration_utils.py` doesn't set `is_renewal=False`
- Verify the renewal was created with `is_renewal=True`

### "Renewal banner not appearing"

**Check:**
- Semester date is within 30 days
- Application is approved and active
- Scholarship is active
- No pending or inactive renewals blocking

## Integration with Manual Testing

This automated test complements manual testing:

1. **Automated Test:** Verifies logic and data integrity
2. **Manual Test:** Verifies UI and user experience

Run both for complete verification:
- Automated test ensures logic is correct
- Manual test ensures UI works correctly

## Related Files

- `test_renewal_chain.py` - Automated test script
- `test_renewal_dates.py` - Date manipulation helper
- `semester_expiration_utils.py` - Renewal activation logic
- `students/routes.py` - Renewal eligibility check logic
- `TESTING_RENEWAL_SYSTEM.md` - Complete testing guide

